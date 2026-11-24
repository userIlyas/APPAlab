# Переменные окружения

Корневой `.env.example` содержит **65 имён** с пустыми значениями: все `${...}` входы двух Compose + настройки wrapper/build. Полный машинный список: `provenance/compose-environment-names.txt`. Значения прежнего `.env` не перенесены. Исходный `agentic-banking-lab/.env.example` сохранён как исторически рабочий учебный пример с публичными demo-defaults.

## Провайдеры

- `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `OPENROUTER_MODEL`: общий Chat Completions endpoint. Код требует непустой ключ даже для локального mock; используйте canary, не production API key.
- `BANKING_OPENROUTER_{API_KEY,BASE_URL,MODEL}`, `TRAVEL_OPENROUTER_{API_KEY,BASE_URL,MODEL}`, `MEMORY_OPENROUTER_{API_KEY,BASE_URL,MODEL}`: system overrides, пустое значение использует общие значения.
- `OPENROUTER_JSON_MODE`, `OPENROUTER_TIMEOUT_SECONDS`: формат/таймаут. Endpoint compatibility и существование модельного id требуют отдельной проверки; observed id не подтверждает доступность.
- `EMBEDDING_API_KEY`, `EMBEDDING_BASE_URL`, `EMBEDDING_MODEL`, `EMBEDDING_TIMEOUT_SECONDS`: отдельный `/embeddings`, не Chat Completions. Непустой ключ нужен коду. На наблюдённом стенде embedding key пуст; `/health` памяти не доказывает готовность embed.

## Taint Tracking

| Имя | Фактическое назначение |
|---|---|
| `APPA_TAINT_MODE` | off по умолчанию в Python; off/observe/enforce. Только appa Compose передаёт его (default enforce); основной Compose — нет |
| `APPA_TAINT_POLICY` | путь внутри runtime-контейнера/процесса, default configs/appa.toml относительно source; не прокидывается исходным Compose автоматически |
| `APPA_TAINT_ALLOW_NARROW` | JSON array имён auto-accept narrowing; default memory.untrusted/search.text/search.news/travel.plan; пересекается с policy narrowers; Compose не прокидывает |
| `APPA_TAINT_MAX_SESSIONS` | размер per-process cache, default 4096; Compose не прокидывает |
| `APPA_TAINT_E2E_HARNESS` | runtime-флаг диагностического transfer endpoint; appa Compose жёстко устанавливает 1. Не настраивается через `.env` в сохранённом Compose |
| `APPA_BUILD_RUST_IMAGE` | shell-переменная wheel builder, default rust:1.96-bookworm; export в терминале, не чтение `.env` |
| `APPA_TAINT_INSTALL` | **build ARG**, не runtime env: 1 устанавливает wheel; appa Compose задаёт 1, base Dockerfile default 0 |

Последние два флага install/harness не являются `${...}` входами Compose, поэтому не включены как настраиваемые ключи корневого шаблона. Не путайте доступность native-модуля и включённый gate.

## Identity и хранилища

`POSTGRES_PASSWORD`, `MONGO_ROOT_PASSWORD`, `KEYCLOAK_ADMIN_PASSWORD`; `KEYCLOAK_{BANKING_AGENT,BANK_MCP,BANK_MCP_VULNERABLE,TRAVEL_AGENT,MEMORY_OPERATOR,OPERATIONS_SKILL,INVESTMENT_SKILL,TRAVEL_SKILL}_SECRET`. Конфигуратор/realm/сервисы должны получать согласованные значения. `AUTH_DISABLED` предназначен только для изолированных тестов.

`BANKING_LANGFUSE_{PUBLIC_KEY,SECRET_KEY}`, `TRAVEL_LANGFUSE_{PUBLIC_KEY,SECRET_KEY}`, `MEMORY_LANGFUSE_{PUBLIC_KEY,SECRET_KEY}`, `LANGFUSE_INIT_USER_PASSWORD`, `LANGFUSE_ENCRYPTION_KEY`, `LANGFUSE_SALT`, `LANGFUSE_NEXTAUTH_SECRET`, `SEAWEEDFS_ACCESS_KEY`, `SEAWEEDFS_SECRET_KEY`. На пустой новой БД init создаёт учебные проекты. В Compose остаются некоторые жёсткие demo-значения (в т.ч. Redis/ClickHouse), не параметры production-секретов.

## Поведение сервисов

`BANKING_AGENT_MODE` (основной Compose default orchestrator; APPA фиксирует legacy), `ABS_MCP_MODE`, `SKILL_MEMORY_MODE`, `MEMORY_ORCHESTRATION_INTERVAL_SECONDS`, `MEMORY_HTTP_TIMEOUT_SECONDS`, `TRAVEL_HTTP_TIMEOUT_SECONDS`, `BANK_TIMEZONE`, `DOCKER_DNS_SERVER`, `DDGS_TEXT_BACKEND`.

`FLIGHTS_PROVIDER`, `TUTU_MCP_URL`, `MOCK_FLIGHTS_MCP_URL`, `FLIGHTS_MCP_AUTH_TOKEN`, `FLIGHTS_MOCK_NOTE`: внешний или локальный flight provider и включённый fixture. `ABS_MCP_URL`, `ABS_MCP_VULNERABLE_URL`, `MEMORY_URL`, `TRAVEL_AGENT_URL` переопределяются в основном Compose; APPA использует свои фиксированные внутренние адреса.

## Внутренние env, не входы host `.env`

Compose задаёт `PORT`, `APP_MODULE`/`SERVICE_PACKAGE` через build, `AGENT_SYSTEM_ID`, `EXPECTED_AUDIENCE`, `ALLOWED_AZP`, Keycloak issuer/internal/JWKS URLs, `SERVICE_CLIENT_ID`/`SERVICE_CLIENT_SECRET`, `MONGODB_URL`, `DATABASE_URL`, Langfuse URLs/project IDs и другие service-specific значения. Их inventory есть в исходном Compose; не нужно копировать runtime `docker inspect .Config.Env` в Git или публиковать его целиком.
