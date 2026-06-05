Сделай отдельный internal TTS service, который живет своей жизнью: принимает текст и выбранный голос, синтезирует речь локальной моделью и возвращает готовый `ogg/opus`-аудиофайл. Сервис должен быть автономным и запускаться в пустом отдельном проекте, где есть только его собственный devcontainer/runtime files.

Контекст:

- сервис должен быть самостоятельным
- старый прототип TTS уже существовал, но был слишком сцеплен со старым монолитом; полезные идеи оттуда можно переиспользовать, архитектурную связанность переносить нельзя
- никакой предметной области клиента внутри сервиса быть не должно

Главная цель:

- поднять отдельный TTS service, который:
  - знает ограниченный набор заранее разрешенных голосов
  - умеет синтезировать речь из присланного текста
  - возвращает результат как `audio/ogg` c `opus`
  - может жить на VPS как internal-only контейнер без публичного домена

Service boundaries:

- сервис не должен зависеть от какого-либо внешнего монолита
- сервис не должен импортировать код чужого приложения
- сервис не должен требовать чужую базу данных
- сервис не должен требовать чужой `.env`
- сервис не должен знать ничего о доменных сущностях клиента
- сервис не должен открывать публичный HTTP route наружу, если это не отдельное явно принятое решение

Функциональные требования:

1. Independent runtime

- сервис стартует сам по себе отдельным процессом/контейнером
- сервис не требует token-ов чужого приложения
- сервис не зависит от внешней БД

2. Voices

- у сервиса есть фиксированный конфигом список доступных голосов
- один голос считается default voice
- сервис должен уметь вернуть список доступных голосов через API
- запрос на неизвестный голос должен fail closed с `400`, а не тихо падать на default

3. Synthesis

- основной вход: `text + voice_id`
- сервис должен нормализовать текст перед синтезом:
  - trim
  - collapse repeated whitespace
- пустой текст запрещен
- нужен ограничитель длины текста через env-конфиг
- результат синтеза должен быть в `ogg/opus`, а не в wav/mp3 как финальный API output

4. Cache

- обязательного server-side cache в первой версии нет
- клиент может вызывать сервис без ожидания, что сервис будет хранить результаты
- при этом архитектура не должна мешать добавить file-cache позже
- если появятся временные промежуточные файлы, они должны корректно очищаться

5. Health and introspection

- нужен `GET /healthz`
- нужен `GET /voices`
- нужен основной synthesis endpoint
- health endpoint должен позволять infra быстро понять, что процесс жив

Рекомендуемый API contract:

1. `GET /healthz`

Response `200`:

```json
{
  "status": "ok"
}
```

2. `GET /voices`

Response `200`:

```json
{
  "default_voice_id": "en_US-voice-1",
  "voices": [
    {
      "id": "en_US-voice-1",
      "label": "Voice 1"
    }
  ]
}
```

3. `POST /v1/synthesize`

Request:

```json
{
  "text": "apple",
  "voice_id": "en_US-voice-1"
}
```

Success response:

- `200 OK`
- `Content-Type: audio/ogg`
- body: raw ogg/opus bytes

Validation errors:

- `400 Bad Request`
- JSON body with compact machine-readable message

Server failure:

- `500 Internal Server Error`
- JSON body without leaking stack trace

Implementation guidance:

1. Engine choice

- можно использовать Piper как основной synthesis engine
- допускается lazy-download голосов, если это остается под контролем
- если первый запрос из-за lazy-download становится слишком тяжелым, добавь опциональный prefetch/warmup режим на старте

2. Audio pipeline

- если engine отдает wav, конвертируй его в `ogg/opus` через `ffmpeg`
- не возвращай промежуточный wav наружу

3. Concurrency and resource safety

- обязательно ограничь параллельный synthesis
- для первой версии допустим простой process-local semaphore / worker cap
- сервис не должен запускать неограниченное число одновременных Piper процессов

4. Logging

- логируй старт сервиса, конфиг голосов и synthesis errors
- не логируй весь текст целиком на info уровне
- если нужен traceability, логируй length/hash/voice_id

5. Config

Ожидаемые env vars примерно такие:

- `TTS_HOST`
- `TTS_PORT`
- `TTS_DEFAULT_VOICE_ID`
- `TTS_ENABLED_VOICE_IDS`
- `TTS_VOICE_DIR`
- `TTS_MAX_TEXT_LENGTH`
- `TTS_SYNTHESIS_TIMEOUT_SEC`
- `TTS_MAX_CONCURRENT_SYNTHESIS`
- `TTS_PREFETCH_VOICES_ON_START`

Можно скорректировать имена, но:

- конфиг должен быть явным
- значения по умолчанию должны быть безопасными

Infra shape:

1. Container

- отдельный Docker image
- внутри должны быть установлены:
  - Python runtime
  - Piper runtime dependencies
  - `ffmpeg`
- запуск должен идти отдельным entrypoint вроде `python -m tts_service`

2. Persistence

- persistent volume нужен как минимум для downloaded voices
- если позже появится server-side cache, он должен лежать отдельно и переживать рестарты
- логи можно оставлять stdout-first, если файловые логи не нужны

3. Network

- сервис должен быть доступен только по внутреннему Docker hostname
- публичный ingress не нужен
- если compose stack уже существует, сервис должен спокойно жить в той же internal network

4. VPS expectations

- сервис должен быть удобен для деплоя как отдельный stack/service
- host paths для persistent данных должны быть явными и предсказуемыми

Non-goals:

- не интегрировать сервис в какое-либо клиентское приложение
- не хранить user preferences
- не добавлять предметную логику клиента
- не делать генерацию длинных batch jobs, если без этого можно обойтись
- не строить очередь задач, distributed workers или object storage, если без этого можно обойтись

Acceptance criteria:

1. The service starts locally in its devcontainer or docker environment.
2. `GET /healthz` returns `200`.
3. `GET /voices` returns the configured voice list and default voice.
4. `POST /v1/synthesize` with valid `text` and `voice_id` returns non-empty `audio/ogg`.
5. Unknown `voice_id` returns `400`.
6. Empty text returns `400`.
7. Over-limit text returns `400`.
8. A synthesis failure returns `500`.
9. Restarting the container keeps downloaded voice files if persistent storage is configured.

Tests:

- Добавь focused automated tests минимум для:
  - text normalization
  - validation of empty/too-long text
  - voice selection validation
  - `/healthz`
  - `/voices`
  - `/v1/synthesize` happy path with mocked synth backend
  - failed synthesis error path

Рекомендованный rollout order:

1. выделить config model
2. выделить voice registry / validation
3. реализовать synthesizer adapter
4. реализовать ogg conversion pipeline
5. поднять HTTP API
6. покрыть focused tests
7. собрать Docker image
8. проверить локальный ручной smoke test

Критичные архитектурные запреты:

- не импортировать ничего из чужого runtime-кода
- не делать клиент-специфичные endpoint names
- не вшивать knowledge о user id, lesson id, assignment id и любых внешних сущностях
- не требовать чужую инфраструктурную конфигурацию для запуска сервиса

Ожидаемый итог:

- отдельный TTS service repo/runtime slice
- clear internal HTTP API
- голосовой synthesis в `audio/ogg`
- Docker-ready deployment shape


Сгенери компактный агентс мд файл с описанием что это зп сервисс- как кго стартовать для чего он нужен и какие решения н аосновании чего принималиьь - этот сервис не предполагается серьезно развивать - однако держать общую архитектутрадля быстрго  решения проблем и доработок необходимо