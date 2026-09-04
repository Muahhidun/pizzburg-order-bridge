# PizzBurg Order Bridge

Отдельный API-сервис для передачи заказов из агрегаторов доставки в Poster. Сервис принимает
официальный формат заказов Яндекс Еды, сохраняет исходный запрос в PostgreSQL и умеет создавать
онлайн-заказ в Poster. Отправка в Poster защищена отдельным выключенным по умолчанию флагом.

## Реализовано в каркасе

- FastAPI и автоматическая OpenAPI-документация (`/docs`);
- OAuth 2.0 `client_credentials` с короткоживущим JWT;
- PostgreSQL, async SQLAlchemy и миграции Alembic;
- идемпотентный приём заказа и защита от изменённого дубля;
- Poster Adapter для `incomingOrders.createIncomingOrder` с защитой от повторной отправки;
- одно пилотное заведение `pizzburg-main`;
- список заведений в официальном формате Яндекс Еды `places`;
- Docker Compose и автоматические тесты.

API первого этапа:

```text
GET  /health
POST /security/oauth/token
GET  /restaurants
GET  /menu/{restaurant_id}/composition
POST /order
GET  /order/{order_id}
GET  /order/{order_id}/status
```

`/health` открыт для Railway health check. Остальные бизнес-маршруты требуют Bearer JWT.

Меню соответствует контракту Яндекс Еды
`application/vnd.eats.menu.composition.v2+json`. Сейчас сервис читает активные позиции категории
напрямую из основного Poster: исходные ID, категории, названия, вес и доступность. Для Яндекса
используются цены и видимость источника заказов `Wolt`. Выключенные позиции и категории не
выгружаются. Фотографии берутся в приоритете с актуальной
витрины PizzBurg, а при отсутствии — из Poster; для каждой фотографии рассчитывается SHA-1.
Ответ также содержит подготовленные описания и размеры. Меню кэшируется на пять минут.

При включённой передаче Yandex ID позиции используется как `product_id` Poster. Цена передаётся
в минимальных денежных единицах, заказ создаётся с режимом доставки, а заказ с типом оплаты
`CARD` отмечается как предоплаченный. Выбранные вкусы и соусы добавляются в комментарий заказа,
поскольку их ID в меню Яндекса являются вариантами витрины, а не ID техкарт Poster.

## Локальный запуск в Docker

1. Установить Docker Desktop.
2. Создать локальную конфигурацию: `cp .env.example .env`.
3. Заменить локальные OAuth/JWT-заглушки в `.env`.
4. Запустить: `docker compose up --build`.
5. Открыть `http://localhost:8000/docs`.

Файл `.env` исключён из Git. Для Railway те же переменные задаются в настройках проекта.

## Запуск без Docker

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
cp .env.example .env
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload
```

Для этого варианта PostgreSQL должен быть доступен по `BRIDGE_DATABASE_URL`.

## Railway

В сервисе приложения задайте переменные:

```text
BRIDGE_ENVIRONMENT=production
BRIDGE_DATABASE_URL=${{Postgres.DATABASE_URL}}
BRIDGE_OAUTH_CLIENT_ID=<сгенерированный Client ID>
BRIDGE_OAUTH_CLIENT_SECRET=<сгенерированный секрет>
BRIDGE_JWT_SECRET=<отдельный случайный секрет не короче 32 байт>
BRIDGE_POSTER_MAIN_TOKEN=<токен основного Poster с правом создания онлайн-заказов>
BRIDGE_POSTER_MAIN_SPOT_ID=1
BRIDGE_POSTER_MENU_PRICE_SOURCE=Wolt
BRIDGE_POSTER_ORDER_FORWARDING_ENABLED=false
BRIDGE_POSTER_CURRENCY=KZT
```

Имена ссылок чувствительны к названию сервиса базы данных: пример предполагает, что он
называется `Postgres`. Контейнер автоматически выполняет `alembic upgrade head` перед запуском
API. После успешного deployment создайте публичный домен в `Settings → Networking` и проверьте
`https://<domain>/health`.

## Тесты и стиль

```bash
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

Тесты используют временную SQLite-базу; рабочее и production-окружения используют PostgreSQL.

## Безопасное включение Poster

Новый deployment всегда оставляйте с `BRIDGE_POSTER_ORDER_FORWARDING_ENABLED=false`, пока не
согласовано время теста. После проверки токена, заведения и состава тестового заказа установите
значение `true`, дождитесь успешного deployment и попросите Яндекс отправить новый тестовый
заказ. Один `eatsId` отправляется в Poster только один раз. Если ответ Poster неоднозначен или
завершился ошибкой, автоматический повтор блокируется до ручной проверки, чтобы на планшете не
появился дубль.

Рабочее включение выполняется только после того, как тестовый заказ появился на планшете и его
содержимое сверено с заказом в Яндекс Вендор.

Никакие production-секреты нельзя добавлять в репозиторий, Docker-образ или сообщения Git.
