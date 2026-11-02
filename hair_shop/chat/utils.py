import io
import os
import re
import subprocess
import tempfile
import uuid

from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_SIZE = (1920, 1920)
WEBP_QUALITY = 82

MAX_AUDIO_BYTES = 10 * 1024 * 1024
MAX_AUDIO_SECONDS = 60
AUDIO_DURATION_TOLERANCE = 1
AUDIO_BITRATE = "64k"
AUDIO_SAMPLE_RATE = 44100

_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")


def compress_chat_image(uploaded):
    """Сжимает фото из чата в WebP, как compress_product_image.

    Клиент тоже сжимает фото перед отправкой, но серверная проверка нужна,
    чтобы в хранилище не попадали огромные файлы вроде 6000×4000.
    """
    if not uploaded or not getattr(uploaded, "size", 0):
        raise ValueError("Файл не передан.")
    if uploaded.size > MAX_UPLOAD_BYTES:
        raise ValueError("Файл больше 10 МБ.")

    try:
        image = Image.open(uploaded)
        image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ValueError("Не удалось распознать изображение.")

    image = ImageOps.exif_transpose(image)

    if image.mode in ("RGBA", "LA", "PA"):
        background = Image.new("RGB", image.size, (255, 255, 255))
        if image.mode == "PA":
            image = image.convert("RGBA")
        background.paste(image, mask=image.split()[-1])
        image = background
    elif image.mode != "RGB":
        image = image.convert("RGB")

    image.thumbnail(MAX_SIZE, Image.LANCZOS)

    buffer = io.BytesIO()
    image.save(buffer, format="WEBP", quality=WEBP_QUALITY, optimize=True)
    buffer.seek(0)

    return ContentFile(buffer.read(), name=f"{uuid.uuid4().hex}.webp")


def _ffmpeg_binary():
    try:
        import imageio_ffmpeg
    except ImportError as exc:
        raise ValueError("Обработка аудио недоступна.") from exc
    return imageio_ffmpeg.get_ffmpeg_exe()


def _probe_duration(path):
    """Длительность по данным самого файла, а не по сведениям браузера."""
    result = subprocess.run(
        [_ffmpeg_binary(), "-hide_banner", "-i", path],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    stderr = result.stderr or ""
    if "Audio:" not in stderr:
        raise ValueError("Файл не является аудио.")

    match = _DURATION_RE.search(stderr)
    if not match:
        raise ValueError("Не удалось определить длительность записи.")

    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def convert_chat_audio(uploaded):
    """Проверяет запись и перекодирует её в MP3 для всех браузеров.

    Chrome присылает webm/opus, Safari — mp4/aac. Единый MP3 играет везде,
    поэтому перекодируем на сервере, а не полагаемся на кодек браузера.
    Максимальная длина записи — 60 секунд.
    """
    if not uploaded or not getattr(uploaded, "size", 0):
        raise ValueError("Файл не передан.")
    if uploaded.size > MAX_AUDIO_BYTES:
        raise ValueError("Файл больше 10 МБ.")

    suffix = os.path.splitext(getattr(uploaded, "name", "") or "")[1] or ".audio"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as source:
        for chunk in uploaded.chunks():
            source.write(chunk)
        source_path = source.name
    output_path = f"{source_path}.mp3"

    try:
        duration = _probe_duration(source_path)
        if duration > MAX_AUDIO_SECONDS + AUDIO_DURATION_TOLERANCE:
            raise ValueError("Запись длиннее 60 секунд.")

        result = subprocess.run(
            [
                _ffmpeg_binary(),
                "-y",
                "-v",
                "error",
                "-i",
                source_path,
                "-vn",
                "-ac",
                "1",
                "-ar",
                str(AUDIO_SAMPLE_RATE),
                "-b:a",
                AUDIO_BITRATE,
                "-t",
                str(MAX_AUDIO_SECONDS),
                "-f",
                "mp3",
                output_path,
            ],
            capture_output=True,
            timeout=120,
        )
        if result.returncode != 0 or not os.path.exists(output_path):
            raise ValueError("Не удалось обработать аудио.")

        with open(output_path, "rb") as converted:
            data = converted.read()
    except subprocess.TimeoutExpired as exc:
        raise ValueError("Обработка аудио заняла слишком много времени.") from exc
    finally:
        for path in (source_path, output_path):
            try:
                os.unlink(path)
            except OSError:
                pass

    seconds = max(1, min(MAX_AUDIO_SECONDS, round(duration)))
    return ContentFile(data, name=f"{uuid.uuid4().hex}.mp3"), seconds
