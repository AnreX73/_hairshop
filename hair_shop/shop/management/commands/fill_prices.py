# <app>/management/commands/fill_prices.py

import random
from django.core.management.base import BaseCommand
from django.db import transaction
from shop.models import Product   # замените на вашу модель


class Command(BaseCommand):
    help = 'Заполняет price и discount_percentage: 15% товаров без скидки (цена 2000-3500), остальные со скидкой 15/20/25 (final_price 1500-2500)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Количество товаров в одной транзакции'
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        all_products = list(Product.objects.all())
        total = len(all_products)

        if total == 0:
            self.stdout.write(self.style.WARNING('Нет товаров для обновления.'))
            return

        # --- Выбираем 15% товаров БЕЗ скидки (случайные) ---
        no_discount_count = int(total * 0.15)
        # Перемешиваем список товаров и берём первые no_discount_count штук
        shuffled_products = all_products.copy()
        random.shuffle(shuffled_products)
        no_discount_products = set(shuffled_products[:no_discount_count])  # множество объектов

        # --- Параметры диапазонов ---
        FINAL_LOW = 1500
        FINAL_HIGH = 2500
        DISCOUNT_CHOICES = [15, 20, 25]

        PRICE_LOW_NO_DISC = 2000
        PRICE_HIGH_NO_DISC = 3500

        updated_count = 0

        for i in range(0, total, batch_size):
            batch = all_products[i:i + batch_size]
            with transaction.atomic():
                for product in batch:
                    if product in no_discount_products:
                        # Без скидки
                        discount = 0
                        price = random.randint(PRICE_LOW_NO_DISC, PRICE_HIGH_NO_DISC)
                    else:
                        discount = random.choice(DISCOUNT_CHOICES)
                        # Вычисляем допустимый диапазон для price, чтобы final_price попал в [FINAL_LOW, FINAL_HIGH]
                        # final_price = price * (100 - discount) // 100   (целочисленно)
                        # Чтобы гарантировать final_price в интервале, вычисляем price так:
                        min_price = (FINAL_LOW * 100 + (100 - discount) - 1) // (100 - discount)
                        max_price = (FINAL_HIGH * 100) // (100 - discount)
                        if min_price > max_price:
                            # На всякий случай, если диапазон пуст (не должно случиться при наших числах)
                            price = min_price
                        else:
                            price = random.randint(min_price, max_price)

                    product.price = price
                    product.discount_percentage = discount

                Product.objects.bulk_update(batch, ['price', 'discount_percentage'])

            updated_count += len(batch)
            self.stdout.write(f'Обработано {updated_count} из {total} товаров')

        self.stdout.write(self.style.SUCCESS(
            f'Готово. Обновлено {updated_count} товаров.\n'
            f'  - {no_discount_count} товаров без скидки (цена {PRICE_LOW_NO_DISC}-{PRICE_HIGH_NO_DISC})\n'
            f'  - {total - no_discount_count} товаров со скидкой {DISCOUNT_CHOICES} (final_price {FINAL_LOW}-{FINAL_HIGH})'
        ))