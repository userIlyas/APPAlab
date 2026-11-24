"""OpenAPPA information-flow gate for the Agentic Banking Lab.

Wires OpenAPPA's deterministic policy engine (the ``appa-agent-python`` PyO3
binding, built from the OpenAPPA workspace) into the points where data crosses
a trust boundary in the agent loop:

* ``services.common.mcp.MCPClient.call``  -> ``abs.*`` / ``search.*`` tools
* memory recall (``MemoryClient.recall`` / ``SkillMemoryClient.request("context")``)
  -> ``memory.recall`` (trusted read) + ``memory.untrusted`` (synthetic narrowing
  emitted only when the recalled records are marked untrusted)
* ``TravelA2AClient._send``               -> ``travel.plan`` (external partner)

OpenAPPA keeps a per-conversation trajectory label (trust x audience) by
replaying admitted tool events before every decision.  Readers of untrusted
bytes (search, external partner, poisoned memory) narrow trust
``trusted -> suspicious``; money sinks declare ``requires = { trust = "trusted" }``
and are deterministically refused once the conversation has ingested untrusted data.

Recoverable IFC: a *narrowing* read is refused first and offered a remedy.
This module auto-accepts only narrowing offers for tools that the policy itself
declares to lower trust (``ALLOW_NARROW``), never authority/escalation offers.

Modes (env ``APPA_TAINT_MODE``):

* ``off``     (default) — engine never loaded; zero overhead; running stand unchanged.
* ``observe`` — engine runs and decisions are logged; nothing is blocked (advisory).
* ``enforce`` — engine runs and blocks sinks that violate the policy.  **Fail-closed**:
  if the native engine, the policy file, or a session cannot be (re)built, the gate
  raises :class:`TaintDenied` instead of silently passing the call through.
"""

from __future__ import annotations

import asyncio
import contextvars
import json
import logging
import os
import threading
import uuid
from typing import Any, Awaitable, Callable

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]

logger = logging.getLogger("appa_taint")

MODE = os.getenv("APPA_TAINT_MODE", "off").strip().lower()
POLICY_PATH = os.getenv(
    "APPA_TAINT_POLICY",
    os.path.join(os.path.dirname(__file__), "..", "..", "configs", "appa.toml"),
)
# Candidate readers whose narrowing may be auto-accepted.  Pruned at load time to
# the tools the policy actually declares as narrowing readers (fail safe).
ALLOW_NARROW = tuple(
    json.loads(
        os.getenv(
            "APPA_TAINT_ALLOW_NARROW",
            '["memory.untrusted","search.text","search.news","travel.plan"]',
        )
    )
)
CONTROL_TOOL = "execute_remedy_plan"
MAX_SESSIONS = int(os.getenv("APPA_TAINT_MAX_SESSIONS", "4096"))

# Metadata `source` values that mark a recalled memory record as untrusted bytes
# (external web, external partner, lab-injected poison).  Bank-owned sources stay
# trusted; SECURITY.md S03/S14/S15 are about these external sources.
UNTRUSTED_SOURCES = frozenset(
    {"internet", "travel-partner", "duckduckgo-mcp", "user-chat-lab"}
)

_conversation: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "appa_conversation", default=None
)


def set_conversation(conversation_id: str) -> contextvars.Token:
    """Pin the trajectory id for the current request (called at the chat entry)."""
    return _conversation.set(conversation_id)


def reset_conversation(token: contextvars.Token) -> None:
    _conversation.reset(token)


def current_conversation() -> str | None:
    return _conversation.get()


def has_untrusted_memory(result: Any) -> bool:
    """True when a recall result carries records the host marked untrusted."""
    records = result
    if isinstance(result, dict) and "memories" in result:
        records = result["memories"]
    if not isinstance(records, list):
        return False
    for record in records:
        if not isinstance(record, dict):
            continue
        metadata = record.get("metadata")
        if not isinstance(metadata, dict):
            continue
        trust = str(metadata.get("trust") or "")
        source = str(metadata.get("source") or "")
        if trust.startswith("untrusted") or source in UNTRUSTED_SOURCES:
            return True
    return False


class TaintDenied(RuntimeError):
    """A tool call was refused by the OpenAPPA policy gate."""


class _SessionEntry:
    def __init__(self, conversation_id: str, native: Any, allowed_narrow: frozenset[str]):
        self.conversation_id = conversation_id
        self.native = native
        self.allowed_narrow = allowed_narrow
        self.lock = threading.Lock()


