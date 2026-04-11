import pandas as pd
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from shop.models import Product, Category  # замените your_app на имя вашего приложения

IMPORT_DIR = Path(settings.BASE_DIR) / 'wb_exports'
FILE_NAME = 'products_change_1.xlsx'


class Command(BaseCommand):
    help = f'Полная синхронизация полей Product из {IMPORT_DIR / FILE_NAME}'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Только показать что будет сделано, без записи в БД',
        )
        parser.add_argument(
            '--diagnose',
            action='store_true',
            help='Показать артикулы из файла которых нет в БД (первые 20)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        diagnose = options['diagnose']

        file_path = IMPORT_DIR / FILE_NAME
        if not file_path.exists():
            raise CommandError(f'Файл не найден: {file_path}')

        try:
            df = pd.read_excel(file_path, dtype=str)
        except Exception as e:
            raise CommandError(f'Ошибка чтения файла: {e}')

        # Чистим пробелы во всех строковых ячейках
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)

        required_columns = {'article', 'category', 'hair_length', 'hair_width', 'number_of_strands'}
        missing = required_columns - set(df.columns)
        if missing:
            raise CommandError(f'В файле отсутствуют столбцы: {missing}')

        self.stdout.write(f'Строк в файле: {len(df)}')

        # Все артикулы из БД для быстрого сравнения
        db_articles = set(Product.objects.values_list('article', flat=True))
        file_articles = set(df['article'].dropna().str.strip())

        not_in_db = file_articles - db_articles
        self.stdout.write(f'Найдено в БД: {len(file_articles - not_in_db)} из {len(file_articles)}')

        if not_in_db:
            self.stdout.write(self.style.WARNING(
                f'Не найдено в БД: {len(not_in_db)} артикулов'
            ))

        if diagnose:
            self.stdout.write('\n--- ДИАГНОСТИКА: артикулы из файла которых нет в БД ---')
            for a in sorted(not_in_db)[:20]:
                # Показываем hex чтобы увидеть скрытые символы
                self.stdout.write(f'  "{a}"  hex: {a.encode().hex()}')
            if len(not_in_db) > 20:
                self.stdout.write(f'  ... и ещё {len(not_in_db) - 20}')
            self.stdout.write('--- конец диагностики ---\n')
            return

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — запись в БД не производится'))

        # Загружаем все нужные продукты одним запросом
        products = {
            p.article: p
            for p in Product.objects.select_related('category').filter(article__in=file_articles)
        }

        # Кэш категорий
        categories = {c.name: c for c in Category.objects.all()}

        updated = 0
        not_found = 0
        cat_errors = 0
        missing_articles = []

        for _, row in df.iterrows():
            article = row.get('article')
            if pd.isna(article) or not str(article).strip():
                continue
            article = str(article).strip()

            product = products.get(article)
            if not product:
                not_found += 1
                missing_articles.append(article)
                continue

            raw_category = row.get('category')
            if pd.notna(raw_category) and str(raw_category).strip():
                cat_name = str(raw_category).strip()
                cat = categories.get(cat_name)
                if cat:
                    product.category = cat
                else:
                    self.stdout.write(self.style.WARNING(
                        f'Категория не найдена: "{cat_name}" (артикул {article})'
                    ))
                    cat_errors += 1

            raw_length = row.get('hair_length')
            product.hair_length = str(raw_length).strip() if pd.notna(raw_length) and str(raw_length).strip() else ''

            raw_width = row.get('hair_width')
            product.hair_width = str(raw_width).strip() if pd.notna(raw_width) and str(raw_width).strip() else None

            raw_strands = row.get('number_of_strands')
            product.number_of_strands = str(raw_strands).strip() if pd.notna(raw_strands) and str(raw_strands).strip() else ''

            if not dry_run:
                product.save(update_fields=['category', 'hair_length', 'hair_width', 'number_of_strands'])
            updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Готово. Обновлено: {updated}, не найдено: {not_found}, ошибок категорий: {cat_errors}'
        ))

        if missing_articles and not dry_run:
            missing_path = IMPORT_DIR / 'not_found_articles.txt'
            missing_path.write_text('\n'.join(missing_articles), encoding='utf-8')
            self.stdout.write(self.style.WARNING(
                f'Пропущенные артикулы сохранены → {missing_path}'
            ))