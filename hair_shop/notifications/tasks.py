import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import Max, Q

# Замените на актуальный путь к вашим моделям
from .models import ChatSession 

logger = logging.getLogger(__name__)

def cleanup_old_chat_sessions():
    """
    Удаляет сессии чата, в которых последнее сообщение было отправлено 
    более 30 дней назад, либо сессии без единого сообщения.
    """
    logger.info("Запуск задачи очистки старых чат-сессий...")
    
    # Считаем пороговую дату (30 дней назад)
    # Если нужен строго календарный месяц, используйте dateutil.relativedelta(months=1)
    threshold_date = timezone.now() - timedelta(days=30)

    # Находим сессии для удаления
    # Аннотируем каждую сессию датой её последнего сообщения
    sessions_to_delete = ChatSession.objects.annotate(
        last_msg_date=Max('messages__created_at')
    ).filter(
        # Либо последнее сообщение было раньше пороговой даты
        Q(last_msg_date__lt=threshold_date) | 
        # Либо сообщений в сессии вообще нет (last_msg_date будет None)
        Q(last_msg_date__isnull=True) 
    )

    count = sessions_to_delete.count()

    if count > 0:
        # Удаляем сессии. 
        # Благодаря on_delete=models.CASCADE у ChatMessage, сообщения удалятся автоматически.
        sessions_to_delete.delete()
        logger.info(f"Успешно удалено {count} старых чат-сессий.")
    else:
        logger.info("Старых чат-сессий для удаления не найдено.")

    return f"Очистка завершена. Удалено сессий: {count}"

