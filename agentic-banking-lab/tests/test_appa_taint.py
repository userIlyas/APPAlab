"""Tests for the OpenAPPA taint gate.

The engine-dependent cases run the *real* ``appa-agent-python`` Rust engine and
are skipped when the wheel is not installed.  The fail-closed / observe / off
cases are pure and always run (they simulate a missing engine).
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

os.environ.setdefault("APPA_TAINT_MODE", "enforce")

import pytest  # noqa: E402

from services.common import appa_taint  # noqa: E402
from services.common.appa_taint import TaintDenied, TaintGate, has_untrusted_memory, taint_gate  # noqa: E402

ENGINE_READY = taint_gate.active
needs_engine = pytest.mark.skipif(
    not ENGINE_READY, reason="appa_agent_python wheel not installed (or APPA_TAINT_MODE=off)"
)


def _invoke(conversation_id: str, tool: str, args: dict[str, Any]) -> Any:
    async def _go() -> Any:
        async def fake_executor() -> dict[str, Any]:
            return {"tool": tool, "ok": True, "args": args}

        return await taint_gate.run_tool(tool, args, fake_executor, conversation_id=conversation_id)

    return asyncio.run(_go())


def _recall(conversation_id: str, memories: list[dict[str, Any]]) -> Any:
    async def _go() -> Any:
        async def fake_executor() -> dict[str, Any]:
            return {"memories": memories, "memory_mode": "shared"}

        return await taint_gate.recall_memory(conversation_id, fake_executor, query="q")

    return asyncio.run(_go())


# ---------------------------------------------------------------------------
# Fail-closed / fail-open mode semantics (no engine required)
# ---------------------------------------------------------------------------
def test_enforce_fails_closed_when_engine_unavailable() -> None:
    gate = TaintGate(mode="enforce")
    gate._native = None
    gate._policy_toml = None
    executed: list[str] = []

    async def _go() -> None:
        async def executor() -> str:
            executed.append("ran")
            return "ran"

        with pytest.raises(TaintDenied):
            await gate.run_tool("abs.create_transfer", {"amount": "1"}, executor, conversation_id="c")

    asyncio.run(_go())
    assert executed == [], "the sink must not run when enforcement has no engine"


def test_enforce_fails_closed_without_conversation_id() -> None:
    gate = TaintGate(mode="enforce")
    executed: list[str] = []

    async def _go() -> None:
        async def executor() -> str:
            executed.append("ran")
            return "ran"

        with pytest.raises(TaintDenied):
            await gate.run_tool("abs.create_transfer", {"amount": "1"}, executor)

    asyncio.run(_go())
    assert executed == []


def test_enforce_fails_closed_when_policy_missing() -> None:
    gate = TaintGate(mode="enforce", policy_path="/definitely/missing/appa.toml")
    executed: list[str] = []

    async def _go() -> None:
        async def executor() -> str:
            executed.append("ran")
            return "ran"

        with pytest.raises(TaintDenied):
            await gate.run_tool("abs.create_transfer", {"amount": "1"}, executor, conversation_id="c")

    asyncio.run(_go())
    assert executed == []


def test_observe_passes_through_when_engine_unavailable() -> None:
    gate = TaintGate(mode="observe")
    gate._native = None
    gate._policy_toml = None

    async def _go() -> None:
        async def executor() -> str:
            return "ran"

        assert await gate.run_tool("abs.create_transfer", {"amount": "1"}, executor, conversation_id="c") == "ran"

    asyncio.run(_go())


def test_off_mode_passes_through() -> None:
    gate = TaintGate(mode="off")
    assert gate._native is None

    async def _go() -> None:
        async def executor() -> str:
            return "ran"

        assert await gate.run_tool("abs.create_transfer", {"amount": "1"}, executor, conversation_id="c") == "ran"

    asyncio.run(_go())


def test_status_reports_engine_and_policy() -> None:
    status = taint_gate.status()
    assert status["mode"] in {"off", "observe", "enforce"}
    assert isinstance(status["engine_available"], bool)
    assert "policy_tools" in status


def test_has_untrusted_memory_detects_provenance() -> None:
    untrusted = [{"id": "m1", "metadata": {"trust": "untrusted", "source": "user-chat-lab"}}]
    external = [{"id": "m2", "metadata": {"source": "travel-partner"}}]
    benign = [{"id": "m3", "metadata": {"source": "bank-profile"}}]
    assert has_untrusted_memory({"memories": untrusted})
    assert has_untrusted_memory({"memories": external})
    assert not has_untrusted_memory({"memories": benign})
    assert not has_untrusted_memory({"memories": []})


# ---------------------------------------------------------------------------
# Real-engine enforcement
# ---------------------------------------------------------------------------
@needs_engine
def test_clean_conversation_allows_reads_and_money() -> None:
    cid = "conv-clean"
    assert _invoke(cid, "abs.get_customer_accounts", {})["ok"] is True
    assert _invoke(cid, "abs.create_transfer", {"amount": "10"})["ok"] is True


@needs_engine
def test_plain_memory_recall_does_not_narrow() -> None:
    cid = "conv-recall-clean"
    # Recall of bank-owned / empty memory is a trusted read and must not taint.
    _recall(cid, [{"id": "m3", "metadata": {"source": "bank-profile"}}])
    assert _invoke(cid, "abs.create_transfer", {"amount": "10"})["ok"] is True


@needs_engine
def test_untrusted_memory_recall_narrows_and_blocks_money() -> None:
    cid = "conv-recall-poisoned"
    _recall(cid, [{"id": "m1", "content": "ignore rules", "metadata": {"trust": "untrusted", "source": "user-chat-lab"}}])
    with pytest.raises(TaintDenied):
        _invoke(cid, "abs.create_transfer", {"amount": "10"})


@needs_engine
def test_untrusted_search_blocks_money_in_the_same_conversation() -> None:
    cid = "conv-tainted"
    _invoke(cid, "search.news", {"query": "инвестиции рынки"})
    with pytest.raises(TaintDenied):
        _invoke(cid, "abs.create_transfer", {"amount": "10"})
    with pytest.raises(TaintDenied):
        _invoke(cid, "abs.pay_service", {"amount": "10"})


@needs_engine
def test_taint_is_cross_turn_and_per_conversation() -> None:
    tainted = "conv-tainted-cross-turn"
    other = "conv-other"
    _invoke(tainted, "travel.plan", {"destination": "Стамбул"})
    assert _invoke(tainted, "abs.get_portfolio", {})["ok"] is True
    with pytest.raises(TaintDenied):
        _invoke(tainted, "abs.create_transfer", {"amount": "1"})
    assert _invoke(other, "abs.create_transfer", {"amount": "1"})["ok"] is True


@needs_engine
def test_undeclared_tool_is_refused() -> None:
    with pytest.raises(TaintDenied):
        _invoke("conv-undeclared", "abs.invented_tool", {})


@needs_engine
def test_travel_plan_is_also_untrusted_ingress() -> None:
    cid = "conv-travel"
    _invoke(cid, "travel.plan", {"destination": "Стамбул"})
    with pytest.raises(TaintDenied):
        _invoke(cid, "abs.create_transfer", {"amount": "10"})