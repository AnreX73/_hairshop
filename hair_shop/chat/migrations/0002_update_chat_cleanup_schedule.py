from django.db import migrations

OLD_FUNC = "notifications.tasks.cleanup_old_chat_sessions"
NEW_FUNC = "chat.tasks.cleanup_old_conversations"
OLD_NAME = "cleanup_old_chat_sessions"
NEW_NAME = "cleanup_old_chat_conversations"


def forwards(apps, schema_editor):
    """Переводит существующую задачу планировщика на новую модель чата."""
    Schedule = apps.get_model("django_q", "Schedule")
    Schedule.objects.filter(func=OLD_FUNC).update(func=NEW_FUNC, name=NEW_NAME)


def backwards(apps, schema_editor):
    Schedule = apps.get_model("django_q", "Schedule")
    Schedule.objects.filter(func=NEW_FUNC).update(func=OLD_FUNC, name=OLD_NAME)


class Migration(migrations.Migration):
    dependencies = [
        ("chat", "0001_initial"),
        (
            "django_q",
            "0019_alter_task_options_alter_ormq_key_alter_ormq_lock_and_more",
        ),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
