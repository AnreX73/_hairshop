FROM python:3.11-slim

# Запрещаем Python писать .pyc файлы и включаем вывод логов без задержек
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Устанавливаем системные зависимости для psycopg2 (PostgreSQL)
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Сначала копируем зависимости (это ускоряет пересборку, если код меняется, а библиотеки нет)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Добавьте gunicorn в requirements.txt, если его там нет
RUN pip install gunicorn

# Копируем весь проект
COPY . .

# Собираем статику сразу при сборке образа (необязательно, но полезно)
# RUN python manage.py collectstatic --no-input

EXPOSE 8000

# Используем gunicorn для запуска (на VPS это стандарт)
# Если всё же хотите runserver, замените gunicorn на python manage.py runserver...
CMD ["sh", "-c", "python manage.py migrate && python manage.py collectstatic --no-input && gunicorn --workers 9 --bind 0.0.0.0:8000 hair_shop.wsgi:application"]

