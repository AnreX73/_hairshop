# validators.py
import os

from django.core.exceptions import ValidationError

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi"}
MAX_IMAGE_SIZE_MB = 10
MAX_VIDEO_SIZE_MB = 100

VIDEO_INSTRUCTION_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".avi"}
MAX_VIDEO_INSTRUCTION_SIZE_MB = 100


def validate_video_instruction(file):
    """Проверка файла видео-инструкции (вертикальные ролики)."""
    ext = os.path.splitext(file.name)[1].lower()

    if ext not in VIDEO_INSTRUCTION_EXTENSIONS:
        raise ValidationError(
            "Недопустимый формат видео. Разрешены: "
            f"{', '.join(sorted(VIDEO_INSTRUCTION_EXTENSIONS))}"
        )

    size_mb = file.size / (1024 * 1024)
    if size_mb > MAX_VIDEO_INSTRUCTION_SIZE_MB:
        raise ValidationError(
            f"Видео не должно превышать {MAX_VIDEO_INSTRUCTION_SIZE_MB} МБ."
        )


def validate_review_media(file):
    ext = os.path.splitext(file.name)[1].lower()
    allowed = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS

    if ext not in allowed:
        raise ValidationError(
            f"Недопустимый формат файла. Разрешены: {', '.join(allowed)}"
        )

    size_mb = file.size / (1024 * 1024)
    if ext in ALLOWED_VIDEO_EXTENSIONS and size_mb > MAX_VIDEO_SIZE_MB:
        raise ValidationError(f"Видео не должно превышать {MAX_VIDEO_SIZE_MB} МБ.")
    if ext in ALLOWED_IMAGE_EXTENSIONS and size_mb > MAX_IMAGE_SIZE_MB:
        raise ValidationError(f"Фото не должно превышать {MAX_IMAGE_SIZE_MB} МБ.")
