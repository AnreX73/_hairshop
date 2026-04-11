import pandas as pd
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from shop.models import Product  # замените your_app на имя вашего приложения

EXPORT_DIR = Path(settings.BASE_DIR) / 'wb_exports'
FILE_NAME = 'products_export.xlsx'


class Command(BaseCommand):
    help = f'Экспорт всех продуктов в {EXPORT_DIR / FILE_NAME}'

    def handle(self, *args, **options):
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
# отсортировать по дате создания начиная с певого 
        qs = Product.objects.select_related('category').values(
            'id',
           'name',
            'article',
            'product_group',
            'group_slug',
            'note_for_manager',
            'category__name',
            'description',
            'color',
            'hair_length',
            'hair_width',
            'hair_material',
            'number_of_strands',
            'hair_extension_method',
            'hair_type',
            'country_of_origin',
            'kit',
            'decoration',
            'package',
            'packaging_weight',
            'packaging_length',
            'packaging_width',
            'packaging_height',
            'price',
            'discount_percentage',
            'is_available',
            'is_hit',
            'rating',
            'reviews_count',
            'popularity',
            
        ).order_by('created_at')

        df = pd.DataFrame(list(qs))
        df.rename(columns={'category__name': 'category'}, inplace=True)

        file_path = EXPORT_DIR / FILE_NAME
        df.to_excel(file_path, index=False)

        self.stdout.write(self.style.SUCCESS(
            f'Готово. Экспортировано {len(df)} записей → {file_path}'
        ))