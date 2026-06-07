from django.core.management.base import BaseCommand
from django.db import transaction

from shop.models import Product, ProductHairShade, ProductImage


class Command(BaseCommand):
    help = (
        "Переносит оттенки из дубликатов товаров в ProductHairShade и удаляет дубликаты"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Показать что будет сделано без изменений в БД",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING("=== DRY RUN — БД не изменяется ===\n")
            )

        # все артикулы у которых больше одного товара
        from django.db.models import Count, Min

        articles = (
            Product.objects.values("article")
            .annotate(cnt=Count("pk"), min_pk=Min("pk"))
            .filter(cnt__gt=1)
            .order_by("-cnt")
        )

        total_groups = articles.count()
        total_duplicates = 0
        total_shades = 0

        self.stdout.write(f"Найдено групп с дубликатами: {total_groups}\n")

        for group in articles:
            article = group["article"]
            main_pk = group["min_pk"]
            count = group["cnt"]

            products = list(Product.objects.filter(article=article).order_by("pk"))
            main = products[0]
            duplicates = products[1:]

            shades = set(p.hair_shade for p in products if p.hair_shade)

            self.stdout.write(
                f"\nАртикул: {article} | Главный pk={main.pk} | "
                f"Дубликатов: {len(duplicates)} | Оттенки: {shades}"
            )

            if not dry_run:
                with transaction.atomic():
                    # переносим все оттенки в ProductHairShade
                    for shade in shades:
                        obj, created = ProductHairShade.objects.get_or_create(
                            product=main,
                            shade=shade,
                        )
                        if created:
                            total_shades += 1
                            self.stdout.write(
                                f"  + оттенок {shade} → товар pk={main.pk}"
                            )

                    # удаляем ProductImage дубликатов (файлы не трогаем)
                    for dup in duplicates:
                        img_count = dup.images.count()
                        ProductImage.objects.filter(product=dup).delete()
                        self.stdout.write(
                            f"  - удалено {img_count} записей медиа у pk={dup.pk}"
                        )

                    # удаляем дубликаты
                    dup_pks = [d.pk for d in duplicates]
                    Product.objects.filter(pk__in=dup_pks).delete()
                    total_duplicates += len(dup_pks)
                    self.stdout.write(f"  - удалены дубликаты: {dup_pks}")
            else:
                self.stdout.write(f"  [dry-run] перенести оттенки: {shades}")
                self.stdout.write(
                    f"  [dry-run] удалить дубликаты pk: {[d.pk for d in duplicates]}"
                )

        # одиночные товары — у них тоже есть hair_shade, переносим
        singles = (
            Product.objects.exclude(
                article__in=Product.objects.values("article")
                .annotate(cnt=Count("pk"))
                .filter(cnt__gt=1)
                .values("article")
            )
            .filter(hair_shade__isnull=False)
            .exclude(hair_shade="")
        )

        self.stdout.write(f"\nОдиночных товаров с оттенком: {singles.count()}")

        if not dry_run:
            for product in singles:
                obj, created = ProductHairShade.objects.get_or_create(
                    product=product,
                    shade=product.hair_shade,
                )
                if created:
                    total_shades += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\n{'[DRY RUN] ' if dry_run else ''}Готово:\n"
                f"  Групп обработано: {total_groups}\n"
                f"  Дубликатов удалено: {total_duplicates}\n"
                f"  Оттенков перенесено: {total_shades}\n"
            )
        )
