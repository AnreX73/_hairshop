import time

from asgiref.sync import async_to_sync
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.utils import timezone

from shop.models import CartItem

from .models import Conversation, Message

OPERATORS_GROUP = "chat.operators"
RATE_LIMIT_PER_MINUTE = 20

CLIENT_STATUS_LABELS = {
    "guest": "Гость",
    "registered": "Клиент",
    "cart": "С корзиной",
}


class ChatError(Exception):
    """Ошибка, которую можно показать посетителю."""


class RateLimited(ChatError):
    """Слишком много сообщений за минуту."""


def can_reply(user):
    """Отвечать в чате могут все сотрудники (is_staff)."""
    return bool(user and user.is_authenticated and user.is_staff)


def client_status(conversation):
    """Статус клиента: гость, клиент или клиент с товаром в корзине.

    Статус не хранится в диалоге и вычисляется по текущим данным. Если
    queryset уже аннотирован `has_cart`, лишний запрос не выполняется.
    """
    if not conversation.user_id:
        return "guest"
    has_cart = getattr(conversation, "has_cart", None)
    if has_cart is None:
        has_cart = CartItem.objects.filter(
            cart__user_id=conversation.user_id
        ).exists()
    return "cart" if has_cart else "registered"


def summary(conversation, message):
    """Краткая сводка диалога для списка в виджете оператора."""
    status = client_status(conversation)
    return {
        "id": str(conversation.pk),
        "client_label": conversation.client_label,
        "client_status": status,
        "client_status_label": CLIENT_STATUS_LABELS[status],
        "updated_at": message.created_at.isoformat(),
        "last_text": message.text[:80] if message.text else "📷 Фото",
        "last_is_staff": message.is_staff,
        "has_image": bool(message.image),
    }


def _check_rate_limit(conversation, is_staff):
    # Общий счётчик в Redis ограничивает все вкладки одной стороны диалога.
    key = (
        f"chat-rate:{conversation.pk}:{int(is_staff)}:"
        f"{int(time.time()) // 60}"
    )
    cache.add(key, 0, timeout=120)
    if cache.incr(key) > RATE_LIMIT_PER_MINUTE:
        raise RateLimited("Слишком много сообщений. Подождите минуту.")


def create_message(
    conversation,
    *,
    is_staff,
    client_id,
    text="",
    image=None,
    author=None,
):
    """Создаёт сообщение с защитой от повторной отправки.

    Возвращает пару (message, created). Если сообщение с таким client_id
    уже есть, возвращает существующее и created=False.
    """
    text = (text or "").strip()
    if not text and not image:
        raise ChatError("Введите сообщение или прикрепите фото.")
    if len(text) > 2000:
        raise ChatError("Введите сообщение до 2000 символов.")

    existing = Message.objects.filter(
        conversation=conversation,
        is_staff=is_staff,
        client_id=client_id,
    ).first()
    if existing:
        return existing, False

    _check_rate_limit(conversation, is_staff)

    try:
        with transaction.atomic():
            message = Message.objects.create(
                conversation=conversation,
                is_staff=is_staff,
                client_id=client_id,
                text=text,
                image=image,
                author=author if is_staff else None,
            )
            Conversation.objects.filter(pk=conversation.pk).update(
                updated_at=timezone.now()
            )
    except IntegrityError:
        # Параллельная отправка того же client_id: возвращаем уже созданное.
        existing = Message.objects.filter(
            conversation=conversation,
            is_staff=is_staff,
            client_id=client_id,
        ).first()
        if existing:
            return existing, False
        raise
    return message, True


def broadcast_message(conversation, message, *, created):
    """Отправляет сообщение в WebSocket-группу диалога и операторам."""
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    async_to_sync(channel_layer.group_send)(
        f"chat.{conversation.pk.hex}",
        {"type": "chat.message", "message": message.payload()},
    )
    if created:
        async_to_sync(channel_layer.group_send)(
            OPERATORS_GROUP,
            {
                "type": "inbox.update",
                "conversation": summary(conversation, message),
            },
        )


def notify_push(conversation, message):
    """Push-уведомления о новом сообщении.

    Гостям push не отправляется: подписка в проекте привязана к пользователю.
    """
    from notifications.push import send_push_to_client, send_push_to_staff

    preview = message.text[:80] if message.text else "📷 Фото"
    if message.is_staff:
        if conversation.user_id:
            send_push_to_client(
                user=conversation.user,
                title="💬 Ответ консультанта",
                body=preview,
                url="/?chat=open",
            )
    else:
        send_push_to_staff(
            title="💬 Новое сообщение в чате",
            body=f"{conversation.client_label}: {preview}",
            url=f"/chat/operator/{conversation.pk}/",
        )


def publish_message(conversation, message, *, created):
    broadcast_message(conversation, message, created=created)
    if created:
        notify_push(conversation, message)
