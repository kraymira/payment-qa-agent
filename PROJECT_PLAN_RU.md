# Payment QA Agent — сокращённый план проекта

## Цель

Payment QA Agent показывает переход от обычных платёжных автотестов к безопасному AI-assisted triage.

Проект решает одну задачу: получить данные о падении теста, собрать связанные факты и определить наиболее вероятную категорию проблемы. Финансовые правила проверяет обычный Python-код. AI анализирует доказательства и объясняет вывод, но не изменяет тесты и не принимает решение о релизе.

```text
Payment failure
  → structured evidence
  → deterministic checks
  → guarded AI analysis
  → triage report or human review
```

## Правило разработки

MVP состоит из трёх последовательных релизов. Каждый релиз должен:

1. Работать без кода из следующих релизов.
2. Иметь одну понятную задачу и публичный результат.
3. Запускаться задокументированной командой.
4. Иметь автоматические тесты.
5. Не содержать зависимостей, которые пока не используются.

# MVP

## Релиз 1 — Payment Core

### Рабочий результат

Самостоятельная Python-библиотека, моделирующая безопасное создание платежа и его жизненный цикл.

### Функциональность

- создание платежа с `Decimal` amount;
- нормализация и проверка валюты;
- обязательный idempotency key;
- повтор одинакового запроса возвращает тот же платёж;
- повтор ключа с другим payload вызывает `IdempotencyConflict`;
- state machine `created → pending → completed`;
- переход в `failed` из `created` или `pending`;
- запрет переходов из финального статуса;
- упорядоченный transaction timeline.

### Публичный API

- `PaymentService`;
- `Payment`;
- `PaymentEvent`;
- `PaymentStatus`;
- доменные исключения.

Внутренние validation-функции и таблица переходов не являются публичным API.

### Проверка

```bash
uv run pytest
```

### Definition of Done

- правила создания платежа и idempotency покрыты тестами;
- допустимые и запрещённые переходы покрыты тестами;
- timeline содержит создание и каждое успешное изменение статуса;
- неизвестный payment ID возвращает доменную ошибку;
- проект не использует внешнюю сеть или базу данных;
- в runtime dependencies нет сторонних пакетов.

### Статус

Релиз реализован. Следующая работа с Payment Core допустима только для исправления найденной ошибки или поддержки следующего релиза.

## Релиз 2 — Deterministic Triage

### Рабочий результат

CLI получает JSON с данными о падении и возвращает структурированную классификацию без использования LLM.

### Вход

Один `FailureBundle`:

```json
{
  "test_name": "test_retry_does_not_duplicate_payment",
  "assertion": "expected one payment, found two",
  "payment_ids": ["pay_1", "pay_2"],
  "timeline": [],
  "invariant": "one idempotency key must map to one payment"
}
```

На этом этапе bundles хранятся как небольшие примеры в репозитории. Автоматический PyTest plugin для их сбора не входит в MVP.

### Выход

```json
{
  "classification": "product_bug",
  "probable_cause": "duplicate payment",
  "evidence_ids": ["assertion", "payment:pay_1", "payment:pay_2"],
  "requires_human_review": false
}
```

### Классификации

- `product_bug`;
- `test_bug`;
- `infrastructure_issue`;
- `insufficient_evidence`.

### Сценарии

1. Один idempotency key связан с двумя payment IDs.
2. `completed` платёж получил недопустимый переход обратно в `pending`.
3. В bundle недостаточно фактов для вывода.

### Запуск

```bash
uv run python -m payment_qa_agent.triage examples/duplicate_payment.json
uv run pytest
```

### Definition of Done

- три sample bundles хранятся в репозитории;
- каждый bundle проходит schema validation;
- CLI возвращает JSON;
- результат содержит только существующие evidence IDs;
- одинаковый вход всегда даёт одинаковый результат;
- инструмент работает без API-ключа и интернета;
- правила покрыты unit-тестами.

### Новые зависимости

- `pydantic` только для входной и выходной схемы.

### Статус

Релиз реализован в ветке `feature/deterministic-triage` и ожидает совместного
ревью перед слиянием в `main`.

## Релиз 3 — Guarded AI Triage

