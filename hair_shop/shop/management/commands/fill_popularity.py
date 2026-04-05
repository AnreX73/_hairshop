# <app>/management/commands/fill_popularity.py

import random
from django.core.management.base import BaseCommand
from django.db import transaction
from shop.models import Product   # замените на вашу модель


class Command(BaseCommand):
    help = 'Заполняет поле popularity случайными числами для фейковой сортировки'

    def add_arguments(self, parser):
        parser.add_argument(
            '--min',
            type=int,
            default=0,
            help='Минимальное значение популярности (по умолчанию 0)'
        )
        parser.add_argument(
            '--max',
            type=int,
            default=10000,
            help='Максимальное значение популярности (по умолчанию 10000)'
        )
        parser.add_argument(
            '--distribution',
            type=str,
            choices=['uniform', 'normal'],
            default='uniform',
            help='Тип распределения: uniform (равномерное) или normal (нормальное)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='Количество товаров в одной транзакции'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Только показать статистику, не сохранять'
        )

    def handle(self, *args, **options):
        min_val = options['min']
        max_val = options['max']
        dist = options['distribution']
        batch_size = options['batch_size']
        dry_run = options['dry_run']

        # Проверяем, существует ли поле popularity в модели
        try:
            Product._meta.get_field('popularity')
        except FieldDoesNotExist:
            self.stdout.write(self.style.ERROR(
                'Поле "popularity" не найдено в модели Product.\n'
                'Добавьте его в модель и выполните миграции:\n'
                '  popularity = models.IntegerField(default=0, verbose_name="Популярность")'
            ))
            return

        total = Product.objects.count()
        if total == 0:
            self.stdout.write(self.style.WARNING('Нет товаров для обновления.'))
            return

        self.stdout.write(f'Генерация популярности для {total} товаров (диапазон {min_val}–{max_val}, распределение {dist})')

        # Генерация значений
        if dist == 'uniform':
            # Равномерное распределение
            values = [random.randint(min_val, max_val) for _ in range(total)]
        else:  # normal
            # Нормальное распределение: среднее = (min+max)/2, сигма = (max-min)/6 (почти все значения в пределах)
            mean = (min_val + max_val) / 2
            sigma = (max_val - min_val) / 6
            values = []
            for _ in range(total):
                val = int(random.gauss(mean, sigma))
                # Клиппируем в заданный диапазон
                val = max(min_val, min(max_val, val))
                values.append(val)

        if dry_run:
            # Статистика без сохранения
            avg = sum(values) / total
            self.stdout.write(f'Среднее: {avg:.2f}, мин: {min(values)}, макс: {max(values)}')
            self.stdout.write('DRY-RUN: изменения не сохранены.')
            return

        # Обновляем пачками
        updated = 0
        with transaction.atomic():
            for i in range(0, total, batch_size):
                batch = Product.objects.all()[i:i+batch_size]
                for product, val in zip(batch, values[i:i+batch_size]):
                    product.popularity = val
                Product.objects.bulk_update(batch, ['popularity'])
                updated += len(batch)
                self.stdout.write(f'Обновлено {updated} из {total} товаров')

        self.stdout.write(self.style.SUCCESS(f'Готово. Популярность обновлена для {updated} товаров.'))