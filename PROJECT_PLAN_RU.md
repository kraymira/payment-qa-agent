# Payment QA Agent — план продукта и реализации

## Назначение проекта

Payment QA Agent — учебный и портфолио-проект для подготовки к роли AI-Native QA Automation Engineer в BVNK. Он демонстрирует, как обычная автоматизация платёжного сервиса развивается в безопасный agentic QA workflow.

Проект решает одну понятную задачу: после падения платёжного автотеста автоматически собрать доказательства, исследовать их с помощью ограниченного набора инструментов и подготовить структурированный triage report. Финансовую корректность определяет только детерминированный код. AI помогает анализировать причины и объяснять результат, но не меняет проверки и не принимает окончательное решение о релизе.

Основная ценность проекта — не количество технологий, а законченная инженерная история:

```text
Платёжный сценарий
  → автоматическая проверка
  → обнаружение нарушения
  → сбор доказательств
  → исследование с помощью agent tools
  → классификация причины
  → guardrail и human review
```

## Продуктовый сценарий

Клиент отправляет запрос на создание платежа с `Idempotency-Key`. Сервис обрабатывает запрос, но клиент не получает ответ из-за timeout и повторяет его. Ошибка реализации может создать два платежа вместо одного.

PyTest обнаруживает нарушение инварианта, формирует failure bundle и передаёт его triage-компоненту. Агент изучает данные теста, transaction timeline и связанные логи, после чего возвращает классификацию, уверенность, список доказательств и рекомендуемое действие.

Пример результата:

```json
{
  "classification": "product_bug",
  "confidence": 0.94,
  "probable_cause": "Non-atomic idempotency check",
  "evidence_ids": ["assertion-1", "payment-1", "payment-2"],
  "recommended_action": "block_release_and_create_defect",
  "requires_human_review": true
}
```

Критическое нарушение `one idempotency key → one payment` блокирует релиз детерминированным правилом. AI только собирает и объясняет доказательства.

# Принципы реализации

## Каждый этап является рабочим продуктом

Этап считается завершённым, только если:

1. Его можно запустить одной задокументированной командой.
2. Он демонстрирует полезное поведение без кода из будущих этапов.
3. Ключевое поведение покрыто автоматическими тестами.
4. Ошибки возвращаются в понятном и проверяемом виде.
5. README объясняет назначение, запуск и ожидаемый результат.
6. Все добавленные зависимости реально используются.
7. Следующий этап расширяет готовый продукт, а не чинит недоделанную основу.

## Границы ответственности AI

Детерминированный код:

- проверяет суммы и валюты;
- контролирует допустимые переходы статусов;
- обнаруживает duplicate payments;
- проверяет финансовые инварианты;
- применяет обязательные release rules.

AI-компонент:

- сопоставляет данные из нескольких источников;
- классифицирует вероятную причину падения;
- указывает использованные доказательства;
- предлагает дальнейшее действие;
- эскалирует случай человеку при недостатке данных или низкой уверенности.

AI не может:

- выполнять произвольные shell-команды;
- читать произвольные файлы;
- изменять тесты или expected results;
- изменять платежи;
- самостоятельно создавать внешние задачи;
- единолично разрешать релиз.

## Минимальный стек

MVP использует только технологии, необходимые для основной истории:

- Python 3.12+;
- `uv` для окружения, зависимостей и запуска;
- PyTest для автоматизации;
- FastAPI и Pydantic для Payment API и схем данных;
- HTTPX для API-тестов;
- LangGraph для agent workflow;
- один model adapter для демонстрационного LLM-запуска;
- Ruff для linting и formatting;
- GitHub Actions для CI;
- один K6-сценарий для конкурентной проверки idempotency.

В MVP не входят ORM, отдельная база данных, Docker, полноценный UI, Kafka, Redis, Celery, RAG, vector database, Grafana или несколько agent frameworks.

# MVP

MVP состоит из пяти последовательных релизов. Каждый релиз самодостаточен, запускается отдельно и остаётся рабочим после добавления следующих возможностей.

## Релиз 1 — Payment Core

### Результат

Устанавливаемая Python-библиотека и локальная demo-команда, моделирующие создание и жизненный цикл платежа.

