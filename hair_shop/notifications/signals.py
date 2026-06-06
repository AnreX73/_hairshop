from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from shop.models import Order, Product, Review  # ← твоя модель
from .push import (
    send_push_to_staff,
    send_push_to_user,
    send_push_to_client,
    send_push_chat_to_staff,
)
from .models import ChatMessage


@receiver(post_save, sender=Order)
def notify_staff_on_new_order(sender, instance, created, **kwargs):
    if not created:
        return
    send_push_to_staff(
        title=f"Новый заказ #{instance.pk}",
        body=f"{instance.delivery_city} — {instance.total} ₽",
        url="/dashboard/orders/",
    )


# уведомление, что написали отзыв
@receiver(post_save, sender=Review)
def notify_staff_on_new_review(sender, instance, created, **kwargs):
    if not created:
        return

    product_url = instance.product.get_absolute_url()
    target_url = f"{product_url}#review-{instance.id}"

    send_push_to_staff(
        title=f"Новый отзыв к товару {instance.product.name}",
        body=f"{instance.user.get_full_name() or instance.user.username} — {instance.rating} ⭐",
        url=target_url,
    )


# уведомление, что товар закончился
# Запоминаем старое значение ДО сохранения
@receiver(pre_save, sender=Product)
def remember_old_stock(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._old_stock = Product.objects.get(pk=instance.pk).stock
        except Product.DoesNotExist:
            instance._old_stock = None
    else:
        instance._old_stock = None


# Уведомляем только когда stock перешёл с ненулевого на ноль
@receiver(post_save, sender=Product)
def notify_staff_on_out_of_stock(sender, instance, **kwargs):
    old_stock = getattr(instance, "_old_stock", None)

    if instance.stock == 0 and old_stock and old_stock > 0:
        send_push_to_staff(
            title="Товар закончился 📦",
            body=f"{instance.category} — {instance.name or instance.article}",
            url=f"/dashboard/products/{instance.pk}/edit/",
        )


# Уведомляем для клинта
@receiver(post_save, sender=Order)
def notify_customer_on_status_change(sender, instance, created, **kwargs):
    if created:
        return  # новый заказ — не уведомляем, это для staff

    messages = {
        "confirmed": ("Заказ подтверждён ✅", "Ваш заказ принят в работу"),
        "processing": ("Заказ собирается 📦", "Ваш заказ комплектуется"),
        "shipped": (
            "Заказ отправлен 🚚",
            f"Трек-номер: {instance.tracking_number}"
            if instance.tracking_number
            else "Заказ передан в доставку",
        ),
        "delivered": ("Заказ доставлен 🎉", "Ваш заказ ждёт вас!"),
        "cancelled": ("Заказ отменён ❌", "Свяжитесь с нами если есть вопросы"),
    }

    if instance.status in messages:
        title, body = messages[instance.status]
        send_push_to_user(
            user=instance.user,
            title=title,
            body=body,
            url="/users/profile/?tab=4",  # страница заказов в личном кабинете
        )


@receiver(post_save, sender=ChatMessage)
def notify_on_chat_message(sender, instance, created, **kwargs):
    if not created:
        return
    print(
        f"=== SIGNAL FIRED: sender={instance.sender}, session={instance.session.id} ==="
    )
    session = instance.session

    if instance.sender == "client":
        # Клиент написал → пушим стафф
        preview = instance.text[:80] if instance.msg_type == "text" else "📷 Фото"
        send_push_chat_to_staff(session.id, preview)

    elif instance.sender == "admin":
        # Админ ответил → пушим клиента
        preview = (
            instance.text[:80]
            if instance.msg_type == "text"
            else "📷 Фото от консультанта"
        )
        send_push_to_client(
            user=session.client,
            title="💬 Ответ консультанта",
            body=preview,
            url="/?chat=open",
        )
