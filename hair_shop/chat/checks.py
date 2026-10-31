"""Системные проверки чата: слой Channels должен быть загружаемым и доступным.

Без этого ошибка вида «ImportError: channels_redis» всплывает только на
WebSocket-рукопожатии, и в браузере это выглядит как «Соединение прервано».
"""

import socket
from importlib import import_module
from urllib.parse import urlsplit

from django.conf import settings
from django.core.checks import Error, Warning, register


@register()
def channel_layer_check(app_configs, **kwargs):
    issues = []
    config = (settings.CHANNEL_LAYERS or {}).get("default") or {}
    backend = config.get("BACKEND")
    if not backend:
        return [
            Error(
                "Не настроен CHANNEL_LAYERS['default']",
                hint="Без него чат не работает: WebSocket отдаёт 500.",
                id="chat.E001",
            )
        ]

    module_path, _, class_name = backend.rpartition(".")
    try:
        getattr(import_module(module_path), class_name)
    except (ImportError, AttributeError) as exc:
        return [
            Error(
                f"Не удалось загрузить канал-слой {backend}: {exc}",
                hint=(
                    "Установите зависимости: pip install -r requirements.txt "
                    "(channels-redis)."
                ),
                id="chat.E002",
            )
        ]

    for host in config.get("CONFIG", {}).get("hosts", []) or []:
        if not isinstance(host, str) or not host.startswith(("redis://", "rediss://")):
            continue
        parts = urlsplit(host)
        try:
            with socket.create_connection(
                (parts.hostname, parts.port or 6379), timeout=0.5
            ):
                pass
        except (OSError, TypeError) as exc:
            issues.append(
                Warning(
                    f"Redis для чата недоступен ({host}): {exc}",
                    hint=(
                        "Запустите Redis или поправьте REDIS_URL: без него "
                        "WebSocket не подключится."
                    ),
                    id="chat.W001",
                )
            )
    return issues
