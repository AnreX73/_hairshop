from django.shortcuts import render, redirect
from django.db.models import Prefetch
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import UpdateView
from django.shortcuts import get_object_or_404
from .forms import RegisterUserForm, LoginUserForm, UserPasswordResetForm, UserPasswordResetConfirmForm, ChangeUserInfoForm
from django.contrib.auth.views import LoginView, PasswordResetView, PasswordResetConfirmView
from django.urls import reverse_lazy
from shop.models import Product, CartItem, Order, Review, ProductImage
from .models import User







class RegisterUser(View):
    template_name = "users/register.html"

    def get(self, request):
        context = {
            "form": RegisterUserForm(),
            "title": "регистрация",
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = RegisterUserForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            email = form.cleaned_data.get("email")
            password = form.cleaned_data.get("password1")
            user = authenticate(request, username=email, password=password)
            login(request, user, backend="users.authentication.EmailAuthBackend")
            return redirect("users:profile")
        context = {
            "form": form,
        }
        return render(request, self.template_name, context)


class UpdateUserInfo(LoginRequiredMixin, UpdateView):
    model = User
    template_name = "users/update_user_info.html"
    form_class = ChangeUserInfoForm
    success_url = reverse_lazy("users:profile")
    success_message = "Данные пользователя изменены"

    def setup(self, request, *args, **kwargs):
        self.user_id = request.user.pk
        return super().setup(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["checkout"] = False  # или логика определения контекста
        return kwargs

    def get_object(self, queryset=None):
        if not queryset:
            queryset = self.get_queryset()
        return get_object_or_404(queryset, pk=self.user_id)


class LoginUser(LoginView):
    template_name = "users/login.html"
    form_class = LoginUserForm
    extra_context = {"title": "Login"}


@login_required(login_url="/register/")
def profile(request):
    user = request.user
    favorites = Product.objects.filter(favorited_by__user=user).order_by('-favorited_by__created_at')
    try:
        cart = user.cart
    # для отображения товаров в корзине — как было
        user_cart_products = cart.items.select_related('product').prefetch_related(
            Prefetch(
                'product__images',
                queryset=ProductImage.objects.filter(media_type='image').order_by('order'),
                to_attr='prefetched_images'
         )
        ).order_by('-added_at')
    # считаем из того же queryset — без доп. запросов
        user_cart_total = sum(item.total_price for item in user_cart_products)
        total_items = sum(item.quantity for item in user_cart_products)
    except Cart.DoesNotExist:
        user_cart_products = []
        user_cart_total = 0
        total_items = 0

    # История заказов с товарами за один запрос
    orders = (
    Order.objects.filter(
        user=user,
        
    )
    .prefetch_related(
        Prefetch(
            'items__product__images',
            queryset=ProductImage.objects.filter(media_type='image').order_by('order'),
            to_attr='prefetched_images'  # именно это использует main_image property
        )
    )
    .order_by('-created_at')
)   
# id товаров, на которые пользователь уже оставил отзыв
    reviewed_product_ids = set(
        Review.objects.filter(user=user).values_list('product_id', flat=True)
    )
    user_favorite_ids = list(favorites.values_list('id', flat=True))
    active_tab = request.GET.get('tab', 1)
    # Делаем так:
    try:
        cart = user.cart
        cart_items = cart.items.select_related('product').all()
        user_cart_total = sum(item.total_price for item in cart_items)
        total_items = sum(item.quantity for item in cart_items)
    except Cart.DoesNotExist:
        cart_items = []
        user_cart_total = 0
        total_items = 0
    context = {
        "user": user,
        "title": "Profile",
        "favorites": favorites,
        "user_cart_products":user_cart_products,
        "user_favorite_ids": user_favorite_ids,
        "active_tab": active_tab,
        "user_cart_total": user_cart_total,
        "total_items": total_items,
        "orders": orders,
        "reviewed_product_ids": reviewed_product_ids,
    }
    # Render the profile page
    return render(request, 'users/profile.html', context=context)


    

class UserPasswordResetView(PasswordResetView):
    template_name = "users/user_password_reset_form.html"
    success_url = reverse_lazy("password_reset_done")
    form_class = UserPasswordResetForm


class UserPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "users/user_password_reset_confirm.html"
    success_url = reverse_lazy("password_reset_complete")
    form_class = UserPasswordResetConfirmForm






