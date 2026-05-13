from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("shop", "0046_convert_hair_length")]

    operations = [
        migrations.RemoveField(model_name="product", name="hair_length"),
        migrations.RenameField(
            model_name="product",
            old_name="hair_length_new",
            new_name="hair_length",
        ),
    ]
