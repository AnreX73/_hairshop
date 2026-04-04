"""
Management command: import_wb_products

Положи файл в:
    your_app/management/commands/import_wb_products.py

Убедись что рядом есть пустые __init__.py:
    your_app/management/__init__.py
    your_app/management/commands/__init__.py

Использование:
    # Посмотреть что будет импортировано (без записи в БД)
    python manage.py import_wb_products --category_id 8 --dry-run

    # Импорт одной категории
    python manage.py import_wb_products --category_id 8

    # Импорт всех категорий сразу
    python manage.py import_wb_products --all

    # Импорт без скачивания фото
    python manage.py import_wb_products --all --no-photos

Структура папки с файлами (положи рядом с manage.py):
    wb_exports/
        category_4.xlsx   ← Волосы для наращивания
        category_5.xlsx   ← Канекалон
        category_7.xlsx   ← Ободки
        category_8.xlsx   ← Резинки
        category_9.xlsx   ← Парики
        category_10.xlsx  ← Шиньоны

Как формируется group_slug:
    Slug НЕ задаётся в скрипте явно — его генерирует метод save() модели:
        raw_value = f"{self.name}_{self.product_group}"
        self.group_slug = make_slug(raw_value)
    Например: name='Афрорезинка', product_group='11' → 'afrorezinka_11'
    Все товары одной группы получат одинаковый slug автоматически.

    НО: bulk_create не вызывает save() — поэтому slug генерируем
    здесь в скрипте по той же логике что и в модели.
"""

import os
import time
import hashlib

import requests
import pandas as pd

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

# Поменяй 'shop' на имя своего приложения
from shop.models import Product, ProductImage, Category


# ═══════════════════════════════════════════════════════════════════════════════
# НАСТРОЙКИ
# ═══════════════════════════════════════════════════════════════════════════════

WB_EXPORT_DIR = os.path.join(settings.BASE_DIR, 'wb_exports')

CATEGORY_FILES = {
    4:  'category_4.xlsx',   # Волосы для наращивания
    5:  'category_5.xlsx',   # Канекалон
    7:  'category_7.xlsx',   # Ободки
    8:  'category_8.xlsx',   # Резинки
    9:  'category_9.xlsx',   # Парики
    10: 'category_10.xlsx',  # Шиньоны
}

PHOTO_DELAY = 0.3


# ═══════════════════════════════════════════════════════════════════════════════
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════════════════════

def clean(value) -> str:
    """Пустые ячейки Excel (NaN) → пустая строка ''."""
    if pd.isna(value):
        return ''
    return str(value).strip()


def clean_decimal(value):
    """Числовое значение → float, пустое → None (NULL в БД)."""
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def clean_int(value) -> int:
    """Числовое значение → int, пустое или ошибка → 0."""
    if pd.isna(value):
        return 0
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return 0


def get_col(row: pd.Series, *col_names: str) -> str:
    """
    Безопасно читает колонку из строки DataFrame.
    Принимает несколько возможных имён — возвращает первое непустое.

    Нужно потому что:
    1. Разные категории имеют разный набор колонок
    2. Одно поле в разных файлах может называться чуть по-разному

    Пример:
        get_col(row, 'Вес с упаковкой', 'Вес упаковки')
        → вернёт первое непустое из двух вариантов названия
    """
    for name in col_names:
        if name in row.index:
            val = clean(row[name])
            if val:
                return val
    return ''


def make_slug(text: str) -> str:
    """
    Транслит + slug. Повторяет логику make_slug() из models.py.

    ВАЖНО: эта функция должна быть идентична той что в models.py —
    иначе slug сгенерированный здесь будет отличаться от того
    что сгенерирует модель при ручном создании товара через admin.

    Пример: 'Афрорезинка_11' → 'afrorezinka_11'
    """
    TRANSLIT = {
        'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo','ж':'zh',
        'з':'z','и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o',
        'п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'h','ц':'ts',
        'ч':'ch','ш':'sh','щ':'sch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu',
        'я':'ya',
    }
    result = ''
    for ch in text.lower():
        result += TRANSLIT.get(ch, ch)

    slug = ''.join(c if c.isalnum() else '-' for c in result)
    slug = '-'.join(part for part in slug.split('-') if part)
    return slug[:255] or 'product'


def download_photo(url: str, save_dir: str) -> str:
    """
    Скачивает фото, сохраняет в save_dir.
    Возвращает путь относительно MEDIA_ROOT или '' при ошибке.

    User-Agent и Referer нужны чтобы WB не вернул 403 Forbidden —
    сервер проверяет что запрос выглядит как браузерный.
    """
    try:
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
            ),
            'Referer': 'https://www.wildberries.ru/',
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        # MD5-хэш URL как имя файла — гарантирует уникальность без дублей
        ext   = url.split('.')[-1].split('?')[0]
        fname = hashlib.md5(url.encode()).hexdigest() + '.' + ext
        fpath = os.path.join(save_dir, fname)

        with open(fpath, 'wb') as f:
            f.write(resp.content)

        return os.path.relpath(fpath, settings.MEDIA_ROOT)

    except Exception:
        return ''


