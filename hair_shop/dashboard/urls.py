from django.urls import path
from dashboard import views
from dashboard.views import AdminDashboardView

app_name = 'dashboard'  # Это пространство имен (namespace)

urlpatterns = [
    # Главная страница админки: /admin-panel/
    path('admin_area/', AdminDashboardView.as_view(), name='admin_area'),
    path('orders/', views.manage_orders, name='manage_orders'),
    path('orders/<int:order_id>/assign/', views.order_assign, name='order_assign'),
    path('orders/<int:order_id>/processing/', views.order_set_processing, name='order_processing'),
    path('orders/<int:order_id>/ship/', views.order_ship, name='order_ship'),
    path('orders/<int:order_id>/deliver/', views.order_deliver, name='order_deliver'),
    path('orders/<int:order_id>/cancel/', views.order_cancel, name='order_cancel'),
    path('orders/<int:order_id>/payment-webhook/', views.order_payment_webhook, name='order_payment_webhook'),
    path('orders/items/<int:item_id>/toggle/', views.order_item_toggle, name='order_item_toggle'),
    path('orders/set-manager/', views.set_active_manager, name='set_active_manager'),
]
