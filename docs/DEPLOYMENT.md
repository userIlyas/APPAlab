# Развёртывание с чистого окружения

## Граница применимости

**Только отдельный чистый хост/VM/WSL-профиль с отдельным Docker daemon.** Не выполнять `up`, `build` или исходный wheel builder рядом с работающим исходным стендом: Compose содержит фиксированные имена проекта/контейнера/сети, порты и теги образов. `-p other` недостаточно из-за hard-coded `container_name` и external network. Эти настройки намеренно не переписаны.

Пошаговый исходный процесс ниже восстановлен по коду; **полное развёртывание из нуля в рамках публикации не выполнено**. Offline Cargo preflight в чистом временном контейнере завершился 101: нет `reqwest` в Cargo cache/index. Нужны разрешённые загрузки зависимостей и отдельная проверка старта. Диапазоны Python/maturin и mutable image tags не гарантируют побитно одинаковые образы.

## Предварительные требования

- Linux/WSL2 + работающий Docker Engine/Desktop и Compose v2+; фактически наблюдались Engine 29.9.2 / Compose 5.6.1.
- Для исходного wheel-процесса — Linux x86_64/glibc; исходный Rust-образ `rust:1.96-bookworm` (наблюдён digest `sha256:a339861ae23e9abb272cea45dfafde21760d2ce6577a70f8a926153677902663`). На другой архитектуре нужна отдельная сборка/проверка.
- Git, Bash, tar; Python 3.12+ для локальных проверок (или совместимый CPython ≥3.11 для wheel-only теста; наблюдён Python хоста 3.14.10).
- Доступ для скачивания Docker base images, Debian apt, PyPI, crates.io. Секреты для сборки не нужны.
- Только контролируемые локальные OpenAI-compatible LLM и embeddings endpoints для полного chat-сценария; никакие провайдерские API при проверке публикации не вызывались. Tutu/DDG — внешние сервисы; без отдельного разрешения не тестировать.

## 1. Получить исходники и подготовить собственную конфигурацию

После merge PR:

```bash
git clone https://github.com/userIlyas/APPAlab.git
cd APPAlab
python3 scripts/verify_snapshot.py
# Только в свежем checkout: никогда не перезаписывать существующую .env.
test ! -e agentic-banking-lab/.env && cp .env.example agentic-banking-lab/.env
```

До merge используйте явно одобренную PR-ветку. Все исходники OpenAPPA уже есть — никаких submodule init и соседних private clones не нужно.

В новом собственном `.env` настройте нужные параметры согласно [CONFIGURATION](CONFIGURATION.md). Файл-шаблон в корне содержит имена и пустые значения, не секреты. Публичные demo-defaults остаются в Compose/realm/исходном example; это не безопасные production-настройки. Не копируйте `.env` исходного стенда. Для безопасного локального travel backend задайте `FLIGHTS_PROVIDER=mock`; это не отключает автоматически DDG.

## 2. Собрать OpenAPPA wheel из включённых исходников

```bash
cd agentic-banking-lab
# ВНИМАНИЕ: исходный скрипт очищает /tmp/appa-build и /tmp/appa-dist.
# Только чистая VM, без параллельной сборки и без чужих данных в этих каталогах.
bash scripts/build_appa_wheel.sh ../OpenAPPA
```

Скрипт копирует OpenAPPA без `.git` и `target` во временную директорию; исходный каталог должен называться **OpenAPPA**. Он запускает Rust-контейнер, устанавливает python3/python3-venv/python3-pip через apt, maturin `>=1.9,<2`, затем `maturin build --release --out /dist`. Результат копируется в `vendor/appa_agent_python-*.whl`.

Для фиксации базового образа можно передать **экспортированную shell-переменную** `APPA_BUILD_RUST_IMAGE=rust@sha256:a339861ae23e9abb272cea45dfafde21760d2ce6577a70f8a926153677902663`; `.env` этот Bash-скрипт сам не читает. Исходники Rust включают Cargo.lock, но исходный скрипт не задаёт `--locked`. Release profile не требует `APPA_RELEASE_REF`: не устанавливайте upstream release/publishing-переменные для этой development-binding сборки.

Прежний wheel: `appa_agent_python-0.46.1-cp311-abi3-manylinux_2_34_x86_64.whl`, SHA-256 `1651ebf84548189895cd38cc2894b6801dbc4ba810c8d729830abfc73d45d962`. Это контрольная сумма **наблюдённого старого артефакта**, не обещание идентичного rebuild. Wheel и локальные Docker images не публикуются и не нужны как замена исходникам.

## 3. Проверить движок без инфраструктуры и операций

Из корня APPAlab, в отдельной локальной venv:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install 'pytest>=8.4,<9' 'pytest-asyncio>=1.2,<2' agentic-banking-lab/vendor/appa_agent_python-*.whl
PYTHON="$PWD/.venv/bin/python" bash scripts/test-native.sh
```

Установка этих пакетов касается только `.venv` свежего checkout. `test-native.sh` требует загруженный движок/политику и запускает три повторения gate + glue с fake-executor. Сеть/Keycloak/АБС для тестов не нужны.

## 4. Собрать и запустить Docker — только на чистом хосте

Из `agentic-banking-lab/`:

```bash
docker compose --env-file .env -f docker-compose.yml config --quiet
docker compose --env-file .env -f docker-compose.yml build
docker compose --env-file .env -f docker-compose.yml up -d
# Основной стек должен создать agentic-banking_banking и пройти свои dependencies.
docker compose --env-file .env -f docker-compose.appa.yml build
docker compose --env-file .env -f docker-compose.appa.yml up -d
```

Не объединяйте файлы через `-f base -f appa` без анализа: исходный APPA Compose предназначен как **отдельный** проект, присоединяющийся к сети base. Основные Python-сервисы собираются без native install (ARG default `0`), APPA — с `APPA_TAINT_INSTALL=1`; `vendor/` и `configs/` должны существовать даже для обычной сборки.

Первый запуск создаёт собственные DB volumes/демо-записи, выполняет realm import и keycloak-configurator. Данные из прежних volumes не нужны и не включены. APPA-контейнер использует общие с новым base-стеком сервисы; он не является отдельным банком/tenant.

## 5. Приёмка нового развёртывания

Проверки/ожидаемые поля — [VALIDATION](VALIDATION.md). Перед любыми HTTP-проверками подтвердите владельца нового экземпляра, точный scope и отсутствие production-интеграций. Диагностический `/v1/appa/e2e/transfer` **не вызывать**: даже синтетический transfer пишет в ledger.

На новом разрешённом стенде `/health` APPA должен показывать `enforce`, engine/policy available, 14 tools, fail_closed. Это только состояние gate, не полный chat-тест. UI на 3000 ведёт на основной агент 8000; APPA API — 8009.

Не считать запуск успешным по одному `docker ps` или старым отчётам. Нужны новая сборка, health, offline controls и отдельно согласованный mock-only полный E2E; search-name mismatch и embedding-зависимость остаются известными ограничениями.
