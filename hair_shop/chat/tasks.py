import logging
from datetime import timedelta

from django.db.models import Exists, Max, OuterRef
from django.utils import timezone

from .models import Conversation

logger = logging.getLogger(__name__)

# Сроки хранения после последнего сообщения.
GUEST_RETENTION_DAYS = 7
REGISTERED_RETENTION_DAYS = 45
CART_RETENTION_DAYS = 90
EMPTY_RETENTION_HOURS = 12


def _has_cart_expression():
    """EXISTS-подзапрос: у пользователя диалога есть товар в корзине."""
    from shop.models import CartItem

    return Exists(CartItem.objects.filter(cart__user_id=OuterRef("user_id")))


def cleanup_old_conversations():
    """Удаляет диалоги по срокам, зависящим от статуса клиента.

    Статус вычисляется в момент очистки, а не хранится в диалоге:
    - гость без аккаунта — 7 дней;
    - зарегистрированный с пустой корзиной — 45 дней;
    - зарегистрированный с товаром в корзине — 90 дней;
    - диалог без сообщений — 12 часов.

    Пустая корзина (без CartItem) не считается статусом «с корзиной».
    """
    now = timezone.now()
    has_cart = _has_cart_expression()

    with_messages = Conversation.objects.annotate(
        last_message_at=Max("messages__created_at")
    ).filter(last_message_at__isnull=False)

    guests = with_messages.filter(
        user__isnull=True,
        last_message_at__lt=now - timedelta(days=GUEST_RETENTION_DAYS),
    )
    carts = (
        with_messages.filter(
            user__isnull=False,
            last_message_at__lt=now - timedelta(days=CART_RETENTION_DAYS),
        )
        .annotate(has_cart=has_cart)
        .filter(has_cart=True)
    )
    registered = (
        with_messages.filter(
            user__isnull=False,
            last_message_at__lt=now - timedelta(days=REGISTERED_RETENTION_DAYS),
        )
        .annotate(has_cart=has_cart)
        .filter(has_cart=False)
    )

    deleted = {}
    for name, queryset in (
        ("гости", guests),
        ("клиенты с корзиной", carts),
        ("клиенты", registered),
    ):
        count = queryset.count()
        if count:
            queryset.delete()
        deleted[name] = count

    empty = Conversation.objects.filter(
        messages__isnull=True,
        created_at__lt=now - timedelta(hours=EMPTY_RETENTION_HOURS),
    )
    empty_count = empty.count()
    if empty_count:
        empty.delete()
    deleted["пустые"] = empty_count

    total = sum(deleted.values())
    if total:
        logger.info(
            "Удалено старых диалогов чата: %s (%s)",
            total,
            ", ".join(f"{name}: {count}" for name, count in deleted.items()),
        )
    else:
        logger.info("Старых диалогов чата для удаления не найдено.")

    return (
        f"Очистка завершена. Удалено диалогов: {total} "
        f"(гости: {deleted['гости']}, "
        f"клиенты с корзиной: {deleted['клиенты с корзиной']}, "
        f"клиенты: {deleted['клиенты']}, пустые: {deleted['пустые']})"
    )
