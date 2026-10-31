# Заглушка «Технические работы»

Показывает посетителям страницу-заглушку, пока на сервере идут работы. Реализовано на уровне nginx: Django-приложение при этом может быть остановлено или пересобираться.

## Файлы

| Файл | Назначение | В git |
|---|---|---|
| `maintenance.html` | Страница «Технические работы» (в стиле студии) | да |
| `nginx.working.conf` | Рабочий конфиг: проксирование на Django, `/static/`, `/media/` | да |
| `nginx.maintenance.conf` | Конфиг заглушки: отдаёт `maintenance.html` на все адреса | да |
| `nginx.conf` | Фактический конфиг, который монтируется в контейнер nginx | **нет** (в `.gitignore`) |
| `maintenance.sh` | Скрипт переключения режимов | да |
| `README.md` | Эта инструкция | да |

`nginx.conf` специально не хранится в git: на сервере это «переключатель», и `git pull` не должен затирать выбранный режим.

## Переключение

На сервере, из корня проекта (`hair_shop/`):

```bash
bash conf/maintenance.sh on       # включить заглушку
bash conf/maintenance.sh off      # выключить заглушку
bash conf/maintenance.sh status   # узнать текущий режим
```

Скрипт копирует нужный шаблон в `conf/nginx.conf` и перезапускает контейнер `nginx`.

Что делает скрипт, чтобы не уронить сайт:

- если `conf/nginx.conf` пропал (например, свежий клон репозитория) — восстанавливает его из `nginx.working.conf`;
- перед перезапуском проверяет новый конфиг через `nginx -t` внутри контейнера и при ошибке возвращает прежний конфиг;
- делает `docker compose up -d --no-deps nginx` (применяет изменения compose, например новые volume, но не поднимает `web`/`db`) и затем `restart` — новый конфиг гарантированно прочитан.

### Вручную (если скрипт недоступен)

```bash
# включить заглушку
cp conf/nginx.maintenance.conf conf/nginx.conf
docker compose exec nginx nginx -t && docker compose restart nginx

# вернуть сайт
cp conf/nginx.working.conf conf/nginx.conf
docker compose exec nginx nginx -t && docker compose restart nginx
```

## Как это работает

- В `compose.yml` сервис `nginx` монтирует:
  - `./conf/nginx.conf` → `/etc/nginx/conf.d/default.conf` (read-only);
  - `./conf/maintenance.html` → `/usr/share/nginx/html/maintenance.html` (read-only).
- В режиме заглушки все запросы попадают в `location /`, где `try_files /maintenance.html =503` отдаёт страницу. Ответ отдаётся с `Cache-Control: no-cache, no-store`, чтобы браузеры не запоминали заглушку.
- `/static/` и `/media/` в режиме заглушки не раздаются — страница самодостаточна (стили встроены), внешний только шрифт (Oswald / Great Vibes), который при недоступности заменяется системным.
- `nginx.working.conf` проксирует WebSocket-чат: `proxy_http_version 1.1`, заголовки `Upgrade`/`Connection` и таймауты 3600 с. В Nginx Proxy Manager для домена должна быть включена опция **Websockets Support**, иначе `/ws/chat/` не подключится.

## Важно

- Не редактируйте `conf/nginx.conf` вручную «по мелочи»: при следующем `maintenance.sh on/off` он будет перезаписан. Постоянные изменения вносите в `nginx.working.conf` и применяйте командой `off`.
- Если контейнер `nginx` ещё не запущен, поднимите его: `docker compose up -d nginx`.
- Проверить, что заглушка включилась: `curl -s http://localhost:8002/ | grep "Технические работы"` (порт из `compose.yml`). Снаружи — через домен/NPM.
- `try_files /maintenance.html =503` отдаёт найденный файл с кодом **200**; `503` вернётся только если сам файл `maintenance.html` пропал. Для посетителей это не важно, но учитывайте при настройке мониторинга.
- После выключения заглушки может понадобиться обновить страницу в браузере (жёстко: `Ctrl+F5`).