class TaintGate:
    """Process-wide, per-conversation OpenAPPA gate (opt-in)."""

    def __init__(self, mode: str | None = None, policy_path: str | None = None) -> None:
        requested = (mode or MODE).strip().lower()
        self.mode = requested if requested in {"off", "observe", "enforce"} else "off"
        self.policy_path = policy_path or POLICY_PATH
        self._native = self._load_native()
        self._sessions: dict[str, _SessionEntry] = {}
        self._sessions_lock = threading.Lock()
        self._policy_toml: str | None = None
        self._tool_names: list[str] = []
        self._declared_narrowers: frozenset[str] = frozenset()
        self._allowed_narrow: frozenset[str] = frozenset(ALLOW_NARROW)
        if self.mode != "off":
            self._reload_policy()

    # ------------------------------------------------------------------ setup
    def _load_native(self) -> Any:
        if self.mode == "off":
            return None
        try:
            import appa_agent_python  # noqa: F401
        except Exception as exc:
            if self.mode == "enforce":
                logger.critical(
                    "APPA_TAINT_MODE=enforce but appa_agent_python is not importable; "
                    "the gate will fail closed: %s",
                    exc,
                )
            else:
                logger.warning("appa_agent_python not importable; taint gate disabled: %s", exc)
            return None
        logger.info("OpenAPPA engine loaded: %s", appa_agent_python.BINDING_IDENTITY)
        return appa_agent_python

    def _reload_policy(self) -> None:
        try:
            with open(self.policy_path, "rb") as fh:
                raw = fh.read()
            text = raw.decode("utf-8")
            if tomllib is None:
                raise RuntimeError("tomllib unavailable")
            data = tomllib.loads(text)
        except Exception as exc:
            logger.critical("cannot load OpenAPPA policy %s: %s", self.policy_path, exc)
            self._policy_toml = None
            self._tool_names = []
            self._declared_narrowers = frozenset()
            return
        self._policy_toml = text
        self._tool_names = [t["name"] for t in data.get("tool", [])]
        self._declared_narrowers = frozenset(
            t["name"]
            for t in data.get("tool", [])
            if t.get("delta") and not t.get("requires")
        )
        # Fail safe: never auto-accept a remedy for a tool the policy does not
        # declare as a narrowing reader.
        self._allowed_narrow = self._allowed_narrow & self._declared_narrowers

    def status(self) -> dict[str, Any]:
        """Read-only health/debug view for the /health endpoint and diagnostics."""
        return {
            "mode": self.mode,
            "engine_available": self._native is not None,
            "engine_identity": getattr(self._native, "BINDING_IDENTITY", None),
            "policy_loaded": self._policy_toml is not None,
            "policy_tools": len(self._tool_names),
            "declared_narrowers": sorted(self._declared_narrowers),
            "allowed_narrow": sorted(self._allowed_narrow),
            "fail_closed": self.mode == "enforce",
            "sessions": len(self._sessions),
        }

    @property
    def active(self) -> bool:
        """True when the engine is loaded and ready to participate."""
        return self.mode != "off" and self._engine_ready()

    def _engine_ready(self) -> bool:
        return self._native is not None and self._policy_toml is not None

    # ------------------------------------------------------------- session mgmt
    def _session_for(self, conversation_id: str) -> _SessionEntry | None:
        if not self._engine_ready():
            return None
        with self._sessions_lock:
            entry = self._sessions.get(conversation_id)
            if entry is None:
                if len(self._sessions) >= MAX_SESSIONS:
                    self._sessions.pop(next(iter(self._sessions)), None)
                try:
                    native = self._native.Session(
                        self._policy_toml,
                        json.dumps(self._tool_names),
                        "agentic-banking conversation",
                    )
                except Exception as exc:
                    logger.error(
                        "cannot open OpenAPPA session for %s: %s", conversation_id, exc
                    )
                    return None
                entry = _SessionEntry(conversation_id, native, self._allowed_narrow)
                self._sessions[conversation_id] = entry
            return entry

    # ------------------------------------------------------------------ native
    @staticmethod
    def _decision(raw: str) -> dict[str, Any]:
        return json.loads(raw)

    def _call_native(self, fn: Callable[[], Any]) -> Any:
        """Run a native call, translating engine refusals into TaintDenied."""
        try:
            return fn()
        except TaintDenied:
            raise
        except self._native.AppaError as exc:  # type: ignore[union-attr]
            cls = getattr(exc, "refusal_class", None)
            raise TaintDenied(f"OpenAPPA refusal {cls}: {exc}") from exc
        except Exception as exc:
            logger.error("OpenAPPA engine call failed: %s", exc)
            raise TaintDenied(f"OpenAPPA engine call failed: {exc}") from exc

    def _check_blocking(self, entry: _SessionEntry, tool: str, args: dict, call_id: str) -> dict:
        raw = self._call_native(lambda: entry.native.check(tool, args, call_id=call_id))
        return self._decision(raw)

    def _accept_narrowing(self, entry: _SessionEntry, call_id: str, offer: str) -> dict:
        ctl_id = f"ctl-{uuid.uuid4()}"
        raw = self._call_native(
            lambda: entry.native.check(CONTROL_TOOL, {"offer_id": offer}, call_id=ctl_id)
        )
        return self._decision(raw)

    # ---------------------------------------------------------- public helpers
    async def run_tool(
        self,
        canonical_tool: str,
        arguments: dict[str, Any],
        executor: Callable[[], Awaitable[Any]],
        conversation_id: str | None = None,
    ) -> Any:
        """Execute ``executor`` under the gate; return its (possibly admitted) result.

        Raises :class:`TaintDenied` when the policy blocks the call in enforce mode.
        """
        cid = conversation_id or current_conversation()

        if self.mode == "off":
            return await executor()

        # From here on the engine is expected to participate.  In enforce mode any
        # missing precondition fails closed instead of executing the tool.
        if cid is None:
            if self.mode == "enforce":
                raise TaintDenied("OpenAPPA: no conversation id pinned for a gated tool call")
            return await executor()

        if not self._engine_ready():
            if self.mode == "enforce":
                raise TaintDenied("OpenAPPA engine/policy unavailable in enforce mode")
            return await executor()

        entry = self._session_for(cid)
        if entry is None:
            if self.mode == "enforce":
                raise TaintDenied("cannot open OpenAPPA session in enforce mode")
            return await executor()

        call_id = str(uuid.uuid4())
        decision = await asyncio.to_thread(
            self._check_blocking, entry, canonical_tool, arguments, call_id
        )
        kind = decision.get("kind")

        if kind == "blocked":
            offers = decision.get("offer_ids") or []
            if canonical_tool in entry.allowed_narrow and offers:
                accepted = await asyncio.to_thread(
                    self._accept_narrowing, entry, call_id, offers[0]
                )
                if accepted.get("kind") == "control":
                    logger.info(
                        "appa_taint narrow accepted tool=%s conv=%s", canonical_tool, cid
                    )
                    decision = await asyncio.to_thread(
                        self._check_blocking, entry, canonical_tool, arguments, call_id
                    )
                    kind = decision.get("kind")
                else:
                    kind = "blocked"

        if kind == "blocked":
            feedback = decision.get("feedback", "policy refused this call")
            if self.mode == "enforce":
                logger.warning(
                    "appa_taint deny tool=%s conv=%s reason=%s",
                    canonical_tool,
                    cid,
                    feedback.replace("\n", " ")[:400],
                )
                raise TaintDenied(feedback)
            logger.info(
                "observe would_block tool=%s conv=%s reason=%s", canonical_tool, cid, feedback
            )
            # No dispatch was opened for a blocked call (the engine never admitted
            # it) — run the tool as a plain passthrough in observe mode.
            return await executor()

        if kind == "control":
            if self.mode == "enforce":
                raise TaintDenied(decision.get("reply", "authority review required"))
            return await executor()

        # kind == "allowed": a dispatch is open and owed an outcome.
        try:
            result = await executor()
        except BaseException:
            await self._abandon(entry, call_id)
            raise
        return await self._report(entry, call_id, result)

    async def recall_memory(
        self,
        conversation_id: str | None,
        executor: Callable[[], Awaitable[Any]],
        query: str | None = None,
    ) -> Any:
        """Gate a memory recall; narrow the conversation if untrusted records returned.

        ``memory.recall`` itself is a trusted read of bank-managed memory.  Only when
        the recalled records are marked untrusted is a synthetic ``memory.untrusted``
        narrowing event emitted so OpenAPPA lowers the conversation's trust.
        """
        result = await self.run_tool(
            "memory.recall", {"query": query}, executor, conversation_id=conversation_id
        )
        if has_untrusted_memory(result):

            async def _admit_untrusted() -> Any:
                return result

            await self.run_tool(
                "memory.untrusted",
                {"reason": "recalled memory carries untrusted provenance"},
                _admit_untrusted,
                conversation_id=conversation_id,
            )
        return result

    async def _abandon(self, entry: _SessionEntry, call_id: str) -> None:
        try:
            await asyncio.to_thread(entry.native.abandon, call_id)
        except Exception as exc:  # best effort; a failed outcome must not mask the real error
            logger.error("OpenAPPA abandon failed for %s: %s", call_id, exc)

    async def _report(self, entry: _SessionEntry, call_id: str, result: Any) -> Any:
        try:
            text = json.dumps(result, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            text = str(result)

        def _admit() -> dict:
            try:
                raw = self._call_native(lambda: entry.native.report(text, call_id=call_id))
                return self._decision(raw)
            except TaintDenied:
                raise
            except Exception as exc:
                logger.error("OpenAPPA result admission failed for %s: %s", call_id, exc)
                if self.mode == "enforce":
                    raise TaintDenied("OpenAPPA result admission failed") from exc
                return {"kind": "delivered", "content": text, "disposition": "admitted"}

        admitted = await asyncio.to_thread(_admit)
        content = admitted.get("content")
        replaced = admitted.get("disposition") not in (None, "admitted")
        if not replaced:
            return result
        try:
            return json.loads(content)
        except (TypeError, ValueError):
            return content


# Module-level singleton used by the hook points.
taint_gate = TaintGate()
