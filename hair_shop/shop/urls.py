from django.urls import path

from shop.views import catalog, index, product_page, toggle_favorite, toggle_cart, remove_from_cart

app_name = 'shop'

urlpatterns = [
    path('', index, name='index'),  
    path('catalog/', catalog, name='catalog'),
    path('product_page/<slug:slug>/<int:product_id>/', product_page, name='product_page'),
    path('toggle_favorite/<int:product_id>/', toggle_favorite, name='toggle_favorite'),
    path('toggle-cart/<int:product_id>/', toggle_cart, name='toggle_cart'),
    path('remove-from-cart/<int:product_id>/', remove_from_cart, name='remove_from_cart'),
]