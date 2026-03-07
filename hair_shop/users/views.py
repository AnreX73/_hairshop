from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.views import View
from .forms import RegisterUserForm, LoginUserForm, UserPasswordResetForm, UserPasswordResetConfirmForm
from django.contrib.auth.views import LoginView, PasswordResetView, PasswordResetConfirmView
from django.urls import reverse_lazy
from shop.models import Product    




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
            form.save()
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password1")
            user = authenticate(username=username, password=password)
            login(request, user)
            return redirect("users:profile")
        context = {
            "form": form,
        }
        return render(request, self.template_name, context)


class LoginUser(LoginView):
    template_name = "users/login.html"
    form_class = LoginUserForm
    extra_context = {"title": "Login"}


@login_required(login_url="/register/")
def profile(request):
    user = request.user
    favorites = Product.objects.filter(favorited_by__user=user).order_by('-favorited_by__created_at')
    user_favorite_ids = list(favorites.values_list('id', flat=True))
    context = {
        "user": user,
        "title": "Profile",
        "favorites": favorites,
        "user_favorite_ids": user_favorite_ids,
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