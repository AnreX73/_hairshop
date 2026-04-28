from django import forms
from shop.models import Order

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