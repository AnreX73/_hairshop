from django.apps import AppConfig


class ChatConfig(AppConfig):
    name = "chat"
    verbose_name = "Чат с посетителями"

    def ready(self):
        from . import checks  # noqa: F401  регистрирует системные проверки
