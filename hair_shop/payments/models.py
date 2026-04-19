from django.db import models



class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('succeeded', 'Успешно'),
        ('canceled', 'Отменён'),
        ('refunded', 'Возврат'),
    ]
    order = models.ForeignKey('shop.Order', on_delete=models.CASCADE)
    yookassa_payment_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
