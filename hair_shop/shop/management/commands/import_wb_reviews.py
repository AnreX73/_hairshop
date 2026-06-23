# management/commands/import_wb_reviews.py
import pandas as pd
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from shop.models import Review
from shop.models import Product
from django.db.models.signals import post_save
from django.db.models import Avg, Count
from shop.signals import update_product_rating_on_save
from notifications.signals import notify_staff_on_new_review


User = get_user_model()
WB_USERNAME = "wb_reviews@test.ru"


def clean_str(value):
    """Преобразует NaN и пустые значения в пустую строку"""
    if pd.isna(value):
        return ""
    return str(value).strip()


class Command(BaseCommand):
    help = "Импорт отзывов с Wildberries из Excel"

    def add_arguments(self, parser):
        parser.add_argument("file", type=str, help="Путь к xlsx файлу")

    def handle(self, *args, **options):
        wb_user = User.objects.get(username=WB_USERNAME)
        df = pd.read_excel(options["file"])

        # Отключаем сигналы на время импорта
        post_save.disconnect(update_product_rating_on_save, sender=Review)
        post_save.disconnect(notify_staff_on_new_review, sender=Review)

        created, skipped, not_found = 0, 0, 0
        affected_products = set()

        try:
            for _, row in df.iterrows():
                article = str(row["article"]).strip()

                try:
                    product = Product.objects.get(article=article)
                except Product.DoesNotExist:
                    self.stdout.write(f"  Товар не найден: {article}")
                    not_found += 1
                    continue

                title = (
                    clean_str(row.get("text", ""))[:100].strip()
                    or "Отзыв с Wildberries"
                )

                exists = Review.objects.filter(
                    product=product,
                    user=wb_user,
                    author_name=clean_str(row.get("author_name", "")),
                    rating=int(row["rating"]),
                    text=clean_str(row.get("text", "")),
                ).exists()

                if exists:
                    skipped += 1
                    continue

                review = Review(
                    product=product,
                    user=wb_user,
                    author_name=clean_str(row.get("author_name")),
                    rating=int(row["rating"]),
                    title=clean_str(row.get("text"))[:100],
                    text=clean_str(row.get("text")),
                    advantages=clean_str(row.get("advantages")) or None,
                    disadvantages=clean_str(row.get("disadvantages")) or None,
                    is_approved=True,
                    created_at=row["created_at"].to_pydatetime(),
                )
                review.save(skip_validation=True)
                affected_products.add(product.id)
                created += 1

        finally:
            # Подключаем сигналы обратно в любом случае
            post_save.connect(update_product_rating_on_save, sender=Review)
            post_save.connect(notify_staff_on_new_review, sender=Review)

        # Пересчитываем рейтинги только для затронутых товаров
        self.stdout.write("Пересчитываем рейтинги...")
        for product in Product.objects.filter(id__in=affected_products):
            stats = product.reviews.filter(is_approved=True).aggregate(
                avg_rating=Avg("rating"), count=Count("id")
            )
            product.rating = round(stats["avg_rating"], 2) if stats["avg_rating"] else 0
            product.reviews_count = stats["count"]
            product.save(update_fields=["rating", "reviews_count"])

        self.stdout.write(
            f"\nГотово: создано {created}, пропущено {skipped}, "
            f"товаров не найдено {not_found}"
        )
