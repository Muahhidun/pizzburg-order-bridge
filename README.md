# PizzBurg Order Bridge

Отдельный API-сервис для передачи заказов из агрегаторов доставки в Poster.
Первый этап принимает заказы Яндекс Еды в безопасном режиме `dry-run`: валидирует и
сохраняет их в PostgreSQL, но ничего не отправляет в рабочий Poster.

## Реализовано в каркасе

- FastAPI и автоматическая OpenAPI-документация (`/docs`);
- OAuth 2.0 `client_credentials` с короткоживущим JWT;
- PostgreSQL, async SQLAlchemy и миграции Alembic;
- идемпотентный приём заказа и защита от изменённого дубля;
- одно пилотное заведение `pizzburg-main`;
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
`Пиццы` напрямую из основного Poster: исходные ID, названия, цены, вес и доступность. Ответ
кэшируется на пять минут. Чтение меню не включает отправку заказов в Poster.

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
BRIDGE_POSTER_MAIN_TOKEN=<read-only токен основного Poster>
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

## Граница текущего этапа

Схема `OrderCreate` сейчас является внутренним контрактом каркаса. Перед подключением Яндекса
нужно сверить её с выданной Яндексом технической спецификацией и реализовать Yandex Adapter.
Poster Adapter, меню, стоп-лист, Telegram-уведомления и рабочая отправка заказов относятся к
следующим этапам.

Никакие production-секреты нельзя добавлять в репозиторий, Docker-образ или сообщения Git.
