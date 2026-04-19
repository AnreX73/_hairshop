from django.shortcuts import render

import uuid
from yookassa import Configuration, Payment
from django.conf import settings

import json
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

from yookassa import Refund

Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

def create_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    payment = Payment.create({
        "amount": {
            "value": str(order.total_price),
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": request.build_absolute_uri(reverse('payment_return'))
        },
        "capture": True,  # автоматически списать после подтверждения
        "description": f"Заказ №{order.id}",
        "metadata": {"order_id": order.id}
    }, uuid.uuid4())  # idempotency key — защита от дублей
    
    # Сохраняем в БД
    PaymentRecord.objects.create(
        order=order,
        yookassa_payment_id=payment.id,
        amount=order.total_price,
    )
    
    return redirect(payment.confirmation.confirmation_url)




@csrf_exempt  # ЮКасса не знает твой CSRF-токен
def webhook(request):
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
        # здесь: активировать заказ, отправить email и т.д.
    
    elif event == 'payment.canceled':
        record.status = 'canceled'
        record.save()
    
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