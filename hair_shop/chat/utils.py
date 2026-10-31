import io
import uuid

from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_SIZE = (1920, 1920)
WEBP_QUALITY = 82


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
