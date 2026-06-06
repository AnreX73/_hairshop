import json
import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from pywebpush import webpush, WebPushException
from .models import PushSubscription

logger = logging.getLogger(__name__)
User = get_user_model()


def _send_push(subscriptions, title: str, body: str, url: str = "/"):
    """Внутренняя функция — отправляет push по списку подписок."""
    payload = json.dumps(
        {
            "title": title,
            "body": body,
            "url": url,
            "icon": "/static/icons/icon-192x192.png",
            "badge": "/static/icons/badge-72x72.png",
        }
    )

    dead_subscriptions = []

    for sub in subscriptions:
        print(
            f"=== TRYING WEBPUSH to {sub.user.username}, endpoint={sub.endpoint[:50]} ==="
        )
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": f"mailto:{settings.VAPID_ADMIN_EMAIL}"},
            )
            print("=== WEBPUSH OK ===")
        except WebPushException as e:
            if e.response and e.response.status_code in (404, 410):
                dead_subscriptions.append(sub.pk)
            else:
                print(f"=== WEBPUSH EXCEPTION: {e} ===")
        except Exception:
            import traceback

            traceback.print_exc()

    if dead_subscriptions:
        PushSubscription.objects.filter(pk__in=dead_subscriptions).delete()


def send_push_to_staff(title: str, body: str, url: str = "/"):
    """Отправляет push всем staff-пользователям."""
    subscriptions = PushSubscription.objects.filter(user__is_staff=True)
    if not subscriptions.exists():
        logger.info("No staff push subscriptions found")
        return
    _send_push(subscriptions, title, body, url)


def send_push_to_user(user, title: str, body: str, url: str = "/"):
    """Отправляет push конкретному пользователю (не staff)."""
    subscriptions = PushSubscription.objects.filter(user=user, user__is_staff=False)
    if not subscriptions.exists():
        logger.info(f"No push subscriptions found for {user.username}")
        return
    _send_push(subscriptions, title, body, url)


def send_push_to_client(user, title: str, body: str, url: str = "/"):
    """Push конкретному клиенту."""
    subscriptions = PushSubscription.objects.filter(user=user)
    if subscriptions.exists():
        _send_push(subscriptions, title, body, url)


def send_push_chat_to_staff(session_id: int, body: str):

    send_push_to_staff(
        title="💬 Новое сообщение в чате",
        body=body,
        url=f"/dashboard/admin-chat/{session_id}/",
    )
