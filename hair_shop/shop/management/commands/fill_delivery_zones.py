from django.core.management.base import BaseCommand
from django.db import transaction
# Замените 'your_app' на название вашего приложения, где лежат модели
from shop.models import DeliveryZone, Region 


class Command(BaseCommand):
    help = 'Заполняет базу данных зонами доставки и регионами с кодами'

    def handle(self, *args, **kwargs):
        # ВАЖНО: Укажите актуальные цены и пороги бесплатной доставки!
        # Сейчас они стоят как 0 (или заглушки).
        zones_data = [
            {
                "name": "Зона 1 (Локальная)",
                "price": 300, 
                "free_delivery_threshold": 3000,
                "regions": [
                    {"name": "Алтайский край", "code": "22"},
                    {"name": "Кемеровская область — Кузбасс", "code": "42"},
                    {"name": "Новосибирская область", "code": "54"},
                    {"name": "Омская область", "code": "55"},
                    {"name": "Республика Алтай", "code": "04"},
                    {"name": "Томская область", "code": "70"},
                ]
            },
            {
                "name": "Зона 2 (Урал и Западная Сибирь)",
                "price": 500,
                "free_delivery_threshold": 5000,
                "regions": [
                    {"name": "Курганская область", "code": "45"},
                    {"name": "Оренбургская область", "code": "56"},
                    {"name": "Пермский край", "code": "59"},
                    {"name": "Республика Башкортостан", "code": "02"},
                    {"name": "Свердловская область", "code": "66"},
                    {"name": "Тюменская область", "code": "72"},
                    {"name": "Ханты-Мансийский автономный округ — Югра", "code": "86"},
                    {"name": "Челябинская область", "code": "74"},
                    {"name": "Ямало-Ненецкий автономный округ", "code": "89"},
                ]
            },
            {
                "name": "Зона 3 (Центр, Поволжье, Северо-Запад)",
                "price": 700,
                "free_delivery_threshold": 7000,
                "regions": [
                    {"name": "Москва", "code": "77"},
                    {"name": "Московская область", "code": "50"},
                    {"name": "Санкт-Петербург", "code": "78"},
                    {"name": "Ленинградская область", "code": "47"},
                    {"name": "Нижегородская область", "code": "52"},
                    {"name": "Самарская область", "code": "63"},
                    {"name": "Саратовская область", "code": "64"},
                    {"name": "Воронежская область", "code": "36"},
                    {"name": "Ярославская область", "code": "76"},
                    {"name": "Тульская область", "code": "71"},
                    {"name": "Республика Татарстан", "code": "16"},
                    {"name": "Вологодская область", "code": "35"},
                    {"name": "Архангельская область", "code": "29"},
                    {"name": "Калининградская область", "code": "39"},
                ]
            },
            {
                "name": "Зона 4 (Ближний Восток и Юг РФ)",
                "price": 900,
                "free_delivery_threshold": 10000,
                "regions": [
                    {"name": "Астраханская область", "code": "30"},
                    {"name": "Волгоградская область", "code": "34"},
                    {"name": "Забайкальский край", "code": "75"},
                    {"name": "Иркутская область", "code": "38"},
                    {"name": "Краснодарский край", "code": "23"},
                    {"name": "Красноярский край", "code": "24"},
                    {"name": "Республика Бурятия", "code": "03"},
                    {"name": "Республика Дагестан", "code": "05"},
                    {"name": "Чеченская Республика", "code": "20"},
                    {"name": "Республика Ингушетия", "code": "06"},
                    {"name": "Кабардино-Балкарская Республика", "code": "07"},
                    {"name": "Карачаево-Черкесская Республика", "code": "09"},
                    {"name": "Республика Северная Осетия — Алания", "code": "15"},
                    {"name": "Республика Калмыкия", "code": "08"},
                    {"name": "Ростовская область", "code": "61"},
                    {"name": "Ставропольский край", "code": "26"},
                ]
            },
            {
                "name": "Зона 5 (Дальний Восток и Авиа-доставка)",
                "price": 1500,
                "free_delivery_threshold": 15000,
                "regions": [
                    {"name": "Амурская область", "code": "28"},
                    {"name": "Еврейская автономная область", "code": "79"},
                    {"name": "Камчатский край", "code": "41"},
                    {"name": "Магаданская область", "code": "49"},
                    {"name": "Приморский край", "code": "25"},
                    {"name": "Республика Саха (Якутия)", "code": "14"},
                    {"name": "Республика Тыва", "code": "17"},
                    {"name": "Республика Хакасия", "code": "19"},
                    {"name": "Сахалинская область", "code": "65"},
                    {"name": "Хабаровский край", "code": "27"},
                    {"name": "Чукотский автономный округ", "code": "87"},
                    # Норильск и Таймыр административно входят в Красноярский край (24), 
                    # но для логистики их часто выделяют отдельно. Оставляем код 24.
                    {"name": "г. Норильск", "code": "24"},
                    {"name": "Таймырский Долгано-Ненецкий район", "code": "24"},
                ]
            },
        ]

        self.stdout.write("Начинаю заполнение зон доставки и регионов...")

        # Используем транзакцию, чтобы при ошибке не было частично заполненной БД
        with transaction.atomic():
            for zone_data in zones_data:
                regions_list = zone_data.pop('regions')
                
                # Создаем или обновляем зону доставки
                zone, zone_created = DeliveryZone.objects.update_or_create(
                    name=zone_data['name'],
                    defaults={
                        'price': zone_data['price'],
                        'free_delivery_threshold': zone_data['free_delivery_threshold']
                    }
                )
                
                action = "Создана" if zone_created else "Обновлена"
                self.stdout.write(f"  {action} зона: {zone.name}")

                # Создаем или обновляем регионы внутри зоны
                for region_data in regions_list:
                    region, region_created = Region.objects.update_or_create(
                        name=region_data['name'],
                        defaults={
                            'zone': zone,
                            'region_code': region_data['code']
                        }
                    )
                    
                    if region_created:
                        self.stdout.write(f"    + Добавлен регион: {region.name} (код {region.region_code})")
                    else:
                        self.stdout.write(f"    ~ Обновлен регион: {region.name}")

        self.stdout.write(self.style.SUCCESS("База данных успешно заполнена!"))