## Первая публикация APPAlab

Самодостаточный monorepo со снимками Agentic Banking Lab (`b9374e7` + все локальные source changes), OpenAPPA 0.46.1 (`ada9b33e`) и существующей Taint Tracking обвязкой. Без рефакторинга, submodules, переноса старой Git-истории или бинарной подмены исходников.

- Включены Python/Rust исходники, Compose/Dockerfile, taint policy, тесты, source hashes, runtime inventory, документация запуска/ограничений и upstream MIT/OFL notices.
- Wheel, `.env`, credentials, DB/volumes, confidential runtime logs и прежние result JSON исключены.
- Реальный native engine: gate 14/14 и glue 4/4, по три свежих процесса; только fake-executors, без HTTP/LLM/ledger операций.
- Static source integrity/Compose/build input checks прошли. Нативный модуль тестовой venv совпадает с наблюдённым контейнером и wheel по SHA-256.
- Pattern scan + reviewed exact synthetic fixture allowlist; локальные secret-value comparisons; перед отправкой — сканирование reachable Git blobs.

### Ограничения (не исправлялись)

Полная чистая сборка и `/v1/chat` не подтверждены; offline Cargo preflight не нашёл reqwest. APPA-контейнер при инвентаризации остановлен (255), основной стек запущен без enforcement. Имена настоящего search MCP и policy расходятся. На наблюдённом стенде embedding key пуст. Taint неперсистентен, cache eviction забывает состояние; audience/identity binding не реализованы. APPA diagnostic endpoint способен писать в общий ledger; старые HTTP E2E сохранены только как неисполняемый архив.

Подробности и source rebuild instructions: README и docs/. Эта версия фиксирует существующий результат, а не заявляет production-ready безопасность или исправление известных ограничений. Действующий стенд и его volumes не изменялись.
