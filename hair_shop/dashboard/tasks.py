# dashboard/tasks.py
import logging
import os
from io import BytesIO

from django.core.files.base import ContentFile
from django.db import transaction
from django_q.tasks import async_task
from PIL import Image

logger = logging.getLogger(__name__)


def enqueue_video_instruction_compression(video_id: int):
    """Ставит сжатие видео-инструкции в очередь после коммита."""

    def enqueue():
        try:
            async_task(
                "dashboard.tasks.compress_video_instruction",
                video_id,
                task_name=f"compress_video_instruction_{video_id}",
                q_options={"timeout": 540},
            )
        except Exception:
            logger.exception(
                "Не удалось поставить сжатие видео-инструкции %s в очередь",
                video_id,
            )
            from shop.models import VideoInstruction

            VideoInstruction.objects.filter(pk=video_id, status="pending").update(
                status="error"
            )

    transaction.on_commit(enqueue)


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
    import subprocess
    import tempfile

    import imageio_ffmpeg

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


def compress_video_instruction(video_id: int):
    """
    Фоновая задача Django Q2.

    Готовит вертикальное видео-инструкцию для сайта:
    сжимает до 720p (H.264, CRF 28) и делает JPEG-обложку.
    После успешного сжатия оригинал удаляется.
    """
    import os
    import subprocess
    import tempfile

    import imageio_ffmpeg

    from shop.models import VideoInstruction

    try:
        obj = VideoInstruction.objects.get(pk=video_id)
    except VideoInstruction.DoesNotExist:
        return

    if not obj.file:
        obj.status = "error"
        obj.save(update_fields=["status", "updated_at"])
        return

    obj.status = "processing"
    obj.save(update_fields=["status", "updated_at"])

    tmp_in_path = tmp_out_path = tmp_poster_path = None

    try:
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

        suffix = os.path.splitext(obj.file.name)[1].lower() or ".mp4"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_in:
            with obj.file.open("rb") as source:
                while chunk := source.read(1024 * 1024):
                    tmp_in.write(chunk)
            tmp_in_path = tmp_in.name

        tmp_out_path = f"{tmp_in_path}_compressed.mp4"
        tmp_poster_path = f"{tmp_in_path}_poster.jpg"

        # 720p по ширине, без апскейла. Для вертикали 1080x1920 → 720x1280.
        cmd = [
            ffmpeg_path,
            "-nostdin",
            "-loglevel",
            "error",
            "-y",
            "-i",
            tmp_in_path,
            "-vf",
            "scale=w='min(720,iw)':h=-2",
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-crf",
            "28",
            "-preset",
            "fast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            tmp_out_path,
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=450)
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace")
            raise RuntimeError(f"ffmpeg error: {stderr}")

        poster_cmd = [
            ffmpeg_path,
            "-nostdin",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            "1",
            "-i",
            tmp_out_path,
            "-frames:v",
            "1",
            "-vf",
            "scale=w='min(360,iw)':h=-2",
            "-q:v",
            "3",
            tmp_poster_path,
        ]
        poster_result = subprocess.run(poster_cmd, capture_output=True, timeout=60)
        if poster_result.returncode != 0:
            # Очень короткий ролик — пробуем самый первый кадр.
            poster_cmd[poster_cmd.index("-ss") + 1] = "0"
            poster_result = subprocess.run(poster_cmd, capture_output=True, timeout=60)

        from django.core.files.base import ContentFile

        base_name = f"video_instruction_{obj.pk}"
        with open(tmp_out_path, "rb") as compressed:
            obj.compressed_file.save(
                f"{base_name}.mp4", ContentFile(compressed.read()), save=False
            )

        if poster_result.returncode == 0 and os.path.exists(tmp_poster_path):
            with open(tmp_poster_path, "rb") as poster:
                obj.poster.save(
                    f"{base_name}.jpg", ContentFile(poster.read()), save=False
                )

        obj.status = "done"
        obj.save(
            update_fields=[
                "compressed_file",
                "poster",
                "status",
                "updated_at",
            ]
        )

        # Оригинал больше не нужен — экономим диск.
        original = obj.file
        obj.file = ""
        obj.save(update_fields=["file", "updated_at"])
        if original:
            try:
                original.delete(save=False)
            except Exception:
                pass

    except Exception:
        obj.status = "error"
        obj.save(update_fields=["status", "updated_at"])
        raise

    finally:
        for path in (tmp_in_path, tmp_out_path, tmp_poster_path):
            if not path:
                continue
            try:
                os.unlink(path)
            except Exception:
                pass
