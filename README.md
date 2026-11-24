# APPAlab — Agentic Banking Lab + OpenAPPA

Первый исходный снимок локальной интеграции банковского агентного стенда с OpenAPPA и существующей Python/Rust-обвязкой Taint Tracking. Интеграция сохранена **без рефакторинга**.

> Лабораторный стенд, не банковский продукт. Содержит намеренно уязвимые маршруты и публичные демонстрационные пароли/синтетические записи. Только изолированное окружение, без настоящих счетов, PII и production-ключей.

## Что включено

```text
agentic-banking-lab/  Python/FastAPI/LangGraph, MCP, A2A, UI, Compose, политика, тесты
OpenAPPA/            полный исходный снимок upstream 0.46.1 (Rust + PyO3)
integration/         offline glue-проверка; исторические материалы как *.txt
scripts/             статическая проверка и проверка публикации
provenance/          исходные SHA, отличия, runtime-инвентарь, состав публикации
docs/                архитектура, запуск, настройки, проверки, ограничения
```

OpenAPPA работает **в процессе** `banking-agent-appa` как `appa_agent_python`, а не как sidecar. `Session.check` допускает вызов до executor, `report` принимает результат. Политика требует `trusted` для трёх денежных инструментов и понижает доверие при определённых недоверенных чтениях.

## Начать

1. Прочитайте [ограничения](docs/LIMITATIONS.md) и [правила безопасности](docs/SECURITY.md).
2. [Развёртывание на чистом хосте](docs/DEPLOYMENT.md): собрать wheel из `OpenAPPA/`, затем основной Compose и отдельный APPA Compose.
3. [Проверки без банковских операций](docs/VALIDATION.md).

Основной агент: `127.0.0.1:8000`, UI: `127.0.0.1:3000` (направлен на основной агент).
APPA-агент: `127.0.0.1:8009`, `BANKING_AGENT_MODE=legacy`, `APPA_TAINT_MODE=enforce` по умолчанию его Compose. Основной Compose **не включает enforcement**.

## Статус проверки снимка

Пассивная проверка локального окружения 2026-11-24 UTC: основной стек запущен; APPA-контейнер остановлен (exit 255). Его 20 Python-файлов, политика и wheel совпали с локальными файлами по SHA-256. Причина остановки не установлена. Контейнер не запускался и не изменялся при подготовке публикации.

Offline gate: **14/14, n=3**; glue: **4/4, n=3**, реальный ранее собранный нативный движок, fake-исполнители. Это не новый HTTP E2E. Полная сборка из чистого окружения и `/v1/chat` **UNVERIFIED**. В частности, имена search-инструментов в политике и MCP расходятся; это сохранено, а не исправлено.

## Документы

- [Архитектура и потоки данных](docs/ARCHITECTURE.md)
- [Переменные окружения](docs/CONFIGURATION.md)
- [Версии, происхождение и локальные изменения](docs/PROVENANCE.md)
- [Проверки и пределы воспроизводимости](docs/VALIDATION.md)
- [Ограничения первой версии](docs/LIMITATIONS.md)
- [Перечень публикуемых файлов](provenance/PUBLICATION-FILES.txt)

## Upstream и лицензии

- [LLAMATOR-Core/agentic-banking-lab](https://github.com/LLAMATOR-Core/agentic-banking-lab), `b9374e7faab6da0a5045f0f48ae63afd575dc76a` + сохранённые локальные изменения; [MIT](agentic-banking-lab/LICENSE), © 2026 Timur Nizamov.
- [archestra-ai/OpenAPPA](https://github.com/archestra-ai/OpenAPPA), `ada9b33e227537c092f973c89ab42151a3d9f2c3`, 0.46.1, без изменений исходников; [MIT](OpenAPPA/LICENSE.md), © 2026 Archestra Inc.

Снимки vendored в обычном monorepo; вложенных `.git` и submodules нет. Полная upstream-история не импортирована. Уведомления upstream сохранены; см. [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
