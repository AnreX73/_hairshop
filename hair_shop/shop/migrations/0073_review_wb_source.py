from django.db import migrations

WB_USERNAME = "wb_reviews@test.ru"


def mark_wb_reviews(apps, schema_editor):
    """Отзывы, импортированные с Wildberries, помечаем отдельным источником."""
    Review = apps.get_model("shop", "Review")
    Review.objects.filter(user__username=WB_USERNAME).update(source="wb")


class Migration(migrations.Migration):
    dependencies = [
        ("shop", "0072_review_source"),
    ]

    operations = [
        migrations.RunPython(mark_wb_reviews, migrations.RunPython.noop),
    ]
