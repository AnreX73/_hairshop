from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse


class User(AbstractUser):
    phone_number = models.CharField(max_length=30, default='', verbose_name='телефон для связи')
    delivery_city = models.CharField(max_length=30, default='', verbose_name='город доставки')
    delivery_address = models.CharField(max_length=100, default='', verbose_name='адрес доставки')
    delivery_postal_code = models.CharField(max_length=20, default='', verbose_name='индекс')

    def get_absolute_url(self):
        return reverse('profile', kwargs={'user_id': self.id})
    
    def user_first_mark(self):
        return self.first_name[0].upper() if self.first_name else self.username[0].upper()

    def __str__(self):
        return self.username
