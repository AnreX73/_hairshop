"""
Management command: fetch_wb_videos

Скачивает видео с WB и перекодирует в H.264 для воспроизведения в браузере.

WB хранит видео в формате H.265 (HEVC) — браузеры его не поддерживают.
Поэтому после скачивания сразу перекодируем в H.264 через ffmpeg.

Зависимости:
    pip install yt-dlp
    ffmpeg — должен быть установлен и доступен в PATH

Использование:
    python manage.py fetch_wb_videos --category_id 4 --dry-run
    python manage.py fetch_wb_videos --category_id 4
    python manage.py fetch_wb_videos --all

Перед повторным запуском (если нужно перекачать):
    from shop.models import ProductImage
    ProductImage.objects.filter(media_type='video').delete()
    # и удали папку media/products/videos/ руками
"""

import os
import subprocess

import yt_dlp
import pandas as pd

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from shop.models import Product, ProductImage


# ═══════════════════════════════════════════════════════════════════════════════
# НАСТРОЙКИ
# ═══════════════════════════════════════════════════════════════════════════════

WB_EXPORT_DIR = os.path.join(settings.BASE_DIR, 'wb_exports')

CATEGORY_FILES = {
    4:  'category_4.xlsx',
    5:  'category_5.xlsx',
    7:  'category_7.xlsx',
    8:  'category_8.xlsx',
    9:  'category_9.xlsx',
    10: 'category_10.xlsx',
}


# ═══════════════════════════════════════════════════════════════════════════════
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════════════════════

def clean(value) -> str:
    if pd.isna(value):
        return ''
    return str(value).strip()


