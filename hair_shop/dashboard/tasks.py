# dashboard/tasks.py
import os
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile


def compress_product_image(image_id: int):
    """
    Фоновая задача Django Q2.
    Сжимает оригинальное фото товара в WebP и сохраняет в image_compressed.
    """
    # Импорт внутри функции — обязателен для Django Q2 чтобы избежать circular import
    from shop.models import ProductImage   # поправь путь под свой проект

    try:
        obj = ProductImage.objects.get(pk=image_id)
    except ProductImage.DoesNotExist:
        return

    if not obj.image:
        obj.status = 'done'
        obj.save(update_fields=['status'])
        return

    obj.status = 'processing'
    obj.save(update_fields=['status'])

    try:
        with obj.image.open('rb') as f:
            img = Image.open(f)
            img.load()   # загружаем в память пока файл открыт

        # Нормализуем цветовое пространство → RGB
        if img.mode in ('RGBA', 'LA', 'PA'):
            bg = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'PA':
                img = img.convert('RGBA')
            bg.paste(img, mask=img.split()[-1])
            img = bg
        elif img.mode == 'P':
            img = img.convert('RGB')
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # Уменьшаем если шире/выше 1920px
        MAX_SIZE = (1920, 1920)
        img.thumbnail(MAX_SIZE, Image.LANCZOS)

        # Сохраняем в буфер как WebP
        buffer = BytesIO()
        img.save(buffer, format='WEBP', quality=82, optimize=True)
        buffer.seek(0)

        original_name = os.path.splitext(os.path.basename(obj.image.name))[0]
        compressed_name = f"{original_name}.webp"

        obj.image_compressed.save(
            compressed_name,
            ContentFile(buffer.read()),
            save=False
        )
        obj.status = 'done'
        obj.save(update_fields=['image_compressed', 'status'])

    except Exception:
        obj.status = 'error'
        obj.save(update_fields=['status'])
        raise   # Django Q2 залогирует трейсбек