def read_wb_excel(filepath: str) -> pd.DataFrame:
    """
    Читает Excel-файл. Структура после редакции:
        Строка 0: заголовки
        Строка 1+: данные

    Дополнительно объединяет дублирующие колонки (например Состав и Состав.1
    в категории 9 — это два поля состава которые pandas различает добавляя .1).
    """
    try:
        df = pd.read_excel(filepath, header=0)
    except Exception as e:
        raise CommandError(f'Не удалось открыть {filepath}: {e}')

    # В category_9 есть колонки 'Состав' и 'Состав.1' — объединяем:
    # берём первое непустое значение из обеих колонок
    if 'Состав.1' in df.columns:
        df['Состав'] = df['Состав'].fillna('').astype(str).str.strip()
        df['Состав.1'] = df['Состав.1'].fillna('').astype(str).str.strip()
        # Если основной Состав пустой — берём из Состав.1
        df['Состав'] = df.apply(
            lambda row: row['Состав'] if row['Состав'] else row['Состав.1'],
            axis=1
        )
        df = df.drop(columns=['Состав.1'])

    # Убираем строки без артикула
    df = df[df['Артикул'].notna()].copy()

    # Убираем строки где Группа не число
    df = df[pd.to_numeric(df['Группа'], errors='coerce').notna()].copy()
    df['Группа'] = pd.to_numeric(df['Группа']).astype(int)

    df = df.reset_index(drop=True)
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# COMMAND
# ═══════════════════════════════════════════════════════════════════════════════

