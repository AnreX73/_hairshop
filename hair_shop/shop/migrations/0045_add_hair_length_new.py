from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("shop", "0044_remove_product_is_hit")]  # твоя последняя

    operations = [
        migrations.AddField(
            model_name="product",
            name="hair_length_new",
            field=models.IntegerField(null=True, blank=True),
        ),
    ]
