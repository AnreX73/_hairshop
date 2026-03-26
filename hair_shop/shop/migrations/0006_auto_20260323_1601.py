from django.db import migrations

def migrate_prices(apps, schema_editor):
    Product = apps.get_model('shop', 'Product')
    for obj in Product.objects.all():
        # Округляем или просто берем целую часть
        obj.price = int(obj.start_price) 
        obj.save()

class Migration(migrations.Migration):
    dependencies = [('shop', '0005_product_price')]
    operations = [migrations.RunPython(migrate_prices)]
