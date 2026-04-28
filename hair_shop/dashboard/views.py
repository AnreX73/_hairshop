from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from shop.models import Product, Category, Favorite, Order
from users.models import User  # или Favorite
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test


class AdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'dashboard/admin_area.html'

    # Проверка, что зашел именно админ/стафф
    def test_func(self):
        return self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Собираем данные из разных приложений
        context['total_products'] = Product.objects.count()
        context['total_users'] = User.objects.count()
        context['total_favorites'] = Favorite.objects.count()
        context['recent_products'] = Product.objects.order_by('-id')[:5]
        return context


@login_required
@user_passes_test(lambda u: u.is_staff)
def manage_orders(request):
    orders = Order.objects.all().select_related('user').prefetch_related('items').order_by('-created_at')
    managers = User.objects.filter(is_staff=True)
    context = {
        'title': 'Управление заказами',
        'orders': orders,
        'managers': managers,
    }
    return render(request, 'dashboard/manage_orders.html', context)

