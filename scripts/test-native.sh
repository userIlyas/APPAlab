#!/usr/bin/env bash
# Real native engine + in-memory fake tools only; no HTTP agent/MCP/provider calls.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
export APPA_TAINT_MODE=enforce PYTHONDONTWRITEBYTECODE=1
export APPA_TAINT_POLICY="${ROOT}/agentic-banking-lab/configs/appa.toml"
export APPA_TAINT_ALLOW_NARROW='["memory.untrusted","search.text","search.news","travel.plan"]'
export APPA_TAINT_MAX_SESSIONS=4096
export PYTHONPATH="${ROOT}/agentic-banking-lab"
cd "${ROOT}/agentic-banking-lab"
"${PYTHON}" -c 'from services.common.appa_taint import taint_gate; s=taint_gate.status(); assert s["engine_available"] and s["policy_loaded"] and s["fail_closed"], s; print(s)'
for repetition in 1 2 3; do
  printf '\nNative validation repetition %s/3\n' "${repetition}"
  "${PYTHON}" -m pytest tests/test_appa_taint.py -q -p no:cacheprovider
  "${PYTHON}" "${ROOT}/integration/validation.py"
done
