def make_slug(text: str) -> str:
    CHARS = {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "yo",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "y",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "h",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "sch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
    }
    result = ""
    for ch in text.lower():
        result += CHARS.get(ch, ch)
    slug = "".join(c if c.isalnum() else "-" for c in result)
    slug = "-".join(part for part in slug.split("-") if part)
    return slug[:255] or "product"


def resolve_delivery_zone(region_code=None, region_name=None, city=None):
    """Подбирает зону доставки по данным адреса из DaData.

    Приоритет поиска (от точного к общему):
    1. Точное совпадение названия города с Region.name («Москва»).
    2. Вхождение города в Region.name:
       «Норильск» -> «г. Норильск», «Омск» -> «Омская область».
    3. Точное совпадение названия региона («Красноярский край»).
    4. Вхождение названия региона в Region.name.
    5. Код региона. У Норильска и Таймыра он совпадает с Красноярским краем (24),
       поэтому код используется только как последний вариант.

    Возвращает DeliveryZone или None, если регион не найден.
    """
    # Ленивый импорт: models.py импортирует make_slug из этого модуля.
    from .models import Region

    region_code = (region_code or "").strip()
    region_name = (region_name or "").strip()
    city = (city or "").strip()

    qs = Region.objects.select_related("zone")

    # 1. Точное совпадение по городу
    if city:
        region = qs.filter(name__iexact=city).first()
        if region:
            return region.zone

    # 2. Город входит в название региона или спец-зоны
    #    (город важнее региона: «Норильск» -> «г. Норильск», а не Красноярский край)
    if len(city) >= 4:
        region = qs.filter(name__icontains=city).first()
        if region:
            return region.zone

    # 3. Точное совпадение по названию региона
    if region_name:
        region = qs.filter(name__iexact=region_name).first()
        if region:
            return region.zone

    # 4. Название региона по вхождению
    if len(region_name) >= 4:
        region = qs.filter(name__icontains=region_name).first()
        if region:
            return region.zone

    # 5. Код региона (при дублях — самая дешёвая зона)
    if region_code:
        region = qs.filter(region_code=region_code).order_by("zone__price").first()
        if region:
            return region.zone

    return None


def calc_delivery_cost(zone, subtotal):
    """Стоимость доставки по зоне с учётом порога бесплатной доставки.

    Если зона не определена, возвращает None — стоимость уточнит менеджер.
    """
    if zone is None:
        return None
    if zone.free_delivery_threshold and subtotal >= zone.free_delivery_threshold:
        return 0
    return zone.price
