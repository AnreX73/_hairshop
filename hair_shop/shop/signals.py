from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Avg, Count
from .models import Review, Product, Cart
from django.contrib.auth import get_user_model

User = User = get_user_model()


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