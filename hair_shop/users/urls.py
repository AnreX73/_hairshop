from django.urls import path


from users.views import (
    profile,
    LoginUser,
    RegisterUser,
    UserPasswordResetView,
    UserPasswordResetConfirmView,
)
from django.contrib.auth.views import LogoutView, PasswordResetDoneView, PasswordResetCompleteView


app_name = "users"


urlpatterns = [
    path("profile/", profile, name="profile"),
]


urlpatterns += [
    path("login/", LoginUser.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("register/", RegisterUser.as_view(), name="register"),

    path("password_reset/", UserPasswordResetView.as_view(), name="password_reset"),
    path(
        "password_reset/done/",
        PasswordResetDoneView.as_view(
            template_name="users/user_password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        UserPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        PasswordResetCompleteView.as_view(
            template_name="users/user_password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]
