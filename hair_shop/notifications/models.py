from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class PushSubscription(models.Model):
    """
    Хранит данные подписки браузера на push-уведомления.
    Один staff-пользователь может иметь несколько подписок
    (разные браузеры / устройства).
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='push_subscriptions'
    )
    endpoint = models.TextField(unique=True)
    p256dh = models.TextField()   # публичный ключ браузера
    auth = models.TextField()     # auth secret

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Push Subscription'
        verbose_name_plural = 'Push Subscriptions'

    def __str__(self):
        return f"{self.user.username} — {self.endpoint[:60]}..."
