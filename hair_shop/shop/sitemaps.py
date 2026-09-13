from django.contrib.sitemaps import Sitemap
from django.db.models import Q
from django.urls import reverse

from .models import Category, Product


class ProductSitemap(Sitemap):
    """Карточки товаров. В карту попадают только реально видимые товары."""

    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return (
            Product.objects.filter(
                Q(stock__gt=0) | Q(out_of_stock_behavior="show")
            )
            .order_by("-popularity")
        )

    def lastmod(self, obj):
        return obj.updated_at


class CategorySitemap(Sitemap):
    """Категории — посадочные страницы вида /catalog/<slug>/ .

    Category.get_absolute_url() уже возвращает этот URL,
    а маршрут shop:category добавлен в shop/urls.py.
    """

    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Category.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at


class StaticViewSitemap(Sitemap):
    """Основные статические страницы сайта."""

    changefreq = "daily"
    priority = 1.0

    def items(self):
        return ["shop:index", "shop:catalog", "shop:info_page"]

    def location(self, item):
        return reverse(item)