### Возможности

- создание платежа с `Decimal` amount и трёхбуквенной валютой;
- нормализация валюты;
- обязательный idempotency key;
- повтор одинакового запроса возвращает исходный платёж;
- повтор ключа с другим payload возвращает `IdempotencyConflict`;
- явная state machine;
- допустимые переходы `created → pending → completed` и `created/pending → failed`;
- запрет переходов из финального статуса;
- transaction timeline в памяти.

### Демонстрация

```bash
uv run python -m payment_qa_agent.demo
uv run pytest
```

Demo создаёт платёж, повторяет запрос с тем же ключом, проводит платёж по state machine и печатает transaction timeline.

### Definition of Done

- demo завершается успешно и показывает один payment ID для повторного запроса;
- негативный пример с изменённой суммой возвращает понятную ошибку;
- все переходы state machine протестированы;
- нет внешних сервисов и сетевых зависимостей;
- Ruff и PyTest проходят локально.

### Текущий статус

Уже реализованы модель платежа, in-memory service, базовая idempotency и пять проходящих PyTest-тестов. Для завершения релиза нужны state machine, transaction timeline, demo-команда и Ruff.

### Демонстрируемые навыки

Python typing, dataclasses, enums, exceptions, `Decimal`, PyTest parametrization, тест-дизайн и основы платёжной модели.

## Релиз 2 — Payment API Sandbox

### Результат

Локальный HTTP API, на котором можно воспроизводить payment retries и webhook-сценарии.

### Возможности

- `POST /payments` с `Idempotency-Key`;
- `GET /payments/{payment_id}`;
- `GET /payments/{payment_id}/events`;
- endpoint для имитации webhook;
- дедупликация webhook по event ID;
- защита от регрессии статуса при out-of-order webhook;
- correlation ID во всех событиях;
- структурированные JSON-логи стандартными средствами Python.

### Демонстрация

```bash
uv run fastapi dev payment_qa_agent.api:app
uv run pytest tests/api
```

Swagger UI позволяет вручную создать платёж, повторить запрос и отправить duplicate или out-of-order webhook.

### Definition of Done

- API запускается одной командой;
- OpenAPI доступен автоматически;
- повторный HTTP-запрос не создаёт новый платёж;
- duplicate webhook не создаёт новое событие;
- поздний `pending` не может изменить `completed`;
- API-тесты выполняются через HTTPX;
- библиотека из релиза 1 продолжает работать без изменений публичного контракта.

### Демонстрируемые навыки

FastAPI, Pydantic, HTTPX, API testing, async flows, webhooks, retries, correlation IDs и observability.

## Релиз 3 — Deterministic Failure Triage

### Результат

Полностью рабочий triage-инструмент без LLM. Он создаёт failure bundle и классифицирует известные типы падений по прозрачным правилам.

### Failure bundle

PyTest hook сохраняет JSON-артефакт:

```json
{
  "test_run_id": "run-123",
  "test_name": "test_retry_does_not_duplicate_payment",
  "assertion": "expected one payment, found two",
  "correlation_id": "corr-456",
  "payment_ids": ["pay-1", "pay-2"],
  "invariant": "one idempotency key must map to one payment"
}
```

### Поддерживаемые классификации

- `product_bug`;
- `test_bug`;
- `infrastructure_issue`;
- `expected_external_failure`;
- `insufficient_evidence`.

### Базовые сценарии

1. Retry создал duplicate payment — `product_bug`.
2. Out-of-order webhook вернул `completed` в `pending` — `product_bug`.
3. Временная недоступность внешней зависимости — `infrastructure_issue`.

### Демонстрация

```bash
uv run pytest tests/failure_scenarios
uv run python -m payment_qa_agent.triage artifacts/run-123.json
```

Команда возвращает проверяемый JSON с классификацией, доказательствами и рекомендуемым действием.

### Definition of Done

- failure bundle формируется автоматически при падении выбранного теста;
- три базовых сценария воспроизводимы;
- rule-based classifier выдаёт ожидаемую классификацию;
- результат соответствует Pydantic-схеме;
- каждое доказательство ссылается на существующий объект в bundle;
- инструмент работает без API-ключа и интернета.

