from django.urls import path

from shop.views import catalog, index, product_page, toggle_favorite, toggle_cart, remove_from_cart, order_create, update_cart, order_success, review_create, payment_stub, legal_info, review_media, upload_review_media
from shop import views
app_name = 'shop'

urlpatterns = [
    path('', index, name='index'),  
    path('catalog/', catalog, name='catalog'),
    path('catalog/<int:category_id>/', catalog, name='catalog_by_category'),
    path('legal-info/', legal_info, name='legal_info'),
    path('product_page/<slug:slug>/<int:product_id>/', product_page, name='product_page'),
    path('toggle_favorite/<int:product_id>/', toggle_favorite, name='toggle_favorite'),
    path('toggle-cart/<int:product_id>/', toggle_cart, name='toggle_cart'),
    path('remove-from-cart/<int:item_id>/', remove_from_cart, name='remove_from_cart'),
    path('update-cart/<int:item_id>/', update_cart, name='update_cart'),
    path('order-create/', order_create, name='order_create'),
    path('order-success/<int:order_id>/', order_success, name='order_success'),  # новый
    # В urls.py приложения shop добавь:

    path('reviews/<int:product_id>/create/',
        review_create, name='review_create'),
    path('reviews/<int:review_id>/media/',
        review_media, name='review_media'),

        # AJAX endpoints
    path('reviews/<int:review_id>/media/upload/',
        upload_review_media, name='upload_review_media'),
    path('reviews/media/<int:media_id>/delete/',
        views.delete_review_media, name='delete_review_media'),
    path('reviews/media/<int:media_id>/status/',
        views.review_media_status, name='review_media_status'),
    path('reviews/media/<int:media_id>/partial/',
     views.review_media_item_partial, name='review_media_item_partial'),

    # ===== ЗАГЛУШКА ОПЛАТЫ — УДАЛИТЬ ПОСЛЕ ПОДКЛЮЧЕНИЯ ЭКВАЙРИНГА =====
    path('payment-stub/<int:order_id>/', payment_stub, name='payment_stub'),
    # ===== КОНЕЦ ЗАГЛУШКИ =====
]