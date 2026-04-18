from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from shop.models import Product, Category, Favorite
from users.models import User  # или Favorite



class AdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'dashboard/admin_area.html'

    # Проверка, что зашел именно админ/стафф
    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Собираем данные из разных приложений
        context['total_products'] = Product.objects.count()
        context['total_users'] = User.objects.count()
        context['total_favorites'] = Favorite.objects.count()
        context['recent_products'] = Product.objects.order_by('-id')[:5]
        return context



def product_by_group(request, group):
    products = Product.objects.filter(group=group)
    return render(request, 'dashboard/products_by_group.html', {'products': products})