def make_safe_filename(text: str) -> str:
    """
    Транслит + очистка → безопасное имя файла только из латиницы и цифр.
    Пример: '1309х80х10' → '1309h80h10'
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
    return ''.join(c if c.isalnum() else '_' for c in result)


def read_video_urls(filepath: str) -> dict[str, str]:
    """Читает Excel, возвращает {артикул: url_видео}."""
    try:
        df = pd.read_excel(filepath, header=0)
    except Exception as e:
        raise CommandError(f'Не удалось открыть {filepath}: {e}')

    df = df[df['Артикул'].notna()].copy()

    result = {}
    for _, row in df.iterrows():
        article = clean(row['Артикул'])
        url     = clean(row.get('Видео', ''))
        if article and url:
            result[article] = url
    return result


def download_video(url: str, save_path: str) -> bool:
    """
    Скачивает HLS-видео (.m3u8) через yt-dlp.
    save_path — путь БЕЗ расширения, yt-dlp добавит .mp4 сам.
    """
    ydl_opts = {
        'outtmpl':             save_path + '.%(ext)s',
        'format':              'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'quiet':               True,
        'no_warnings':         True,
        'http_headers': {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
            ),
            'Referer': 'https://www.wildberries.ru/',
        },
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return True
    except Exception:
        return False


def convert_to_h264(input_path: str) -> bool:
    """
    Перекодирует видео из H.265 в H.264 через ffmpeg.

    Почему нужно:
    - WB хранит видео в H.265 (HEVC) — современный кодек, хорошее сжатие
    - Но браузеры H.265 почти не поддерживают (только Safari на Mac/iOS)
    - H.264 поддерживают все браузеры без исключений

    Параметры ffmpeg:
    - libx264: кодек H.264
    - aac: аудио кодек (совместимый с браузерами)
    - crf 23: качество (0=лучше/тяжелее, 51=хуже/легче, 23=хороший баланс)
    - preset fast: скорость кодирования vs размер файла
    - movflags +faststart: метаданные в начало файла для быстрого старта в браузере
    """
    tmp_path = input_path.replace('.mp4', '_tmp.mp4')

    result = subprocess.run(
        [
            r'C:\ffmpeg\bin\ffmpeg.exe',
            '-i', input_path,           # входной файл
            '-vcodec', 'libx264',       # видео → H.264
            '-acodec', 'aac',           # аудио → AAC
            '-crf', '23',               # качество
            '-preset', 'fast',          # скорость
            '-movflags', '+faststart',  # для быстрого старта в браузере
            '-y',                       # перезаписать без вопросов
            tmp_path,
        ],
        capture_output=True,  # скрываем вывод ffmpeg
    )

    if result.returncode == 0:
        # Заменяем оригинал перекодированным файлом
        os.replace(tmp_path, input_path)
        return True
    else:
        # Удаляем битый временный файл если он создался
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# COMMAND
# ═══════════════════════════════════════════════════════════════════════════════

class Command(BaseCommand):
    help = 'Скачивает видео с WB, перекодирует в H.264 и привязывает к товарам'

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
            help='Обработать все категории',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать что будет скачано без реального скачивания',
        )

    def handle(self, *args, **options):
        if options['all']:
            category_ids = list(CATEGORY_FILES.keys())
        else:
            category_ids = [options['category_id']]

        total_ok = total_errors = total_skip = 0

        for category_id in category_ids:
            self.stdout.write(
                self.style.HTTP_INFO(f'\n─── Категория {category_id} ───')
            )
            ok, errors, skip = self._process_category(category_id, options)
            total_ok     += ok
            total_errors += errors
            total_skip   += skip

        self.stdout.write(
            self.style.SUCCESS(
                f'\nВсего: скачано {total_ok}, '
                f'ошибок {total_errors}, '
                f'пропущено (уже есть) {total_skip}'
            )
        )

    def _process_category(self, category_id: int, options: dict) -> tuple[int, int, int]:
        dry_run = options['dry_run']

        filepath = os.path.join(WB_EXPORT_DIR, CATEGORY_FILES[category_id])
        if not os.path.exists(filepath):
            self.stdout.write(self.style.ERROR(f'Файл не найден: {filepath}'))
            return 0, 0, 0

        video_urls = read_video_urls(filepath)
        self.stdout.write(f'Видео в файле: {len(video_urls)}')

        if not video_urls:
            self.stdout.write('Нет видео в этой категории.')
            return 0, 0, 0

        if dry_run:
            self.stdout.write(self.style.WARNING('--- DRY-RUN ---'))
            for article, url in list(video_urls.items())[:5]:
                safe = make_safe_filename(article)
                self.stdout.write(f'  {article:25s} → {safe}.mp4')
            if len(video_urls) > 5:
                self.stdout.write(f'  ... ещё {len(video_urls) - 5}')
            return 0, 0, 0

        video_dir = os.path.join(settings.MEDIA_ROOT, 'products', 'videos')
        os.makedirs(video_dir, exist_ok=True)

        ok = errors = skip = 0

        for i, (article, url) in enumerate(video_urls.items(), start=1):
            self.stdout.write(
                f'[{i}/{len(video_urls)}] {article}',
                ending='\r'
            )
            self.stdout.flush()

            try:
                product = Product.objects.get(article=article)
            except Product.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'\n  Товар не найден в БД: {article}')
                )
                errors += 1
                continue

            if product.images.filter(media_type='video').exists():
                skip += 1
                continue

            safe_name = make_safe_filename(article)
            save_path = os.path.join(video_dir, safe_name)

            # Шаг 1: скачиваем
            self.stdout.write(f'[{i}/{len(video_urls)}] скачиваю:    {article}', ending='\r')
            self.stdout.flush()
            success = download_video(url, save_path)

            if not success:
                self.stdout.write(self.style.ERROR(f'\n  Ошибка скачивания: {article}'))
                errors += 1
                continue

            # Шаг 2: перекодируем H.265 → H.264
            mp4_path = save_path + '.mp4'
            self.stdout.write(f'[{i}/{len(video_urls)}] перекодирую: {article}', ending='\r')
            self.stdout.flush()
            converted = convert_to_h264(mp4_path)

            if not converted:
                self.stdout.write(
                    self.style.WARNING(f'\n  Ошибка перекодирования: {article} — сохранён оригинал')
                )
                # Не фатально — сохраняем как есть, может браузер всё же воспроизведёт

            # Шаг 3: привязываем к товару
            relative_path = os.path.relpath(mp4_path, settings.MEDIA_ROOT)
            ProductImage.objects.create(
                product    = product,
                video      = relative_path,
                media_type = 'video',
                order      = 999,
            )
            ok += 1

        self.stdout.write('')
        self.stdout.write(
            f'Категория {category_id}: '
            f'скачано {ok}, ошибок {errors}, пропущено {skip}'
        )
        return ok, errors, skip