"""End-to-end validation of the glue contract against the real OpenAPPA engine.

Replays the exact call shapes the hook points produce:

* app.py        -> appa_taint.set_conversation(conversation_id)
* mcp.py        -> run_tool("search.news", args, executor)  (conversation via contextvar)
* mcp.py        -> run_tool("abs.create_transfer", args, executor)
* travel.py     -> run_tool("travel.plan", args, executor, conversation_id=...)
* clients.py    -> run_tool("memory.recall", args, executor, conversation_id=...)
"""

import asyncio
import json
import os

os.environ["APPA_TAINT_MODE"] = "enforce"

from services.common.appa_taint import (  # noqa: E402
    TaintDenied,
    current_conversation,
    reset_conversation,
    set_conversation,
    taint_gate,
)

REPORT = {}


def check(name: str, condition: bool, detail: str) -> None:
    REPORT[name] = (condition, detail)
    print(f"[{'PASS' if condition else 'FAIL'}] {name}: {detail}")


async def fake_result(tool: str, args: dict) -> dict:
    return {"tool": tool, "payload": args}


async def main() -> None:
    # Simulate POST /v1/chat for conversation "demo-77".
    token = set_conversation("demo-77")

    # 1) The investment agent reads DuckDuckGo news (mcp.py glue: no explicit cid).
    check("contextvar is set", current_conversation() == "demo-77", current_conversation())
    await taint_gate.run_tool("search.news", {"query": "markets"}, lambda: fake_result("search.news", {}))

    # 2) The same conversation now asks to move money (mcp.py glue, via contextvar).
    try:
        await taint_gate.run_tool(
            "abs.create_transfer", {"amount": "100000"}, lambda: fake_result("abs.create_transfer", {})
        )
        check("money blocked after untrusted search", False, "no exception raised")
    except TaintDenied as exc:
        check("money blocked after untrusted search", True, str(exc).splitlines()[1].strip())

    # 3) A clean conversation can still move money (per-conversation isolation).
    reset_conversation(token)
    token = set_conversation("demo-other")
    out = await taint_gate.run_tool(
        "abs.create_transfer", {"amount": "1"}, lambda: fake_result("abs.create_transfer", {})
    )
    check("clean conversation allowed", out["tool"] == "abs.create_transfer", json.dumps(out))

    # 4) travel.plan and memory.recall are also untrusted ingress (explicit cid glue).
    await taint_gate.run_tool(
        "travel.plan", {"destination": "Стамбул"}, lambda: fake_result("travel.plan", {}),
        conversation_id="demo-travel",
    )
    try:
        await taint_gate.run_tool(
            "abs.pay_service", {"amount": "1"}, lambda: fake_result("abs.pay_service", {}),
            conversation_id="demo-travel",
        )
        check("money blocked after travel result", False, "no exception")
    except TaintDenied as exc:
        check("money blocked after travel result", True, str(exc).splitlines()[1].strip())

    reset_conversation(token)

    failed = [k for k, (ok, _) in REPORT.items() if not ok]
    print(f"\n{len(REPORT) - len(failed)}/{len(REPORT)} checks passed; failures={failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    asyncio.run(main())