### Демонстрируемые навыки

PyTest hooks, structured artifacts, failure analysis, классификация ошибок, explainability и проектирование стабильного baseline перед добавлением AI.

## Релиз 4 — Guarded AI Triage Agent

### Результат

LangGraph-агент исследует failure bundle через строго ограниченные read-only tools и возвращает структурированный triage result.

### Agent tools

#### `get_failure_context`

Возвращает assertion, stack trace, request/response, correlation ID и нарушенный инвариант.

#### `get_payment_timeline`

Возвращает упорядоченные события платежа или idempotency key.

#### `search_logs`

Ищет разрешённые структурированные логи по correlation ID, payment ID и временному диапазону.

#### `get_test_definition`

Возвращает описание цели теста, ожидаемый инвариант и разрешённый фрагмент тестового кода.

### Workflow

```text
Load failure bundle
  → run deterministic critical checks
  → let the agent request evidence through tools
  → validate cited evidence
  → produce structured classification
  → apply confidence and safety guardrails
  → return report or request human review
```

### Structured result

```python
class TriageResult(BaseModel):
    classification: FailureClassification
    confidence: float
    probable_cause: str
    evidence_ids: list[str]
    recommended_action: RecommendedAction
    requires_human_review: bool
```

### Guardrails

- tools имеют только read-only доступ;
- произвольные пути и команды запрещены;
- неизвестный `evidence_id` делает ответ невалидным;
- `confidence < 0.8` требует human review;
- финансовый critical invariant нельзя переопределить ответом LLM;
- отсутствие модели приводит к понятному fallback, а не ломает весь продукт.

### Демонстрация

```bash
uv run python -m payment_qa_agent.agent artifacts/run-123.json
```

Без API-ключа используется предсказуемый fake model. С настроенным ключом запускается один реальный model adapter.

### Definition of Done

- LangGraph workflow проходит от входного bundle до результата;
- агент действительно выбирает и вызывает tools;
- tool inputs и outputs валидируются;
- unit-тесты используют fake model и не зависят от сети;
- минимум три размеченных сценария проходят через agent workflow;
- низкая уверенность и недостаток данных приводят к human review;
- agent result сравнивается с deterministic baseline.

### Демонстрируемые навыки

LangGraph, tool calling, agent state, structured output, dependency injection, fake model testing, least privilege, guardrails и human-in-the-loop.

## Релиз 5 — CI Quality Gate

### Результат

Завершённый MVP с воспроизводимой проверкой качества в CI и одной содержательной K6-проверкой.

### Возможности

- GitHub Actions запускает Ruff и PyTest;
- AI unit-тесты работают без внешней модели;
- integration job с реальной моделью запускается только вручную или при наличии secret;
- локальный evaluation dataset содержит размеченные failure scenarios;
- evaluation script считает долю правильных классификаций и долю корректных эскалаций;
- K6 создаёт конкурентные запросы с одним idempotency key;
- quality gate блокируется только детерминированными критериями.

### Демонстрация

```bash
uv run ruff check .
uv run pytest
uv run python -m payment_qa_agent.evaluate evals/cases.jsonl
k6 run load/idempotency.js
```

### Definition of Done

- чистый checkout поднимается по инструкции;
- CI проходит без LLM API key;
- evaluation выдаёт повторяемые метрики;
- K6 подтверждает, что конкурентные повторы создают один платёж;
- failure artifacts доступны как CI artifacts;
- README содержит архитектуру, demo flow, ограничения и команды запуска;
- все пять релизов остаются отдельно демонстрируемыми.

### Демонстрируемые навыки

CI/CD, autonomous quality gates, AI evaluation, K6, concurrency testing, secrets handling и release decision design.

# Расширенная версия

Расширенная версия начинается только после завершения MVP. Каждое расширение должно отвечать на конкретный риск или улучшать измеримое качество системы.

## Расширение 1 — персистентность и транзакции

- SQLite с SQLAlchemy;
- уникальное ограничение для idempotency key;
- атомарное создание платежа;
- Alembic migrations;
- тест конкурентной гонки на уровне базы.

Ценность: показать, как idempotency обеспечивается не только in-memory логикой, но и транзакционными гарантиями.

