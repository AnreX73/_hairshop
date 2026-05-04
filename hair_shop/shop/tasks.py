def compress_review_media(media_id: int):
    """Сжимает фото или видео отзыва"""
    import os
    from io import BytesIO
    from PIL import Image
    from django.core.files.base import ContentFile

    from shop.models import ReviewMedia  # поправь путь

    try:
        obj = ReviewMedia.objects.get(pk=media_id)
    except ReviewMedia.DoesNotExist:
        return

    if not obj.file:
        obj.status = 'done'
        obj.save(update_fields=['status'])
        return

    obj.status = 'processing'
    obj.save(update_fields=['status'])

    try:
        if obj.media_type == 'photo':
            # ── Сжатие фото (Pillow → WebP) ──────────────────────────────
            with obj.file.open('rb') as f:
                img = Image.open(f)
                img.load()

            if img.mode in ('RGBA', 'LA', 'PA'):
                bg = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'PA':
                    img = img.convert('RGBA')
                bg.paste(img, mask=img.split()[-1])
                img = bg
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            img.thumbnail((1920, 1920), Image.LANCZOS)

            buffer = BytesIO()
            img.save(buffer, format='WEBP', quality=82, optimize=True)
            buffer.seek(0)

            name = os.path.splitext(os.path.basename(obj.file.name))[0]
            obj.file_compressed.save(f"{name}.webp", ContentFile(buffer.read()), save=False)

        else:
            # ── Сжатие видео (ffmpeg) ─────────────────────────────────────
            import tempfile
            import subprocess
            import imageio_ffmpeg

            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_in:
                with obj.file.open('rb') as f:
                    tmp_in.write(f.read())
                tmp_in_path = tmp_in.name

            tmp_out_path = tmp_in_path.replace('.mp4', '_c.mp4')

            cmd = [
                ffmpeg_path,
                '-i', tmp_in_path,
                '-vf', 'scale=1280:-2',
                '-c:v', 'libx264',
                '-crf', '28',
                '-preset', 'fast',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-movflags', '+faststart',
                '-y',
                tmp_out_path,
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=120)
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg: {result.stderr.decode()}")

            name = os.path.splitext(os.path.basename(obj.file.name))[0]
            with open(tmp_out_path, 'rb') as f:
                obj.file_compressed.save(f"{name}_c.mp4", ContentFile(f.read()), save=False)

            for p in (tmp_in_path, tmp_out_path):
                try:
                    os.unlink(p)
                except Exception:
                    pass

        obj.status = 'done'
        obj.save(update_fields=['file_compressed', 'status'])

    except Exception:
        obj.status = 'error'
        obj.save(update_fields=['status'])
        raise