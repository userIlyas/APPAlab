# Local changes relative to Agentic Banking Lab base

Base: b9374e7faab6da0a5045f0f48ae63afd575dc76a. All source content is preserved unchanged in this snapshot.

## Modified tracked files

- `.env.example`
- `Dockerfile`
- `README.md`
- `docker-compose.yml`
- `docs/CONFIGURATION.md`
- `docs/MEMORY.md`
- `docs/RUNBOOK.md`
- `docs/TRAVEL_AGENT.md`
- `services/banking_agent/agents.py`
- `services/banking_agent/app.py`
- `services/banking_agent/clients.py`
- `services/banking_agent/skills.py`
- `services/common/llm.py`
- `services/common/mcp.py`
- `services/common/skill_memory.py`
- `services/common/travel.py`
- `services/memory_service/core.py`
- `tests/test_agent_context.py`
- `tests/test_llm_contract.py`
- `tests/test_memory_architecture.py`
- `tests/test_trace_payloads.py`

## Added source/integration files

- `configs/appa.toml`
- `docker-compose.appa.yml`
- `scripts/build_appa_wheel.sh`
- `services/common/appa_taint.py`
- `tests/test_appa_taint.py`

## Change groups

- OpenAPPA: Python gate, TOML policy, hooks in chat/MCP/memory/travel and both agent modes, fail-closed tests, opt-in Docker wheel install, separate APPA Compose and source build script.
- Provider migration already present locally: OPENROUTER_* for chat, EMBEDDING_* for vectorization, configurable timeouts/DDGS backend, corresponding docs/tests. These non-taint changes are retained too.
- OpenAPPA upstream: no source changes. All tracked source files included.
- Publication-only additions: root documentation, blank environment-name template, provenance/security/static checks, vendor/.gitkeep. Historical docs/scripts copied verbatim as non-executable .txt; result JSON and venv omitted.
- Executable bits use upstream Git index modes (WSL checkout modes are not authoritative); newly added wheel builder is executable. No source-byte changes.
- Excluded generated wheel SHA-256: 1651ebf84548189895cd38cc2894b6801dbc4ba810c8d729830abfc73d45d962. Original file remains untouched in the original workspace.
