# Безопасность публикации и лабораторного запуска

## Что не переносится

Никакие рабочие `.env`, auth.json, live API keys/JWT/Keycloak secrets, private keys/certificates, DB dumps, клиентские данные, runtime logs/transcripts, Docker volumes, локальные venv/caches или wheel не входят в source snapshot. Исторические result JSON также не включены. Исходные ignored файлы сохранены на месте, не удалялись и не менялись.

Публичные учебные defaults и синтетические seed/benchmark/test данные **сохранены**, иначе это был бы уже другой стенд. Они находятся в upstream source/Compose/realm/example и не являются production credentials. В корневом env-шаблоне credential values пусты. Демонстрационные учётные данные нельзя использовать для настоящих систем.

## Выполненный review

- Снимок собран только из tracked + nonignored source файлов, не через копирование `.git` или всего home directory.
- Проверка pattern-based на provider keys, JWT, private-key/certificate markers, credential-bearing URLs/Slack tokens и запрещённые generated/credential файлы.
- Прямое сравнение файлов с текущими секретными значениями локального `.env` в памяти, без печати/сохранения значений. Known public lab defaults учитываются отдельно.
- Найденные 37 pattern matches изучены: upstream redaction/validation tests, synthetic sanitizer corpora, example AWS keys, dummy JWT, неполные невалидные key fragments, URL/parser false positives. Allowlist ограничен точными path/rule/value-SHA256 и hash всего файла, не whole-directory ignores.
- В реальных исходниках не найдено пригодных закрытых ключей/сертификатов. Строки `BEGIN PRIVATE KEY` в synthetic redaction fixtures — неполные dummy fragments, а не секретные ключи.
- Upstream MIT и отдельная OFL-лицензия встроенных Plex fonts сохранены. Binary media — только tracked upstream branding/documentation assets; просмотрены четыре демонстрационных UI-скриншота. Один публичный upstream-скриншот содержит имя/корпоративный адрес автора, не данные клиентов стенда. Локальные DB/клиентские данные не экспортировались.
- Новая Git-история начинается с чистой main, не содержит прежние object databases. Перед push проверяются все reachable blobs, diff, режимы файлов, nested gitlinks и полный manifest.

Это локальная эвристическая проверка + review, **не гарантия отсутствия любых секретов**, не результат Gitleaks/TruffleHog (они не установлены и не запускались). Высокоэнтропийные значения без известных форматов могут требовать дополнительного review. Allowlist и scanner требуют проверки при новых изменениях; не добавлять найденные значения в исключения автоматически.

## Эксплуатационные границы

- Только отдельный контролируемый лабораторный Docker daemon; никакого production, реальных банковских операций/PII/provider keys. Все endpoints при активных тестах должны вести на mock sinks; LLM-провайдер не является целью теста.
- APPA Compose включает диагностический transfer harness и использует общий backend base-стека. Изоляция контейнера не даёт изоляцию данных.
- Фиксированные имена/порты/сеть опасны при запуске второй копии на том же daemon; исходный builder очищает глобальные temp directories. Не запускать на исходном рабочем хосте.
- По умолчанию UI обращается к основному агенту без OpenAPPA enforcement; native-enforcement проверять отдельно, а не по UI.
- При любой неожиданной записи, cross-user/tenant данных, provider spend или alert: прекратить активный тест, сохранить минимальную отредактированную информацию, сообщить владельцу. Никаких real transfer для «доказательства», даже если gate должен отказать.
- Убедитесь, что Git diff/история не содержат локальные секретные файлы перед каждым push. Не публикуйте реальные credentials даже в private fork.

Известные ограничения безопасности/реализации перечислены отдельно в LIMITATIONS.md; эта публикация не заявляет обнаружение новой подтверждённой уязвимости.
