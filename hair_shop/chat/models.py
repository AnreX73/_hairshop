import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class Conversation(models.Model):
    """Диалог посетителя с менеджером.

    Гость привязан к серверной Django-сессии, поэтому его ID не передаётся
    в браузер и не может быть подменён. Если посетитель авторизован, диалог
    дополнительно связывается с его аккаунтом — это нужно для имени в списке
    оператора и для push-уведомлений.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chat_conversations",
        verbose_name="Пользователь",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Диалог"
        verbose_name_plural = "Диалоги"

    def __str__(self):
        return f"Диалог {self.client_label}"

    @property
    def client_label(self):
        if self.user_id and self.user:
            return self.user.get_full_name() or self.user.username
        return f"Гость #{str(self.pk)[:8]}"


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    client_id = models.UUIDField(default=uuid.uuid4)
    is_staff = models.BooleanField(default=False)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    text = models.TextField(max_length=2000, blank=True)
    image = models.ImageField(upload_to="chat/%Y/%m/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "is_staff", "client_id"],
                name="chat_message_dedup",
            ),
            models.CheckConstraint(
                condition=Q(text__gt="") | ~Q(image=""),
                name="chat_message_has_content",
            ),
        ]

    def __str__(self):
        preview = self.text[:40] if self.text else "📷 Фото"
        return f"{'Менеджер' if self.is_staff else 'Посетитель'}: {preview}"

    def payload(self):
        return {
            "id": self.pk,
            "client_id": str(self.client_id),
            "is_staff": self.is_staff,
            "text": self.text,
            "image": self.image.url if self.image else "",
            "created_at": self.created_at.isoformat(),
        }
