from django.urls import path

from dashboard import views
from dashboard.views import (
    AdminDashboardView,
    ProductCloneView,
    ProductCreateView,
    ProductEditView,
    ProductMediaView,
    ProductSearchView,
    admin_chat_view,
    archived_orders,
    delete_product_media,
    media_item_partial,
    media_status,
    order_archive,
    reorder_product_media,
    request_photo,
    # ShadeReviewView,
    upload_product_media,
)

app_name = "dashboard"

urlpatterns = [
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
    path(
        "orders/<int:order_id>/card/",
        views.archive_order_card,
        name="archive_order_card",
    ),
    path("orders/set-manager/", views.set_active_manager, name="set_active_manager"),
    path("orders/<int:order_id>/archive/", order_archive, name="order_archive"),
    path("orders/archived/", archived_orders, name="archived_orders"),
    # ── Товары ──
    path("products/add/", ProductCreateView.as_view(), name="product_create"),
    path("products/<int:pk>/edit/", ProductEditView.as_view(), name="product_edit"),
    path("products/<int:pk>/clone/", ProductCloneView.as_view(), name="product_clone"),
    path("products/search/", ProductSearchView.as_view(), name="product_search"),
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
    path("products/<int:pk>/media/", ProductMediaView.as_view(), name="product_media"),
    # path("products/shade-review/", ShadeReviewView.as_view(), name="shade_review"),
    path(
        "media/<int:media_id>/delete/",
        delete_product_media,
        name="delete_product_media",
    ),
    path("media/<int:media_id>/status/", media_status, name="media_status"),
    path(
        "media/<int:media_id>/partial/", media_item_partial, name="media_item_partial"
    ),
    path("stock-sync/", views.stock_sync, name="stock_sync"),
    path("stock-sync/import/", views.stock_import, name="stock_import"),
    path("stock-sync/export/", views.stock_export, name="stock_export"),
    path("admin-chat/<int:session_id>/", admin_chat_view, name="admin_chat"),
    path(
        "admin-chat/<int:session_id>/request-photo/",
        request_photo,
        name="request_photo",
    ),
    path("chat/", views.chat_list, name="chat_list"),
    path("chat/<int:session_id>/", views.admin_chat, name="admin_chat"),
    path("<int:session_id>/close/", views.close_session, name="chat_close"),
]
