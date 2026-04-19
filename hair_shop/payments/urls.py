from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_payment, name='create_payment'),
    path('webhook/', views.webhook, name='payment_webhook'),
    path('return/', views.payment_return, name='payment_return'),  # редирект после оплаты
    path('refund/<int:payment_id>/', views.create_refund, name='create_refund'),  # возврат
]