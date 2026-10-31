import logging
from datetime import timedelta

from django.db.models import Max, Q
from django.utils import timezone

from .models import Conversation

logger = logging.getLogger(__name__)


def cleanup_old_conversations(days=30):
    """Удаляет диалоги, где последнее сообщение старше `days` дней.

    Пустые диалоги удаляются, только если созданы раньше того же срока.
    Задача запускается планировщиком django-q (раньше чистила старые
    ChatSession).
    """
    threshold = timezone.now() - timedelta(days=days)
    conversations = Conversation.objects.annotate(
        last_message_at=Max("messages__created_at")
    ).filter(
        Q(last_message_at__lt=threshold)
        | Q(last_message_at__isnull=True, created_at__lt=threshold)
    )

    count = conversations.count()
    if count:
        conversations.delete()
        logger.info("Удалено старых диалогов чата: %s", count)
    else:
        logger.info("Старых диалогов чата для удаления не найдено.")

    return f"Очистка завершена. Удалено диалогов: {count}"
