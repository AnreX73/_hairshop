# Чат с посетителями

Документ для разработчика, который впервые открывает приложение `chat`.
Описывает текущую реализацию, а не первоначальный план.

## Что это

Диалог между посетителем сайта и сотрудником: текст, фото и голосовые
сообщения до 60 секунд. Гость привязан к серверной Django-сессии, сотрудник
отвечает из виджета на любой странице или со страницы «Диалоги».

Стек: Django 5.2, Channels 4.3, Redis, Alpine.js, django-q2, ffmpeg.

## Точки входа

### HTTP

| Метод | URL | Доступ | Назначение |
|---|---|---|---|
| POST | `/chat/start/` | любой посетитель | создать/переиспользовать диалог, вернуть `socket_path` |
| POST | `/chat/upload/` | сессия с диалогом | фото или голосовое от посетителя |
| GET | `/chat/operator/` | `is_staff` | список диалогов |
| GET | `/chat/operator/<uuid>/` | `is_staff` | страница диалога |
| POST | `/chat/operator/<uuid>/upload/` | `is_staff` | фото или голосовое от сотрудника |

Оба upload-эндпоинта принимают поля `image` или `audio` и общий `client_id`.

### WebSocket

| URL | Кто | Назначение |
|---|---|---|
| `/ws/chat/` | посетитель | история и новые сообщения своего диалога |
| `/ws/chat/operator/` | `is_staff` | живой список диалогов |
| `/ws/chat/operator/<uuid>/` | `is_staff` | диалог с конкретным посетителем |

Посетитель **не передаёт** id диалога: он берётся из
`request.session["chat_conversation"]`. Сотрудник получает только те диалоги,
к которым имеет доступ, а не-staff отключается кодом `4403`.

## Модели

`Conversation`: UUID pk, `user` (null для гостя), `created_at`, `updated_at`.

`Message`: `conversation`, `client_id`, `is_staff`, `author`, `text`,
`image`, `audio`, `audio_duration`, `created_at`.

Ограничения:

- `unique(conversation, is_staff, client_id)` — защита от повторной отправки;
- `text != '' OR image != '' OR audio != ''` — сообщение не может быть пустым.

История при подключении ограничена последними 100 сообщениями.

## Статусы клиента

Вычисляются при чтении, не хранятся:

| Статус | Условие | Бейдж |
|---|---|---|
| `guest` | `user_id is null` | Гость |
| `registered` | есть пользователь, нет товаров в корзине | Клиент |
| `cart` | есть хотя бы один `CartItem` | С корзиной |

Пустая корзина (`Cart` без `CartItem`) — это `registered`, а не `cart`.

## Сроки хранения

Вычисляются в момент очистки (`chat.tasks.cleanup_old_conversations`):

| Что | Срок после последнего сообщения |
|---|---|
| гость | 7 дней |
| клиент | 45 дней |
| клиент с товаром в корзине | 90 дней |
| диалог без сообщений | 12 часов после создания |

Удаление диалога удаляет фото и аудио через `django-cleanup`.

Расписание: django-q2, задача `cleanup_old_chat_conversations`, ежедневно.

## Медиа

- Фото: JPEG/PNG/WebP на входе → WebP, максимум 1920×1920, качество 82,
  вход до 10 МБ. Клиент сжимает в JPEG перед отправкой.
- Голос: WebM/Opus или MP4/AAC на входе → mono MP3 64 kbps / 44.1 kHz,
  максимум 60 секунд (+1 с допуска), вход до 10 МБ.
- Длительность голоса измеряется **декодированием** потока
  (`ffmpeg -vn -f null -progress pipe:1`), а не полем `Duration:`:
  MediaRecorder часто пишет `Duration: N/A`.
- Запись короче 0.2 с и пустой/невалидный MP3 после транскодирования
  отклоняются.
- Хранение: `MEDIA_ROOT/chat/%Y/%m/`, URL `/media/chat/...`.
- В production `/media/` отдаёт nginx (`alias /app/media/`).
- Бэкап медиа выполняется вместе с базой.

## Интеграция с проектом

| Точка | Где | Что сделано |
|---|---|---|
| Корзина | `chat/services.py`, `views.py`, `consumers.py`, `tasks.py` | `shop.CartItem` |
| Push | `chat/services.notify_push()` | `notifications.push.send_push_to_client` / `send_push_to_staff` |
| Пользователь | `Conversation.client_label` | `get_full_name()` или `username` |
| Базовый шаблон | `shop/templates/shop/base.html` | виджет, CSS, `chat.js` до Alpine |
| Админка | `dashboard/templates/dashboard/admin_area.html` | кнопка «Чат с клиентами» |
| Статика | `{% static_v %}` | общий helper проекта |
| Планировщик | django-q2 | ежедневная очистка |

