from django import forms
from shop.models import Order, Product

class OrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status']

class OrderShipForm(forms.ModelForm):
    """Отдельная форма для отправки — там ещё трек-номер"""
    class Meta:
        model = Order
        fields = ['tracking_number']

class OrderPaymentStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['payment_status']


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            # --- Основное ---
            'name', 'article', 'category', 'price', 'discount_percentage',
            'is_available', 'is_hit',
            # --- Описание ---
            'description', 'note_for_manager', 'product_group',
            # --- Характеристики ---
            'color', 'hair_length', 'hair_width', 'hair_material',
            'number_of_strands', 'hair_extension_method', 'hair_type',
            'country_of_origin',
            # --- Упаковка / комплектация ---
            'kit', 'decoration', 'package',
            'packaging_weight', 'packaging_length',
            'packaging_width', 'packaging_height',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'note_for_manager': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Все поля — не обязательные по умолчанию (кроме name, article, category)
        required_fields = {'name', 'article', 'category', 'price'}
        for name, field in self.fields.items():
            if name not in required_fields:
                field.required = False
            # Красивые плейсхолдеры
            field.widget.attrs.setdefault('class', 'form-control')