## Расширение 2 — более богатая платёжная модель

- fees и rounding rules;
- double-entry ledger и проверка `debits = credits`;
- refunds и reversals;
- FX conversion с `Decimal`;
- blockchain confirmations;
- сценарий reorg и возвращение транзакции в промежуточное состояние;
- reconciliation между внутренними и внешними записями.

Ценность: углубить понимание fiat, stablecoin и ledger testing.

## Расширение 3 — LangSmith observability и evaluations

- traces реальных agent runs;
- размеченный dataset;
- сравнение prompt или model versions;
- проверка корректности tool selection;
- отдельные метрики classification accuracy, evidence grounding и escalation quality;
- regression evaluation перед изменением prompt или workflow.

Ценность: продемонстрировать, что качество AI измеряется, а не оценивается по одному красивому примеру.

## Расширение 4 — intelligent regression selection

- чтение ограниченного git diff;
- карта изменений к payment risks;
- рекомендация regression scope;
- объяснение, почему выбраны конкретные тесты;
- сравнение рекомендации с заранее размеченными PR examples.

Ценность: приблизить проект к AI-driven CI quality gates из вакансии.

## Расширение 5 — контролируемые действия агента

- разрешённый `rerun_test` с allowlist и лимитом повторов;
- проверка flaky hypothesis на основании нескольких запусков;
- формирование bug draft;
- создание внешнего issue только после явного human approval;
- журнал всех tool calls и решений.

Ценность: перейти от read-only investigation к безопасной ограниченной автономности.

## Расширение 6 — расширенное тестирование

- Hypothesis для генерации amounts, currencies и последовательностей событий;
- model-based/stateful testing payment state machine;
- дополнительные K6 spike и retry-storm scenarios;
- fault injection для timeout, duplicate delivery и partial failure;
- контрактные проверки OpenAPI;
- security cases для prompt injection через логи и test artifacts.

Ценность: усилить и обычную QA-инженерию, и AI-specific risk testing.

## Расширение 7 — упаковка и наблюдаемость

- Docker image;
- CLI на Typer;
- OpenTelemetry traces;
- структурированные логи через отдельную библиотеку при доказанной необходимости;
- простой read-only dashboard и один Playwright E2E flow.

Ценность: сделать демонстрацию удобнее, не меняя основную архитектуру.

# Что проект демонстрирует на интервью

| Область | Доказательство в проекте |
|---|---|
| Python | Типизированные модели, state machine, exceptions и CLI |
| PyTest | Fixtures, parametrization, hooks и failure artifacts |
| API testing | FastAPI sandbox и HTTPX integration tests |
| Payments | Idempotency, retries, states, webhooks и concurrency |
| AI-native QA | Agent самостоятельно собирает доказательства через tools |
| Agent architecture | LangGraph state, routing, tool calling и fallback |
| AI safety | Read-only tools, evidence validation и human review |
| AI evaluation | Размеченные cases и повторяемые метрики |
| CI/CD | Детерминированные quality gates и CI artifacts |
| Performance | K6-проверка конкурентной idempotency |
| Engineering judgment | Осознанное разделение детерминированной логики и AI |

# Готовая история для интервью

После завершения MVP проект можно описать так:

> I built a payment QA sandbox in Python and PyTest that covers idempotency, retries, transaction states and webhook ordering. Failed tests produce structured evidence bundles. A guarded LangGraph agent investigates those failures through narrow read-only tools, returns a typed classification with cited evidence and escalates low-confidence cases to a human. Financial release rules remain deterministic. The complete workflow runs in CI, is evaluated against labelled failure scenarios and includes a K6 concurrency check for duplicate-payment prevention.

# Порядок работы

Работа ведётся строго по релизам:

1. Завершить и продемонстрировать Payment Core.
2. Только после этого добавить HTTP API.
3. Создать deterministic triage и failure artifacts без LLM.
4. Добавить LangGraph поверх работающего baseline.
5. Завершить MVP CI, evaluation и одной K6-проверкой.
6. Выбирать расширения по их пользе для подготовки и интервью.

Новая технология не добавляется, если текущий релиз можно закончить без неё или если её роль невозможно объяснить одной фразой.

