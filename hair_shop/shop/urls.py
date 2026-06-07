from django.contrib.sitemaps.views import sitemap
from django.urls import path

from shop import views
from shop.sitemaps import CategorySitemap, ProductSitemap
from shop.views import (
    add_admin_reply,
    catalog,
    index,
    info_page,
    order_create,
    order_success,
    payment_stub,
    product_page,
    remove_from_cart,
    review_create,
    review_media,
    review_popup,
    toggle_cart,
    toggle_favorite,
    update_cart,
    upload_review_media,
)

sitemaps = {
    "products": ProductSitemap,
    "categories": CategorySitemap,
}

app_name = "shop"

urlpatterns = [
    path("", index, name="index"),
    path("catalog/", catalog, name="catalog"),
    path(
        "product_page/<slug:slug>/<int:product_id>/", product_page, name="product_page"
    ),
    path("toggle_favorite/<int:product_id>/", toggle_favorite, name="toggle_favorite"),
    path("toggle-cart/<int:product_id>/", toggle_cart, name="toggle_cart"),
    path("remove-from-cart/<int:item_id>/", remove_from_cart, name="remove_from_cart"),
    path("update-cart/<int:item_id>/", update_cart, name="update_cart"),
    path("order-create/", order_create, name="order_create"),
    path("order-success/<int:order_id>/", order_success, name="order_success"),
    path("info/", info_page, name="info_page"),
    path("reviews/<int:product_id>/create/", review_create, name="review_create"),
    path("reviews/<int:review_id>/media/", review_media, name="review_media"),
    # AJAX endpoints
    path(
        "reviews/<int:review_id>/media/upload/",
        upload_review_media,
        name="upload_review_media",
    ),
    path(
        "reviews/media/<int:media_id>/delete/",
        views.delete_review_media,
        name="delete_review_media",
    ),
    path(
        "reviews/media/<int:media_id>/status/",
        views.review_media_status,
        name="review_media_status",
    ),
    path(
        "reviews/media/<int:media_id>/partial/",
        views.review_media_item_partial,
        name="review_media_item_partial",
    ),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("review/<int:review_id>/popup/", review_popup, name="review_popup"),
    path("review/<int:review_id>/reply/", add_admin_reply, name="review_add_reply"),
    # ===== ЗАГЛУШКА ОПЛАТЫ — УДАЛИТЬ ПОСЛЕ ПОДКЛЮЧЕНИЯ ЭКВАЙРИНГА =====
    path("payment-stub/<int:order_id>/", payment_stub, name="payment_stub"),
    # ===== КОНЕЦ ЗАГЛУШКИ =====
]
