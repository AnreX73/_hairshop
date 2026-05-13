from django.db import migrations


def convert(apps, schema_editor):
    Product = apps.get_model("shop", "Product")
    for p in Product.objects.all():
        val = str(p.hair_length).strip() if p.hair_length else ""
        p.hair_length_new = int(val) if val.isdigit() else None
        p.save()


class Migration(migrations.Migration):
    dependencies = [("shop", "0045_add_hair_length_new")]

    operations = [
        migrations.RunPython(convert, migrations.RunPython.noop),
    ]
