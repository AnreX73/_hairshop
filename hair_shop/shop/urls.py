from django.urls import path

from shop.views import catalog, index, product_page, toggle_favorite, toggle_cart, remove_from_cart, order_create, update_cart, order_success, review_create, payment_stub

app_name = 'shop'

urlpatterns = [
    path('', index, name='index'),  
    path('catalog/', catalog, name='catalog'),
    path('product_page/<slug:slug>/<int:product_id>/', product_page, name='product_page'),
    path('toggle_favorite/<int:product_id>/', toggle_favorite, name='toggle_favorite'),
    path('toggle-cart/<int:product_id>/', toggle_cart, name='toggle_cart'),
    path('remove-from-cart/<int:item_id>/', remove_from_cart, name='remove_from_cart'),
    path('update-cart/<int:item_id>/', update_cart, name='update_cart'),
    path('order-create/', order_create, name='order_create'),
    path('order-success/<int:order_id>/', order_success, name='order_success'),  # новый
    path('review-create/<int:product_id>/', review_create, name='review_create'),
    # ===== ЗАГЛУШКА ОПЛАТЫ — УДАЛИТЬ ПОСЛЕ ПОДКЛЮЧЕНИЯ ЭКВАЙРИНГА =====
    path('payment-stub/<int:order_id>/', payment_stub, name='payment_stub'),
    # ===== КОНЕЦ ЗАГЛУШКИ =====
]