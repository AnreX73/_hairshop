from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("shop", "0060_alter_product_article"),
    ]

    operations = [
        migrations.RunSQL(
            "CREATE EXTENSION IF NOT EXISTS pg_trgm;",
        ),
    ]
