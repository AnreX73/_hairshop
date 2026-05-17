from django.urls import path
from dashboard import views
from dashboard.views import (
    AdminDashboardView,
    ProductCreateView,
    ProductEditView,
    ProductMediaView,
    upload_product_media,
    reorder_product_media,
    delete_product_media,
    media_status,
    media_item_partial,
)

app_name = "dashboard"  # Это пространство имен (namespace)

urlpatterns = [
    # Главная страница админки: /admin-panel/
    path("admin_area/", AdminDashboardView.as_view(), name="admin_area"),
    path("orders/", views.manage_orders, name="manage_orders"),
    path("orders/<int:order_id>/assign/", views.order_assign, name="order_assign"),
    path(
        "orders/<int:order_id>/processing/",
        views.order_set_processing,
        name="order_processing",
    ),
    path("orders/<int:order_id>/ship/", views.order_ship, name="order_ship"),
    path("orders/<int:order_id>/deliver/", views.order_deliver, name="order_deliver"),
    path("orders/<int:order_id>/cancel/", views.order_cancel, name="order_cancel"),
    path(
        "orders/<int:order_id>/payment-webhook/",
        views.order_payment_webhook,
        name="order_payment_webhook",
    ),
    path(
        "orders/items/<int:item_id>/toggle/",
        views.order_item_toggle,
        name="order_item_toggle",
    ),
    path("orders/set-manager/", views.set_active_manager, name="set_active_manager"),
    # ── Товары ──
    path("products/add/", ProductCreateView.as_view(), name="product_create"),
    path("products/<int:pk>/edit/", ProductEditView.as_view(), name="product_edit"),
    path("products/<int:pk>/media/", ProductMediaView.as_view(), name="product_media"),
    # ── AJAX endpoints ──
    path(
        "products/<int:pk>/media/upload/",
        upload_product_media,
        name="upload_product_media",
    ),
    path(
        "products/<int:pk>/media/reorder/",
        reorder_product_media,
        name="reorder_product_media",
    ),
    path(
        "media/<int:media_id>/delete/",
        delete_product_media,
        name="delete_product_media",
    ),
    path("media/<int:media_id>/status/", media_status, name="media_status"),
    path(
        "media/<int:media_id>/partial/", media_item_partial, name="media_item_partial"
    ),
    path("group-editor/", views.group_editor, name="group_editor"),
    path(
        "admin-update-hair-length/",
        views.update_hair_length_view,
        name="update_hair_length",
    ),
    path(
        "update-hair-shade/",
        views.update_hair_shade_view,
        name="update_hair_shade",
    ),
    path("stock-sync/", views.stock_sync, name="stock_sync"),
    path("stock-sync/import/", views.stock_import, name="stock_import"),
    path("stock-sync/export/", views.stock_export, name="stock_export"),
]
