from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from shop.models import Product, Category, Favorite
from users.models import User  # или Favorite
# Допустим, у вас есть заказы
# from orders.models import Order 

# from django.contrib.auth.mixins import LoginRequiredMixin
# from django.views.generic.edit import CreateView, UpdateView
# from django.shortcuts import get_object_or_404
# from django.urls import reverse_lazy
# from shop.models import Product
# from .forms import ProductForm
# from django.utils.text import slugify


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





# class ProductCreateView(LoginRequiredMixin, CreateView):
#     model = Product
#     form_class = ProductForm
#     template_name = 'dashboard/products/product_form.html'

#     def get_parent(self):
#         parent_id = self.request.GET.get('parent')
#         if parent_id:
#             return get_object_or_404(Product, pk=parent_id, parent__isnull=True)
#         return None

#     def get_form_kwargs(self):
#         kwargs = super().get_form_kwargs()
#         kwargs['parent'] = self.get_parent()
#         return kwargs

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['parent'] = self.get_parent()  # для шаблона
#         return context

#     def form_valid(self, form):
#         product = form.save(commit=False)
#         # Генерируем slug из названия серии
#         source_name = product.name or (product.parent.name if product.parent else '')
#         product.slug = slugify(source_name)
#         product.save()
#         form.save_m2m()  # для ManyToMany (category)
#         return super().form_valid(form)

#     def get_success_url(self):
#         return reverse_lazy('product_detail', kwargs={'pk': self.object.pk})


# class ProductUpdateView(LoginRequiredMixin, UpdateView):
#     model = Product
#     form_class = ProductForm
#     template_name = 'dashboard/products/product_form.html'

#     def get_form_kwargs(self):
#         kwargs = super().get_form_kwargs()
#         kwargs['parent'] = self.object.parent  # при редактировании берём из объекта
#         return kwargs

#     def get_success_url(self):
#         return reverse_lazy('product_detail', kwargs={'pk': self.object.pk})