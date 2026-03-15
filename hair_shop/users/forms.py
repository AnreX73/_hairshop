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
    #сделать некоторые поля необязательными кроме username, email, password1, password2
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = False
        self.fields["last_name"].required = False
        self.fields["phone_number"].required = False
        self.fields["delivery_city"].required = False
        self.fields["delivery_address"].required = False

        
    username = forms.CharField(
        max_length=150,
        required=True,
        label="Имя пользователя",
        widget=forms.TextInput(
            attrs={
                "readonly": True,
                "onfocus": "this.removeAttribute('readonly')",
                "autocomplete": "off",
            }
        ),
    )

    email = forms.EmailField(required=True, label="Email", widget=forms.TextInput)

    

    password1 = forms.CharField(
        required=True, label="Пароль", widget=forms.PasswordInput
    )

    password2 = forms.CharField(
        required=True, label="Повторите пароль", widget=forms.PasswordInput
    )

    class Meta:
        model = User
        fields = (
            "username",
            "email",
           "first_name",
           "last_name",
           "phone_number",
           "delivery_city",
           "delivery_address",
            "password1",
            "password2",
        )
        #скрыть необязательные поля в шаблоне
        widgets = {
            "first_name": forms.TextInput(attrs={"style": "display: none;"}),
            "last_name": forms.TextInput(attrs={"style": "display: none;"}),
            "phone_number": forms.TextInput(attrs={"style": "display: none;"}),
            "delivery_city": forms.TextInput(attrs={"style": "display: none;"}),
            "delivery_address": forms.TextInput(attrs={"style": "display: none;"}),
        }

class ChangeUserlnfoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        self.fields["phone_number"].required = False
        self.fields["delivery_city"].required = True
        self.fields["delivery_address"].required = True

    phone_number = forms.CharField(
        label="телефон для связи",
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={"class": "file_group"}),
    )
    email = forms.EmailField(required=True, label="Email", widget=forms.TextInput)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "first_name", "last_name", "phone_number", "delivery_city", "delivery_address")
     


class LoginUserForm(AuthenticationForm):
    username = forms.CharField(
        max_length=150,
        required=True,
        label="Имя пользователя или email",
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



