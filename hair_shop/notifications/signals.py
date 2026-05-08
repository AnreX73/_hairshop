from django.db.models.signals import post_save
from django.dispatch import receiver
from shop.models import Order       # ← твоя модель
from .push import send_push_to_staff

@receiver(post_save, sender=Order)
def notify_staff_on_new_order(sender, instance, created, **kwargs):
    if not created:
        return
    send_push_to_staff(
        title=f'Новый заказ #{instance.pk}',
        body=f'{instance.user.get_full_name()} — {instance.total_price} ₽',
        url=f'/admin/orders/order/{instance.pk}/change/',
    )