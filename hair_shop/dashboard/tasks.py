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
    from shop.models import ProductImage  # поправь путь под свой проект

    try:
        obj = ProductImage.objects.get(pk=image_id)
    except ProductImage.DoesNotExist:
        return

    if not obj.image:
        obj.status = "done"
        obj.save(update_fields=["status"])
        return

    obj.status = "processing"
    obj.save(update_fields=["status"])

    try:
        with obj.image.open("rb") as f:
            img = Image.open(f)
            img.load()  # загружаем в память пока файл открыт

        # Нормализуем цветовое пространство → RGB
        if img.mode in ("RGBA", "LA", "PA"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "PA":
                img = img.convert("RGBA")
            bg.paste(img, mask=img.split()[-1])
            img = bg
        elif img.mode == "P":
            img = img.convert("RGB")
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Уменьшаем если шире/выше 1920px
        MAX_SIZE = (1920, 1920)
        img.thumbnail(MAX_SIZE, Image.LANCZOS)

        # Сохраняем в буфер как WebP
        buffer = BytesIO()
        img.save(buffer, format="WEBP", quality=82, optimize=True)
        buffer.seek(0)

        original_name = os.path.splitext(os.path.basename(obj.image.name))[0]
        compressed_name = f"{original_name}.webp"

        obj.image_compressed.save(
            compressed_name, ContentFile(buffer.read()), save=False
        )
        obj.status = "done"
        obj.save(update_fields=["image_compressed", "status"])

    except Exception:
        obj.status = "error"
        obj.save(update_fields=["status"])
        raise  # Django Q2 залогирует трейсбек


def compress_product_video(image_id: int):
    """
    Фоновая задача Django Q2.
    Сжимает видео товара через ffmpeg (imageio-ffmpeg).
    Уменьшает разрешение до 1280px и битрейт.
    """
    import os
    import tempfile
    import imageio_ffmpeg
    import subprocess
    from shop.models import ProductImage  # поправь путь

    try:
        obj = ProductImage.objects.get(pk=image_id)
    except ProductImage.DoesNotExist:
        return

    if not obj.video:
        obj.status = "done"
        obj.save(update_fields=["status"])
        return

    obj.status = "processing"
    obj.save(update_fields=["status"])

    try:
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

        # Читаем оригинал во временный файл
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_in:
            with obj.video.open("rb") as f:
                tmp_in.write(f.read())
            tmp_in_path = tmp_in.name

        tmp_out_path = tmp_in_path.replace(".mp4", "_compressed.mp4")

        # ffmpeg команда:
        # -vf scale — уменьшаем до 1280px по ширине, высота пропорционально
        # -c:v libx264 — кодек H.264 (универсальный)
        # -crf 28 — качество (18=лучше, 28=меньше размер, для клипов магазина норм)
        # -preset fast — баланс скорость/сжатие
        # -c:a aac -b:a 128k — аудио
        # -movflags +faststart — для быстрого старта в браузере
        cmd = [
            ffmpeg_path,
            "-i",
            tmp_in_path,
            "-vf",
            "scale=1280:-2",  # -2 чтобы высота была чётной
            "-c:v",
            "libx264",
            "-crf",
            "28",
            "-preset",
            "fast",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            "-y",  # перезаписать если существует
            tmp_out_path,
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=120)

        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg error: {result.stderr.decode()}")

        # Сохраняем сжатое видео в Django
        original_name = os.path.splitext(os.path.basename(obj.video.name))[0]
        compressed_name = f"{original_name}_compressed.mp4"

        with open(tmp_out_path, "rb") as f:
            from django.core.files.base import ContentFile

            obj.video_compressed.save(
                compressed_name, ContentFile(f.read()), save=False
            )

        obj.status = "done"
        obj.save(update_fields=["video_compressed", "status"])

    except Exception:
        obj.status = "error"
        obj.save(update_fields=["status"])
        raise

    finally:
        # Чистим временные файлы
        for path in (tmp_in_path, tmp_out_path):
            try:
                os.unlink(path)
            except Exception:
                pass