class Command(BaseCommand):
    help = 'Импорт товаров из выгрузок Wildberries (.xlsx) по категориям'

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '--category_id',
            type=int,
            choices=CATEGORY_FILES.keys(),
            help=f'ID одной категории. Доступные: {list(CATEGORY_FILES.keys())}',
        )
        group.add_argument(
            '--all',
            action='store_true',
            help='Импортировать все категории',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать первые 10 строк без записи в БД',
        )
        parser.add_argument(
            '--no-photos',
            action='store_true',
            help='Не скачивать фото',
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=PHOTO_DELAY,
            help=f'Пауза между скачиванием фото, сек (default: {PHOTO_DELAY})',
        )

    def handle(self, *args, **options):
        if options['all']:
            category_ids = list(CATEGORY_FILES.keys())
        else:
            category_ids = [options['category_id']]

        for category_id in category_ids:
            self.stdout.write(
                self.style.HTTP_INFO(f'\n─── Категория {category_id} ───')
            )
            self._import_category(category_id, options)

        self.stdout.write(self.style.SUCCESS('\nВсё готово!'))

    def _import_category(self, category_id: int, options: dict):
        dry_run   = options['dry_run']
        no_photos = options['no_photos']
        delay     = options['delay']

        # ── Категория из БД ───────────────────────────────────────────────────
        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Категория id={category_id} не найдена в БД')
            )
            return

        # ── Файл ──────────────────────────────────────────────────────────────
        filepath = os.path.join(WB_EXPORT_DIR, CATEGORY_FILES[category_id])
        if not os.path.exists(filepath):
            self.stdout.write(self.style.ERROR(f'Файл не найден: {filepath}'))
            return

        self.stdout.write(f'Читаю: {filepath}')
        df    = read_wb_excel(filepath)
        total = len(df)
        self.stdout.write(
            f'Строк: {total}, групп: {df["Группа"].nunique()}'
        )

        # ── Dry-run ───────────────────────────────────────────────────────────
        if dry_run:
            self.stdout.write(self.style.WARNING('--- DRY-RUN, БД не изменяется ---'))
            for _, row in df.head(10).iterrows():
                # Показываем как будет выглядеть slug
                name  = clean(row['Наименование'])
                group = str(int(row['Группа']))
                slug  = make_slug(f'{name}_{group}')
                self.stdout.write(
                    f'  {clean(row["Артикул"]):25s} | '
                    f'{name:30s} | '
                    f'slug: {slug:35s} | '
                    f'цена: {clean_int(row.get("цена", 0))}'
                )
            if total > 10:
                self.stdout.write(f'  ... ещё {total - 10} строк')
            return

        # ── Папка для фото ────────────────────────────────────────────────────
        gallery_dir = os.path.join(settings.MEDIA_ROOT, 'products', 'gallery')
        os.makedirs(gallery_dir, exist_ok=True)

        # ── Формируем объекты Product ─────────────────────────────────────────
        # bulk_create НЕ вызывает save() модели — поэтому slug генерируем
        # здесь вручную по той же формуле: make_slug(f"{name}_{group}")
        products_to_create = []

        for _, row in df.iterrows():
            article = clean(row['Артикул'])
            if not article:
                continue

            name         = clean(row['Наименование'])
            product_group = str(int(row['Группа']))

            # Воспроизводим логику save() из модели:
            # group_slug = make_slug(f"{self.name}_{self.product_group}")
            group_slug = make_slug(f'{name}_{product_group}')

            # Рейтинг WB 0–10 → нормируем до 0–5
            try:
                rating = float(row.get('Рейтинг') or 0)
                if rating > 5:
                    rating = round(rating / 2, 1)
            except (ValueError, TypeError):
                rating = 0.0

            p = Product(
                # ── Идентификация и группировка ────────────────────────────
                article       = article,
                name          = name,
                product_group = product_group,
                group_slug    = group_slug,

                # ── Категория ──────────────────────────────────────────────
                category = category,

                # ── Основные поля (есть во всех файлах) ───────────────────
                description = clean(row.get('Описание', '')),
                color       = clean(row.get('Цвет', '')),

                # ── Габариты упаковки ──────────────────────────────────────
                # get_col пробует оба варианта названия колонки
                packaging_weight = clean_decimal(
                    row.get('Вес с упаковкой') or row.get('Вес упаковки')
                ),
                packaging_height = clean_decimal(row.get('Высота упаковки')),
                packaging_length = clean_decimal(row.get('Длина упаковки')),
                packaging_width  = clean_decimal(row.get('Ширина упаковки')),

                # ── Характеристики (есть не во всех категориях) ────────────
                # get_col вернёт '' если колонки нет — поле останется пустым
                hair_material         = get_col(row, 'Состав'),
                hair_length           = get_col(row, 'Длина волос'),
                hair_type             = get_col(row, 'Вид волос'),
                number_of_strands     = get_col(row, 'Количество прядей'),
                hair_extension_method = get_col(row, 'Способ наращивания волос'),
                decoration            = get_col(row, 'Декоративные элементы'),
                kit                   = get_col(row, 'Комплектация'),
                country_of_origin     = get_col(row, 'Страна производства'),
                package               = get_col(row, 'Упаковка'),

                # ── Цена и скидка (из файла) ───────────────────────────────
                # clean_int возвращает 0 если ячейка пустая
                price               = clean_int(row.get('цена', 0)),
                discount_percentage = clean_int(row.get('скидка', 0)),

                # ── Статус и рейтинг ───────────────────────────────────────
                is_available = True,
                rating       = rating,

                # Сохраняем все URL фото строкой — удобно видеть в admin
                note_for_manager = clean(row.get('Фото', '')),
            )

            # _photo_urls — временный атрибут, НЕ поле модели.
            # Не пишется в БД, нужен только для создания ProductImage ниже.
            photo_raw     = clean(row.get('Фото', ''))
            p._photo_urls = [u.strip() for u in photo_raw.split(';') if u.strip()]

            products_to_create.append(p)

        # ── bulk_create для товаров ───────────────────────────────────────────
        # Один SQL INSERT. В PostgreSQL возвращает объекты с заполненными id.
        self.stdout.write('Записываю товары в БД...')
        created_products = Product.objects.bulk_create(
            products_to_create,
            batch_size=200,
        )
        self.stdout.write(f'Создано товаров: {len(created_products)}')

        # ── Фото ──────────────────────────────────────────────────────────────
        if no_photos:
            self.stdout.write('Фото пропущены (--no-photos).')
            return

        self.stdout.write('Скачиваю фото...')
        images_to_create = []
        photo_ok     = 0
        photo_errors = 0

        for i, product in enumerate(created_products, start=1):
            photo_urls = getattr(product, '_photo_urls', [])
            if not photo_urls:
                continue

            self.stdout.write(
                f'  [{i}/{len(created_products)}] {product.article[:40]}',
                ending='\r',
            )
            self.stdout.flush()

            for order, url in enumerate(photo_urls):
                # order=0 → главное фото (его вернёт main_image property в модели)
                # order=1,2... → галерея
                path = download_photo(url, gallery_dir)
                if path:
                    images_to_create.append(
                        ProductImage(
                            product    = product,
                            image      = path,
                            media_type = 'image',
                            order      = order,
                        )
                    )
                    photo_ok += 1
                else:
                    photo_errors += 1

                time.sleep(delay)

        self.stdout.write('')
        self.stdout.write('Записываю изображения в БД...')
        ProductImage.objects.bulk_create(images_to_create, batch_size=500)

        self.stdout.write(
            self.style.SUCCESS(
                f'Категория {category_id} ({category.name}): '
                f'товаров {len(created_products)}, '
                f'фото {photo_ok} ок / {photo_errors} ошибок'
            )
        )