from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class PushSubscription(models.Model):
    """
    Хранит данные подписки браузера на push-уведомления.
    Один staff-пользователь может иметь несколько подписок
    (разные браузеры / устройства).
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="push_subscriptions"
    )
    endpoint = models.TextField(unique=True)
    p256dh = models.TextField()  # публичный ключ браузера
    auth = models.TextField()  # auth secret

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Подписка на уведомления"
        verbose_name_plural = "Подписки на уведомления"

    def __str__(self):
        return f"{self.user.username} — {self.endpoint[:60]}..."


# models.py — добавить


class ChatSession(models.Model):
    client = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="chat_sessions"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    # Можно опционально привязать к заказу позже
    # order = models.ForeignKey(Order, null=True, blank=True, ...)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Chat #{self.id} — {self.client.username}"


class ChatMessage(models.Model):
    SENDER_CHOICES = [("client", "Клиент"), ("admin", "Админ")]
    MSG_TYPES = [("text", "Текст"), ("image", "Фото"), ("photo_request", "Запрос фото")]

    session = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    msg_type = models.CharField(max_length=20, choices=MSG_TYPES, default="text")
    text = models.TextField(blank=True)
    image = models.ImageField(upload_to="chat/%Y/%m/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]
