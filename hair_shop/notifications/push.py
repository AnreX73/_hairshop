import json
import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from pywebpush import webpush, WebPushException
from .models import PushSubscription

logger = logging.getLogger(__name__)
User = get_user_model()


def send_push_to_staff(title: str, body: str, url: str = '/'):
    """
    Отправляет push-уведомление всем staff-пользователям.

    Вызывай эту функцию из сигнала или view при создании заказа:
        from notifications.push import send_push_to_staff
        send_push_to_staff(
            title='Новый заказ #42',
            body='Иван Иванов — 3 товара на 4 500 ₽',
            url='/admin/orders/order/42/change/'
        )
    """
    # Берём подписки только staff-пользователей
    subscriptions = PushSubscription.objects.filter(user__is_staff=True)

    if not subscriptions.exists():
        logger.info('No staff push subscriptions found')
        return

    payload = json.dumps({
        'title': title,
        'body': body,
        'url': url,
        'icon': '/static/icons/icon-192x192.png',   # твоя иконка
        'badge': '/static/icons/badge-72x72.png',   # маленький значок на Android
    })

    dead_subscriptions = []

    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    'endpoint': sub.endpoint,
                    'keys': {
                        'p256dh': sub.p256dh,
                        'auth': sub.auth,
                    }
                },
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={
                    'sub': f'mailto:{settings.VAPID_ADMIN_EMAIL}'
                }
            )
            logger.info(f'Push sent to {sub.user.username}')

        except WebPushException as e:
            # 410 Gone или 404 = подписка устарела, удаляем
            if e.response and e.response.status_code in (404, 410):
                dead_subscriptions.append(sub.pk)
                logger.warning(f'Dead subscription for {sub.user.username}, removing')
            else:
                logger.error(f'WebPush error for {sub.user.username}: {e}')

    # Чистим мёртвые подписки
    if dead_subscriptions:
        PushSubscription.objects.filter(pk__in=dead_subscriptions).delete()
