# <app>/management/commands/randomize_prices_by_group.py

import random
import math
from django.core.management.base import BaseCommand
from django.db import transaction
from shop.models import Product   # замените на вашу модель


class Command(BaseCommand):
    help = '''
    Заполняет price и discount_percentage для товаров с учётом групп.
    Если указано --num-groups, товары случайным образом разбиваются на указанное число виртуальных групп.
    Иначе используются реальные уникальные значения product_group (если их слишком много, будет предупреждение).
    Внутри одной группы цены и скидки одинаковы.
    '''

    def add_arguments(self, parser):
        parser.add_argument(
            '--num-groups',
            type=int,
            default=None,
            help='Количество групп, на которые случайным образом разбить все товары (игнорирует product_group)'
        )
        parser.add_argument(
            '--discount-groups-ratio',
            type=float,
            default=0.8,
            help='Минимальная доля групп со скидкой (округляется вверх, по умолчанию 0.8)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Только показать изменения без сохранения'
        )

    def handle(self, *args, **options):
        num_groups_param = options['num_groups']
        ratio = options['discount_groups_ratio']
        dry_run = options['dry_run']

        all_products = list(Product.objects.all())
        total_products = len(all_products)
        if total_products == 0:
            self.stdout.write(self.style.WARNING('Нет товаров.'))
            return

        # --- Определяем группы ---
        if num_groups_param is not None:
            # Искусственное разбиение на заданное количество групп
            num_groups = num_groups_param
            self.stdout.write(f'Используем виртуальные группы: {num_groups} групп (случайное распределение товаров).')
            # Случайно назначаем каждой товару номер группы от 0 до num_groups-1
            group_ids = [random.randint(0, num_groups - 1) for _ in range(total_products)]
            # Собираем словарь {group_id: list of products}
            groups_dict = {}
            for idx, product in enumerate(all_products):
                gid = group_ids[idx]
                groups_dict.setdefault(gid, []).append(product)
            # Преобразуем в список групп (каждая группа — это список товаров)
            groups = list(groups_dict.values())
        else:
            # Используем реальные product_group
            group_values = list(Product.objects.exclude(product_group__isnull=True)
                                 .values_list('product_group', flat=True)
                                 .distinct())
            num_groups = len(group_values)
            self.stdout.write(f'Найдено уникальных значений product_group: {num_groups}')

            # Если групп слишком много (например, > 20% от числа товаров), предупреждаем
            if num_groups > total_products * 0.2:
                self.stdout.write(self.style.WARNING(
                    f'Внимание: количество уникальных групп ({num_groups}) близко к числу товаров ({total_products}).\n'
                    f'Возможно, вы хотели использовать другое поле или указать --num-groups.'
                ))
                proceed = input('Продолжить с этими группами? (y/N): ')
                if proceed.lower() != 'y':
                    self.stdout.write('Отменено. Запустите с параметром --num-groups <желаемое_количество_групп>.')
                    return

            # Группируем товары по значениям product_group
            groups_dict = {}
            for product in all_products:
                g = product.product_group if product.product_group is not None else ''
                groups_dict.setdefault(g, []).append(product)
            groups = list(groups_dict.values())

        total_groups = len(groups)
        # Количество групп со скидкой (округление вверх, но не больше общего числа)
        discount_groups_count = min(total_groups, math.ceil(total_groups * ratio))

        # Перемешиваем группы и делим
        random.shuffle(groups)
        groups_with_discount = groups[:discount_groups_count]
        groups_without_discount = groups[discount_groups_count:]

        self.stdout.write(f'Всего групп: {total_groups}')
        self.stdout.write(f'Групп со скидкой: {len(groups_with_discount)} ({len(groups_with_discount)/total_groups*100:.1f}%)')
        self.stdout.write(f'Групп без скидки: {len(groups_without_discount)}')

        # Параметры для групп со скидкой
        FINAL_LOW, FINAL_HIGH = 1500, 2500
        DISCOUNT_CHOICES = [15, 20, 25]

        # Параметры для групп без скидки
        PRICE_LOW_NO_DISC, PRICE_HIGH_NO_DISC = 2000, 3500

        # Генерируем данные для каждой группы
        group_data = []  # список кортежей (список_товаров, price, discount)

        for group_products in groups_with_discount:
            discount = random.choice(DISCOUNT_CHOICES)
            # price_min/max для целых чисел
            price_min = (FINAL_LOW * 100 + (100 - discount) - 1) // (100 - discount)
            price_max = (FINAL_HIGH * 100) // (100 - discount)
            if price_min > price_max:
                price = price_min
            else:
                price = random.randint(price_min, price_max)
            group_data.append((group_products, price, discount))

        for group_products in groups_without_discount:
            price = random.randint(PRICE_LOW_NO_DISC, PRICE_HIGH_NO_DISC)
            group_data.append((group_products, price, 0))

        # --- Обновление ---
        if dry_run:
            self.stdout.write('\n--- DRY-RUN (без сохранения) ---')
            for group_products, price, discount in group_data:
                count = len(group_products)
                # Покажем первые 3 товара из группы как пример
                sample = ', '.join(str(p.id) for p in group_products[:3])
                self.stdout.write(f'Группа из {count} товаров (id: {sample}...): price={price}, discount={discount}%')
            return

        updated_total = 0
        with transaction.atomic():
            for group_products, price, discount in group_data:
                # Обновляем каждого товара в группе
                product_ids = [p.id for p in group_products]
                rows = Product.objects.filter(id__in=product_ids).update(
                    price=price,
                    discount_percentage=discount
                )
                updated_total += rows
                self.stdout.write(f'Обновлено {rows} товаров: price={price}, discount={discount}%')

        self.stdout.write(self.style.SUCCESS(
            f'\nГотово. Обновлено {updated_total} товаров.\n'
            f'Групп со скидкой: {len(groups_with_discount)}, без скидки: {len(groups_without_discount)}'
        ))