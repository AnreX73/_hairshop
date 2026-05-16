from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('shop', '0048_product_hair_shade_alter_product_hair_length'),  # замени на актуальную
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE shop_product DROP COLUMN IF EXISTS is_available;",
            reverse_sql="ALTER TABLE shop_product ADD COLUMN is_available boolean;",
        ),
    ]