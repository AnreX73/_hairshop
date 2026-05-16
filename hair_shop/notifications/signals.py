from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from shop.models import Order, Product  # ← твоя модель
from .push import send_push_to_staff


@receiver(post_save, sender=Order)
def notify_staff_on_new_order(sender, instance, created, **kwargs):
    if not created:
        return
    send_push_to_staff(
        title=f"Новый заказ #{instance.pk}",
        body=f"{instance.customer_name} — {instance.total} ₽",
        url="/dashboard/orders/",
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
            body=f"{instance.product_group} — {instance.name or instance.article}",
            url=f"/dashboard/products/{instance.pk}/edit/",
        )
