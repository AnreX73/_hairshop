from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.db.models import Avg, Count
from .models import Review, Product, Cart, Order
from django.contrib.auth import get_user_model
from django.db.models import F

User = User = get_user_model()

_order_previous_state = {}  # временное хранилище состояния


@receiver(post_save, sender=Review)
def update_product_rating_on_save(sender, instance, created, **kwargs):
    """
    Обновление рейтинга товара при добавлении или изменении отзыва
    """
    product = instance.product
    
    # Получаем только одобренные отзывы
    approved_reviews = product.reviews.filter(is_approved=True)
    
    # Вычисляем средний рейтинг и количество отзывов
    stats = approved_reviews.aggregate(
        avg_rating=Avg('rating'),
        count=Count('id')
    )
    
    # Обновляем поля товара
    product.rating = round(stats['avg_rating'], 2) if stats['avg_rating'] else 0
    product.reviews_count = stats['count']
    product.save(update_fields=['rating', 'reviews_count'])

    

@receiver(post_delete, sender=Review)
def update_product_rating_on_delete(sender, instance, **kwargs):
    """
    Обновление рейтинга товара при удалении отзыва
    """
    product = instance.product
    
    # Получаем только одобренные отзывы
    approved_reviews = product.reviews.filter(is_approved=True)
    
    # Вычисляем средний рейтинг и количество отзывов
    stats = approved_reviews.aggregate(
        avg_rating=Avg('rating'),
        count=Count('id')
    )
    
    # Обновляем поля товара
    product.rating = round(stats['avg_rating'], 2) if stats['avg_rating'] else 0
    product.reviews_count = stats['count']
    product.save(update_fields=['rating', 'reviews_count'])




@receiver(post_save, sender=User)
def create_user_cart(sender, instance, created, **kwargs):
    """
    Автоматическое создание корзины при регистрации пользователя
    """
    """ проверка , что не создаем корзину при миграциях """
    if kwargs.get('raw'):
        return

    """ проверка , что создаем корзину только при создании пользователя """
    if created:
        Cart.objects.create(user=instance)










@receiver(pre_save, sender=Order)
def cache_previous_order_state(sender, instance, **kwargs):
    """Сохраняем предыдущие статусы до сохранения"""
    if instance.pk:
        try:
            previous = Order.objects.get(pk=instance.pk)
            _order_previous_state[instance.pk] = {
                'status': previous.status,
                'payment_status': previous.payment_status,
            }
        except Order.DoesNotExist:
            pass

        

_order_previous_state = {}  # временное хранилище состояния


@receiver(post_save, sender=Order)
def update_popularity_on_order(sender, instance, created, **kwargs):
    previous = _order_previous_state.pop(instance.pk, None)

    if not previous:
        return

    delivered_now = (
        instance.status == 'delivered' and
        previous['status'] != 'delivered'
    )
    paid_now = (
        instance.payment_status == 'paid' and
        previous['payment_status'] != 'paid'
    )

    if not (delivered_now or paid_now):
        return

    order_items = instance.items.select_related('product')

    for item in order_items:
        Product.objects.filter(pk=item.product_id).update(
            popularity=F('popularity') + item.quantity
        )

    recalculate_hits()


def recalculate_hits():
    top_24_ids = (
        Product.objects.order_by('-popularity')
        .values_list('id', flat=True)[:24]
    )
    Product.objects.update(is_hit=False)
    Product.objects.filter(id__in=list(top_24_ids)).update(is_hit=True)