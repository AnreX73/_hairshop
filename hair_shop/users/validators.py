from django.contrib.auth.password_validation import (
    CommonPasswordValidator,
    MinimumLengthValidator,
    NumericPasswordValidator,
    UserAttributeSimilarityValidator,
)
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class RuMinimumLengthValidator(MinimumLengthValidator):
    def validate(self, password, user=None):
        if len(password) < self.min_length:
            raise ValidationError(
                _(
                    "Этот пароль слишком короткий. Он должен содержать не менее %(min_length)d символов."
                ),
                code="password_too_short",
                params={"min_length": self.min_length},
            )


class RuCommonPasswordValidator(CommonPasswordValidator):
    def validate(self, password, user=None):
        if password.lower().strip() in self.passwords:
            raise ValidationError(
                _("Введённый пароль слишком широко распространён."),
                code="password_too_common",
            )


class RuNumericPasswordValidator(NumericPasswordValidator):
    def validate(self, password, user=None):
        if password.isdigit():
            raise ValidationError(
                _("Введённый пароль состоит только из цифр."),
                code="password_entirely_numeric",
            )


class RuUserAttributeSimilarityValidator(UserAttributeSimilarityValidator):
    def validate(self, password, user=None):
        if not user:
            return
        # Вызываем оригинальную проверку, но перехватываем ошибку для перевода
        try:
            super().validate(password, user)
        except ValidationError:
            raise ValidationError(
                _("Пароль слишком похож на ваше имя пользователя или email."),
                code="password_too_similar",
            )
