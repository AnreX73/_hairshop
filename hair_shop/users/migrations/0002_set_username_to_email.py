# users/migrations/0002_set_username_to_email.py
from django.db import migrations

def set_username_to_email(apps, schema_editor):
    User = apps.get_model("users", "User")
    for user in User.objects.all():
        if user.email and user.username != user.email:
            user.username = user.email[:150]
            user.save()

class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(set_username_to_email, migrations.RunPython.noop),
    ]