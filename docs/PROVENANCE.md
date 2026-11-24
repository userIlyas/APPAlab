# Происхождение и выбранная структура

## Почему monorepo с vendored source snapshots

Будущие правки возможны в обвязке и обоих upstream. Submodules потребовали бы сначала отдельно опубликовать текущие незакоммиченные изменения и поддерживать несколько fork remote. В первой публикации важнее самодостаточный source tree и один PR. Поэтому обычные директории `agentic-banking-lab/` и `OpenAPPA/`, без вложенных Git-репозиториев, без бинарной подмены исходников и без upstream-историй.

| Каталог | Upstream / локальная ветка | Базовый commit | Состояние снимка |
|---|---|---|---|
| agentic-banking-lab | LLAMATOR-Core/agentic-banking-lab / main | b9374e7faab6da0a5045f0f48ae63afd575dc76a | 104 tracked файла (21 изменён) + 5 новых исходных файлов |
| OpenAPPA | archestra-ai/OpenAPPA / main | ada9b33e227537c092f973c89ab42151a3d9f2c3 | все 1343 tracked файла, byte-for-byte; workspace 0.46.1 |
| integration | локальный openappa-abl без Git | N/A | validation.py + исторические docs/HTTP scripts как .txt |

Исходные checkout, `.env`, их Git index/history и незакоммиченные файлы не заменялись. Их содержимое осталось в прежнем окружении. Исключённый wheel по-прежнему находится в исходном workspace; это осознанное исключение артефакта, не потеря исходного кода.

`provenance/source-snapshot.json` — SHA-256 каждого из **1452 исходных файлов**, базовые commits, upstream URLs, ветки, исходный Git status, перечень сгенерированных исключений и Git executable modes. Список локальных изменений: `provenance/LOCAL-CHANGES.md`. Новая `.gitkeep` лишь сохраняет пустой `vendor/`, обязательный Dockerfile.

Основные группы локальных изменений: OpenAPPA gate/hooks/policy/tests; Docker native install/isolated Compose/builder; уже существовавшая миграция `OPENROUTER_*` и `EMBEDDING_*`, таймауты/поиск и обновлённые документы/тесты. Сохранены **все** эти изменения, не только taint.

Для последующих обновлений используйте отдельный upstream clone, сравнивайте новый pinned commit с указанной базой, переносите изменения с review и обновляйте provenance. Этот снимок не обещает автоматическую синхронизацию и не импортирует чужие Git hooks/refs. Вложенные `.github` upstream сохранены как исходный код, но не являются root Actions workflow APPAlab.

## Проверка фактических контейнеров

`provenance/runtime-inventory.json` содержит только отфильтрованные metadata: состояния, image ids/digests, сети, mounts, безопасные значения выбранных env, факт наличия provider key без его значения, сравнение исходников и 77 имён/версий Python packages APPA-образа. Никаких `.Config.Env` целиком, токенов, логов, DB/volume data.

- Основной проект: 24 контейнера, из них 23 running и одноразовый keycloak-configurator exited (0). Их Python common MCP/memory/travel-код предшествует taint-вставкам.
- Отдельный APPA: `sha256:eee53803eceaeec8ed07b026cd0e263e8e09cc576bdbbd8d31fca71790893070`, exited (255), без mounts. Все 20 найденных Python source files и политика совпадают с копируемым рабочим деревом. В образе установлен wheel 0.46.1, идентичный локальному по SHA-256.
- Native `.so` в APPA-контейнере, wheel и тестовой venv имеет одинаковый SHA-256: `324b973dd580b831bd8e3e135cb32a69bc751512c8122f32f807e99eb44a058b`.
- `provenance/requirements-observed.txt` — наблюдение из установленного контейнера, **не проверенный pip lock**; source requirements остаются прежними диапазонами.

Локальные application image ids/digests — доказательство идентичности наблюдённых артефактов, **не публично доступные registry releases** и не инструкции `docker pull`. Base third-party registry digests сохранены где Docker их предоставил. Создавать образы нужно из source.

## История публикации и лицензии

APPAlab начинается с новой минимальной main-ветки и отдельной initial-publication PR-ветки. Старые upstream Git object databases, ignored `.env`, caches, wheels, result JSON, дампы/volumes в эту историю не входят. Публикуются только новые проверенные коммиты. Их reachable blobs отдельно проверяются перед push.

Обе upstream MIT-лицензии и copyright notices сохранены в исходных каталогах; см. THIRD_PARTY_NOTICES.md. Происхождение оригинальных локальных правок обозначено как local working changes, без выдумывания upstream-коммитов или авторства.