Виджет оператора включён в `shop/templates/shop/base.html` и
`dashboard/templates/dashboard/base.html`; `chat/js/chat.js` подключается
раньше Alpine.

## Настройки

```python
ASGI_APPLICATION = "hair_shop.asgi.application"
CHANNEL_LAYERS = {...}   # channels_redis, socket_timeout 30
CACHES = {...}           # django-redis, для rate limit
MEDIA_ROOT / MEDIA_URL
Q_CLUSTER = {...}
```

Переменные окружения: `REDIS_URL`, `DB_*`, `VAPID_*` (если включён push).

## Запуск и разработка

```bash
python manage.py migrate
python manage.py runserver        # daphne в INSTALLED_APPS даёт ASGI
python manage.py qcluster         # отдельный терминал, если нужна очистка
```

Тесты:

```bash
python manage.py test chat --settings=chat.test_settings --noinput
```

Проверки:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
node --check chat/static/chat/js/chat.js
ruff check chat --exclude chat/migrations
```

`chat.test_settings` использует основную базу (миграции проекта содержат
PostgreSQL-специфичный SQL), но подменяет Channels и cache на in-memory.

## Деплой

Порядок обязателен:

```bash
docker compose build web
docker compose run --rm web python manage.py migrate
docker compose up -d --force-recreate web qcluster
docker compose exec web python manage.py check
```

Не перезапускайте приложение до миграции: иначе WebSocket отдаёт `1011`,
потому что код обращается к ещё не созданным колонкам.

Если менялись `chat.js`, `chat.css` или `templates/chat/*`, нужен rebuild
образа: `collectstatic` обновляет только статику и не копирует Django-шаблоны.
После деплоя — `Ctrl+F5`, если статика отдаётся без хешей в имени файла.

Требования прокси: `Upgrade`/`Connection`, `proxy_read_timeout 3600s`,
`client_max_body_size` > 10 МБ, `/media/`, `X-Forwarded-Proto`.

HTTPS обязателен для записи голоса (`window.isSecureContext`).

## Диагностика

| Симптом | Причина | Решение |
|---|---|---|
| `1011` | не применена миграция / Redis недоступен | `migrate`, проверить Redis |
| `4403` | нет сессии / не staff / диалог удалён | открыть виджет заново, проверить права |
| `1008` | origin не в `ALLOWED_HOSTS` | добавить домен |
| нет живых сообщений | `CHANNEL_LAYERS` / Redis | `manage.py check` |
| нет микрофона | HTTP вместо HTTPS | включить TLS |
| фото 404 | нет `/media/` в nginx | добавить alias |
| «Не удалось определить длительность записи» | ffmpeg читает `Duration: N/A` | измерять длительность декодированием |
| голос скачивается и играет локально, но молчит в чате | обработчик `play` получает событие вместо элемента | передать `$event.currentTarget` |
| голос не скачивается или файл битый | транскодирование / хранилище | проверить размер MP3, лог ffmpeg, `Content-Type` |
| предупреждение `AudioContext` | звук уведомлений создан без жеста | создавать только после `pointerdown`/`keydown` |
| старый интерфейс после деплоя | не пересобран образ / кэш браузера | rebuild + `Ctrl+F5` |
| файлы не удаляются | `django_cleanup` не последним / нет volume | поправить порядок и volume |

## Особенности реализации

- Голосовые проигрываются нативным `<audio controls>`; одновременно играет
  только один плеер. Обработчик получает `$event.currentTarget`, иначе плеер
  ставит на паузу сам себя.
- Звук уведомления оператора — необязательный WebAudio-бипер. `AudioContext`
  создаётся и возобновляется только после действия пользователя; до первого
  клика сообщения приходят без звука.
- Старые неиграбельные MP3, сохранённые до исправления, нужно отправить
  заново: если файл уже нулевой, восстановить его нельзя.

## История изменений

| Дата | Изменение |
|---|---|
| 2026-11-02 | Чат добавлен: текст, фото, голос, статусы, очистка |
| 2026-11-02 | Исправлены длительность MediaRecorder, пустой MP3, автозапуск AudioContext и пауза плеера |
