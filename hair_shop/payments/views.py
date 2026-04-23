from django.shortcuts import render
from shop.models import Order

import uuid
from yookassa import Configuration, Payment as YookassaPayment
from .models import Payment as PaymentRecord
from django.conf import settings

import json
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.shortcuts import redirect

from yookassa import Refund



Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

@login_required
def create_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    payment = YookassaPayment.create({
        "amount": {
            "value": str(order.total),
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": request.build_absolute_uri(reverse('payments:payment_return'))
        },
        "capture": True,
        "description": f"Заказ №{order.order_number}",
        "metadata": {"order_id": order.id},
        "receipt": {
        "customer": {
            "email": order.customer_email,
        },
        "items": [
            {
                "description": item.product_name,
                "quantity": str(item.quantity),
                "amount": {
                    "value": str(item.product_price),
                    "currency": "RUB"
                },
                "vat_code": 1,  # 1 = без НДС
            }
            for item in order.items.all()
        ]
    }
}, uuid.uuid4())
   

    PaymentRecord.objects.create(
        order=order,
        yookassa_payment_id=payment.id,
        amount=order.total,
    )

    return redirect(payment.confirmation.confirmation_url)




@csrf_exempt  # ЮКасса не знает твой CSRF-токен
def webhook(request):
    print("WEBHOOK CALLED", request.method)
    print("BODY:", request.body)
    if request.method != 'POST':
        return HttpResponse(status=405)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)
    
    event = data.get('event')
    payment_data = data.get('object', {})
    payment_id = payment_data.get('id')
    
    try:
        record = PaymentRecord.objects.get(yookassa_payment_id=payment_id)
    except PaymentRecord.DoesNotExist:
        return HttpResponse(status=404)
    
    if event == 'payment.succeeded':
        record.status = 'succeeded'
        record.save()
        
        # Обновляем статус заказа
        record.order.payment_status = 'paid'
        record.order.save()
    
    elif event == 'payment.canceled':
        record.status = 'canceled'
        record.save()

        # Обновляем статус заказа
        record.order.payment_status = 'failed'
        record.order.save()
    
    elif event == 'refund.succeeded':
        record.status = 'refunded'
        record.save()
    
    return HttpResponse(status=200)  # обязательно вернуть 200!





def create_refund(payment_record):
    refund = Refund.create({
        "amount": {
            "value": str(payment_record.amount),
            "currency": "RUB"
        },
        "payment_id": payment_record.yookassa_payment_id
    })
    return refund

def payment_return(request):
    return render(request, 'payments/return.html')