from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    UserCreationForm,
    PasswordResetForm,
    SetPasswordForm,
)
from django.forms import widgets
from shop.models import Product


User = get_user_model()


class RegisterUserForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Делаем все поля кроме email и паролей необязательными
        optional_fields = ["first_name", "last_name", "phone_number", "delivery_city", "delivery_address"]
        for field in optional_fields:
            if field in self.fields:
                self.fields[field].required = False

    email = forms.EmailField(
        required=True,
        label="Email",
        widget=forms.TextInput(
            attrs={
                "autocomplete": "off",
                "placeholder": "example@mail.com",
            }
        ),
    )

    password1 = forms.CharField(
        required=True, label="Пароль", widget=forms.PasswordInput
    )

    password2 = forms.CharField(
        required=True, label="Повторите пароль", widget=forms.PasswordInput
    )

    class Meta:
        model = User
        fields = (
            "email",
            "password1",
            "password2",
        )

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Пользователь с таким email уже существует.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        email = self.cleaned_data["email"]
        # username = email, гарантируем уникальность через срез если нужно
        user.username = email[:150]
        user.email = email
        if commit:
            user.save()
        return user

class ChangeUserInfoForm(forms.ModelForm):
    def __init__(self, *args, checkout=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = False
        self.fields["last_name"].required = False
        self.fields["delivery_city"].required = False
        self.fields["delivery_address"].required = False
        # phone_number обязателен только при оформлении заказа
        self.fields["phone_number"].required = checkout

    phone_number = forms.CharField(
        label="Телефон для связи",
        max_length=30,
        required=False,  # согласовано с __init__
        widget=forms.TextInput(attrs={"class": "file_group"}),
    )

    email = forms.EmailField(required=True, label="Email", widget=forms.TextInput)

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Пользователь с таким email уже существует.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"][:150]
        if commit:
            user.save()
        return user

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "phone_number", "delivery_city", "delivery_address")
     


class LoginUserForm(AuthenticationForm):
    username = forms.CharField(
        max_length=150,
        required=True,
        label="email",
        widget=forms.TextInput(
            attrs={
                "class": "my_input",
                "readonly onfocus": "this.removeAttribute('readonly');",
                "autocomplete": "off",
            }
        ),
    )

    password = forms.CharField(
        required=True, label="Пароль", widget=forms.PasswordInput
    )

    class Meta:
        model = User
        fields = ("username", "password")

class UserPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(required=True, label="Email", widget=forms.TextInput)


class UserPasswordResetConfirmForm(SetPasswordForm):
    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)

    new_password1 = forms.CharField(
        required=True, label="Новый пароль", widget=forms.PasswordInput
    )

    new_password2 = forms.CharField(
        required=True, label="Повторите пароль", widget=forms.PasswordInput
    )



