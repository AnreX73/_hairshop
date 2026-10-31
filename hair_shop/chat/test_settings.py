"""Настройки для тестов чата.

База данных берётся из основных настроек: миграции проекта содержат
PostgreSQL-специфичный SQL (shop/0049), поэтому SQLite для тестов не подходит.
Меняем только то, что нужно для изолированной работы WebSocket без Redis.
"""

from hair_shop.settings import *  # noqa: F403

CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
