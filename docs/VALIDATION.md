# Проверка снимка и интеграции

## Новые проверки при подготовке публикации

| Проверка | Результат / что доказывает |
|---|---|
| SHA-256 source snapshot | 1452/1452 файлов, без изменения source bytes |
| Python syntax | 75 банковских/glue/publication Python файлов компилируются без import/pyc |
| JSON / TOML | 2 банковских JSON, 6 выбранных TOML/Cargo.lock разобраны |
| Compose config | base 24 сервиса, APPA 1; build contexts, SERVICE_PACKAGE, bind sources существуют; `.env` оператора не использован |
| Gate real engine | 14 passed, n=3 свежих Python процессов; ни одного skip |
| Glue contract | 4/4, n=3 свежих процессов; ContextVar, tainted deny, clean control, partner narrowing |
| Native artifact identity | установленная venv `.so` = wheel `.so` = container `.so`, SHA-256 см. PROVENANCE |
| Offline Cargo preflight | **не прошёл**, exit 101: нет `reqwest` в пустом Cargo cache/index; это не дефект source, но чистая сборка не подтверждена |
| Работающий полный chat / HTTP E2E | **не запускался**, UNVERIFIED; запрещены операции на основном стенде |
| Полный banking pytest suite / весь Rust workspace | не запускались; native-only venv не содержит FastAPI/LangGraph и полного dev-набора; новые зависимости не устанавливались |
| `git diff --check` | exit 2: 24 whitespace notices в четырёх сохранённых source-файлах (upstream Markdown hard breaks/trailing space и blank EOF); новые publication-файлы без notices. Source bytes намеренно не переформатированы |

Наблюдённый native test runtime: CPython 3.14.10, pytest 9.2.0, appa-agent-python 0.46.1, `BINDING_IDENTITY=appa-agent-python-v9`. Это существовавшая venv, **не** clean install; pytest отличается от банковского requirements-dev (`<9`). В каждом gate run был warning `Unknown config option: asyncio_mode` (pytest-asyncio отсутствует); все 14 выбранных тестов синхронные и используют `asyncio.run`, skips отсутствуют. Рекомендованная чистая venv в DEPLOYMENT использует объявленный dev-диапазон и требует самостоятельного подтверждения.

Модель, system prompt, temperature/seed: N/A, LLM не вызывается; native engine детерминированный, UUID call IDs случайные и не участвуют в asserted policy decisions. Каждое повторение — отдельный процесс и временные Session stores, не старый кэш. Входы и fake tool traces заданы точно в `tests/test_appa_taint.py` и `integration/validation.py`; SHA-256 тестов, wrapper и политики доступны в source snapshot. Локальный журнал подготовки содержит команды, timestamps, outputs, hashes и verdict; сырые HTTP-результаты прежних запусков не публикуются.

## Повторить без внешних сервисов

```bash
python3 scripts/verify_snapshot.py
# После source-сборки wheel и установки в отдельную .venv:
PYTHON="$PWD/.venv/bin/python" bash scripts/test-native.sh
python3 scripts/check_publication.py
```

`test-native.sh` сначала требует загруженную policy/native engine, чтобы engine-dependent skips не выдать за успешный enforcement. Он не запускает агентный HTTP-сервер, не получает токены, не обращается к MCP/провайдеру и не пишет ledger. Допустимые executors — только Python fake-функции с canary dictionaries.

Контроли: чистый диалог допускает fake transfer; загрязнённый отклоняет тот же тип sink; другой диалог остаётся чистым; off/observe passthrough; enforce с отсутствующим native/policy/conversation не вызывает fake sink. Это не доказательство всех конкурентных сценариев, recovery после restart или cross-tenant изоляции.

## Дополнительная приёмка только нового разрешённого стенда

После согласования exact instance/model/tools/test tenant и mock sinks, на отдельном Docker daemon:

1. Выполнить source rebuild по DEPLOYMENT, записать versions/base digests/dependency lock.
2. Подтвердить APPA `/health`: mode enforce, engine_available/policy_loaded/fail_closed true, engine identity, 14 tools. Не вызывать transfer endpoint.
3. Проверить поиск через mock MCP: реальные wire names должны совпасть с policy (в этом снимке **не совпадают**).
4. Подключить контролируемые embedding и LLM fixtures, проверить `/v1/chat` с in-memory money sinks, повторить controls и записать n/N. Такой harness здесь ещё не реализован.

Не выполнять исторические HTTP E2E: они создают ledger transfer и могут вызывать внешние LLM/поиск. Они сохранены только как `.txt`. Старые утверждения 8/8 не переизданы как результаты новых проверок.

## Секреты и история

```bash
python3 scripts/check_publication.py --history
# Только локально, путь к собственному секретному файлу; значения не печатаются:
python3 scripts/check_publication.py --history --private-env /path/to/operator/.env
```

Проверка только эвристическая; reviewed synthetic fixtures — точные fingerprints в allowlist. Новые неразобранные совпадения блокируют публикацию. `--history` сканирует blobs всех локальных refs, а не только текущий diff. Scanner не открывает сеть и не проверяет валидность токенов у провайдера.
