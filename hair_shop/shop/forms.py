from django import forms
from django.contrib.auth import get_user_model
from .models import Product, Category




User = get_user_model()



from django import forms

class OrderForm(forms.Form):
    customer_name = forms.CharField(
        label='ФИО', max_length=200,
        widget=forms.TextInput(attrs={'placeholder': 'Иванова Мария Петровна'})
    )
    customer_email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'placeholder': 'example@mail.ru'})
    )
    customer_phone = forms.CharField(
        label='Телефон', max_length=20,
        widget=forms.TextInput(attrs={'placeholder': '+7 (999) 123-45-67'})
    )
    delivery_city = forms.CharField(
        label='Город', max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'Новосибирск'})
    )
    delivery_address = forms.CharField(
        label='Адрес доставки',
        widget=forms.TextInput(attrs={'placeholder': 'ул. Ленина, д. 1, кв. 10'})
    )
    delivery_postal_code = forms.CharField(
        label='Индекс', max_length=20,
        widget=forms.TextInput(attrs={'placeholder': '630000'})
    )
    notes = forms.CharField(
        label='Комментарий к заказу', required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Позвонить за час до доставки...'})
    )

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class ReviewForm(forms.Form):
    rating = forms.IntegerField(
        label='Оценка', min_value=1, max_value=5,
        widget=forms.NumberInput(attrs={'type': 'range', 'min': 1, 'max': 5, 'step': 1})
    )
    title = forms.CharField(
        label='Заголовок', max_length=200,
        widget=forms.TextInput(attrs={'placeholder': 'Кратко о товаре'})
    )
    text = forms.CharField(
        label='Текст отзыва',
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Поделитесь впечатлениями...'})
    )
    files = MultipleFileField(label='Фото / видео', required=False)


class SearchProductForm(forms.Form):
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        empty_label="Все категории",
        required=False,
        widget=forms.Select(attrs={'class': 'custom-select'})
        
    )

    class Meta:
        model = Product
        fields = ('category',)
        
        