### Рабочий результат

LangGraph-агент получает тот же `FailureBundle`, при необходимости запрашивает дополнительные факты через read-only tools и возвращает `TriageResult` той же формы, что deterministic classifier.

### Agent tools

MVP использует только три инструмента:

- `get_failure_context` — assertion и нарушенный инвариант;
- `get_payment_timeline` — связанные payment events;
- `get_test_definition` — цель теста и ожидаемое поведение.

Агент не получает shell, произвольное чтение файлов, изменение кода или запись во внешние системы.

### Workflow

```text
Validate bundle
  → apply deterministic critical checks
  → request missing evidence through tools
  → validate cited evidence
  → return classification
  → request human review when evidence is insufficient
```

### Guardrails

- финансовый инвариант нельзя отменить ответом модели;
- неизвестный evidence ID делает ответ невалидным;
- недостаток данных всегда приводит к human review;
- unit-тесты используют fake model и не обращаются в сеть;
- реальная модель используется только в ручной демонстрации;
- отсутствие API key не ломает локальный запуск и тесты.

### Запуск

```bash
uv run python -m payment_qa_agent.agent examples/duplicate_payment.json
uv run pytest
```

### Definition of Done

- LangGraph workflow завершает все три сценария;
- агент вызывает только разрешённые tools;
- tool arguments и outputs валидируются;
- deterministic critical result имеет приоритет над LLM output;
- fake-model tests воспроизводимы;
- результат сравнивается с deterministic baseline;
- README объясняет ограничения агента.

### Новые зависимости

- `langgraph`;
- `langchain-core`;
- один model adapter для ручной демонстрации.

# Граница MVP

После третьего релиза MVP завершён. В нём нет HTTP API, базы данных, автоматического создания багов, UI, нагрузочного тестирования или внешней observability-платформы.

Итоговый MVP содержит:

- один payment domain package;
- три failure scenarios;
- один deterministic classifier;
- один LangGraph workflow;
- три read-only agent tools;
- два CLI;
- unit-тесты и короткий README.

# Расширенная версия

Расширения выполняются только после законченного MVP и не являются обязательными.

## Расширение 1 — Payment API

- FastAPI endpoints для создания и чтения платежей;
- HTTPX integration tests;
- retry через настоящий HTTP-запрос;
- duplicate и out-of-order webhook.

Пакеты: `fastapi`, `httpx`.

## Расширение 2 — AI evaluation

- LangSmith traces;
- небольшой размеченный dataset;
- classification accuracy;
- evidence grounding;
- сравнение prompt versions.

Пакет: `langsmith`.

## Расширение 3 — CI и K6

- GitHub Actions для тестов;
- один K6-сценарий с конкурентными запросами и одинаковым idempotency key;
- failure artifacts как CI artifacts.

K6 добавляется только после HTTP API.

## Расширение 4 — платёжный домен

- fees и rounding;
- ledger invariant `debits = credits`;
- refunds и reversals;
- FX conversion;
- blockchain confirmations и reorg;
- reconciliation.

Сценарии добавляются по одному, а не одним большим блоком.

## Расширение 5 — персистентность

- SQLite;
- уникальное ограничение idempotency key;
- атомарная запись платежа;
- тест конкурентной гонки.

ORM и migrations добавляются только при реальной необходимости.

# Что намеренно исключено

В проект не планируются без отдельной причины:

- frontend и Playwright UI-тесты;
- Docker и Kubernetes;
- Kafka, Redis и Celery;
- RAG и vector database;
- несколько agent frameworks;
- Grafana и Prometheus;
- автоматическое изменение тестов;
- полностью автономное решение о релизе.

# История для интервью после MVP

> I built a small payment-domain library covering idempotency, transaction states and timelines. I then added a deterministic failure classifier and used it as a baseline for a guarded LangGraph triage agent. The agent investigates failures through three narrow read-only tools, returns structured evidence and escalates cases with insufficient data. Financial rules remain deterministic, and all agent tests run against a fake model without network access.

# Следующий шаг

Payment Core завершён. Следующая задача — определить минимальные `FailureBundle` и `TriageResult` schemas и подготовить три sample failure bundles для deterministic triage.
