import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from .models import PushSubscription


@login_required
@require_POST
def save_subscription(request):
    """
    Браузер вызывает этот endpoint, когда пользователь разрешает уведомления.
    Сохраняем subscription object в БД.
    """
    try:
        data = json.loads(request.body)

        endpoint = data['endpoint']
        p256dh = data['keys']['p256dh']
        auth = data['keys']['auth']

        # Обновляем если уже есть, создаём если нет
        PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                'user': request.user,
                'p256dh': p256dh,
                'auth': auth,
            }
        )
        return JsonResponse({'status': 'ok'})

    except (KeyError, json.JSONDecodeError) as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
@require_POST
def delete_subscription(request):
    """
    Вызывается когда пользователь отписывается от уведомлений.
    """
    try:
        data = json.loads(request.body)
        PushSubscription.objects.filter(
            user=request.user,
            endpoint=data['endpoint']
        ).delete()
        return JsonResponse({'status': 'ok'})
    except (KeyError, json.JSONDecodeError) as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

