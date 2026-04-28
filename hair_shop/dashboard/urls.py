from django.urls import path
from dashboard.views import AdminDashboardView, manage_orders

app_name = 'dashboard'  # Это пространство имен (namespace)

urlpatterns = [
    # Главная страница админки: /admin-panel/
    path('admin_area/', AdminDashboardView.as_view(), name='admin_area'),
    path('manage_orders/', manage_orders, name='manage_orders'),
    
    # Сюда потом добавите другие страницы, например:
    # path('products/', ProductListView.as_view(), name='product_list'),
    # path('product/create/', ProductCreateView.as_view(), name='product_create'),
    # Вариант: /product/create/?parent=42
    # path('product/<int:pk>/edit/', ProductUpdateView.as_view(), name='product_edit'),
    # path('product_page/<slug:slug>/<int:pk>/', ProductDetailView.as_view(), name='product_detail'),
]
