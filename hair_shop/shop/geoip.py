"""Определение города посетителя по IP-адресу через DaData.

Модуль намеренно не импортирует модели: он работает только с настройками,
кэшем и внешним API. Все публичные функции не бросают исключений — при любой
ошибке посетитель просто не увидит окно «Ваш город?».
"""

import ipaddress
import logging

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

DADATA_IPLOCATE_URL = (
    "https://suggestions.dadata.ru/suggestions/api/4_1/rs/iplocate/address"
)

CITY_CACHE_KEY = "geoip:city:{}"
EMPTY_CACHE_KEY = "geoip:empty:{}"
RATE_CACHE_KEY = "geoip:rate:{}"


def normalize_public_ip(value):
    """Возвращает строку с публичным IP или None.

    Приватные, loopback и служебные адреса отбрасываем: DaData по ним ничего
    осмысленного не вернёт, а в разработке они сэкономят запросы.
    """
    try:
        parsed = ipaddress.ip_address((value or "").strip())
    except ValueError:
        return None

    if parsed.version == 6 and parsed.ipv4_mapped:
        parsed = parsed.ipv4_mapped

    if not parsed.is_global:
        return None

    return str(parsed)


def get_client_ip(request):
    """IP посетителя с учётом nginx.

    Приоритет: X-Real-IP (nginx перезаписывает его значением $remote_addr,
    поэтому подделать нельзя), затем первый адрес X-Forwarded-For,
    затем REMOTE_ADDR.
    """
    candidates = (
        request.META.get("HTTP_X_REAL_IP"),
        (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0],
        request.META.get("REMOTE_ADDR"),
    )
    for candidate in candidates:
        ip = normalize_public_ip(candidate)
        if ip:
            return ip
    return None


def allow_geo_request(ip):
    """Простое ограничение частоты, чтобы не выжечь лимит DaData."""
    if not ip:
        return False

    limit = getattr(settings, "GEOIP_RATE_LIMIT", 10)
    window = getattr(settings, "GEOIP_RATE_WINDOW", 60)

    try:
        if cache.add(RATE_CACHE_KEY.format(ip), 1, window):
            return True
        return cache.incr(RATE_CACHE_KEY.format(ip)) <= limit
    except Exception:  # noqa: BLE001 — Redis может быть недоступен
        logger.warning("GeoIP rate limit unavailable, allowing request")
        return True


def detect_city_by_ip(ip):
    """Возвращает город по IP или None.

    Успешный результат кэшируется на GEOIP_CACHE_SECONDS (по умолчанию 30 дней),
    пустой — на GEOIP_EMPTY_CACHE_SECONDS (сутки), чтобы не дёргать API лишний раз.
    """
    if not ip:
        return None

    city_key = CITY_CACHE_KEY.format(ip)
    empty_key = EMPTY_CACHE_KEY.format(ip)

    cached = _cache_get(city_key)
    if cached is not None:
        return cached

    if _cache_get(empty_key):
        return None

    city = _fetch_city(ip)

    if city is None:
        _cache_set(
            empty_key,
            True,
            getattr(settings, "GEOIP_EMPTY_CACHE_SECONDS", 60 * 60 * 24),
        )
        return None

    _cache_set(
        city_key,
        city,
        getattr(settings, "GEOIP_CACHE_SECONDS", 60 * 60 * 24 * 30),
    )
    return city


def normalize_location(payload):
    """Достаёт из ответа DaData только то, что нужно магазину."""
    location = (payload or {}).get("location") or {}
    data = location.get("data") or {}

    city = (data.get("city") or data.get("settlement") or "").strip()
    if not city:
        return None

    region_code = (data.get("region_kladr_id") or "")[:2]

    return {
        "city": city,
        "region": (data.get("region") or "").strip(),
        "region_code": region_code,
        "postal_code": (data.get("postal_code") or "").strip(),
    }


def _fetch_city(ip):
    api_key = getattr(settings, "DADATA_API_KEY", "")
    if not api_key:
        return None

    try:
        response = requests.post(
            DADATA_IPLOCATE_URL,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Token {api_key}",
            },
            json={"ip": ip},
            timeout=getattr(settings, "GEOIP_TIMEOUT", 3),
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("DaData iplocate failed for %s: %s", ip, exc)
        return None

    return normalize_location(payload)


def _cache_get(key):
    try:
        return cache.get(key)
    except Exception:  # noqa: BLE001 — Redis может быть недоступен
        logger.warning("GeoIP cache is unavailable")
        return None


def _cache_set(key, value, timeout):
    try:
        cache.set(key, value, timeout)
    except Exception:  # noqa: BLE001
        logger.warning("GeoIP cache is unavailable")
