import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import PushSubscription, ChatSession, ChatMessage
from django.shortcuts import get_object_or_404


@login_required
@require_POST
def save_subscription(request):
    """
    Браузер вызывает этот endpoint, когда пользователь разрешает уведомления.
    Сохраняем subscription object в БД.
    """
    try:
        data = json.loads(request.body)

        endpoint = data["endpoint"]
        p256dh = data["keys"]["p256dh"]
        auth = data["keys"]["auth"]

        # Обновляем если уже есть, создаём если нет
        PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                "user": request.user,
                "p256dh": p256dh,
                "auth": auth,
            },
        )
        return JsonResponse({"status": "ok"})

    except (KeyError, json.JSONDecodeError) as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


@login_required
@require_POST
def delete_subscription(request):
    """
    Вызывается когда пользователь отписывается от уведомлений.
    """
    try:
        data = json.loads(request.body)
        PushSubscription.objects.filter(
            user=request.user, endpoint=data["endpoint"]
        ).delete()
        return JsonResponse({"status": "ok"})
    except (KeyError, json.JSONDecodeError) as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


@login_required
def get_or_create_session(request):
    """Клиент открывает чат — получает свою активную сессию или создаёт новую."""
    session, _ = ChatSession.objects.get_or_create(
        client=request.user,
        is_active=True,
    )
    return JsonResponse({"session_id": session.id})


@login_required
def poll_messages(request, session_id, last_id):
    """Polling: вернуть сообщения новее last_id."""
    session = get_object_or_404(ChatSession, id=session_id)

    # Клиент может читать только свою сессию
    if not request.user.is_staff and session.client != request.user:
        return JsonResponse({"error": "forbidden"}, status=403)

    messages = session.messages.filter(id__gt=last_id).values(
        "id", "sender", "msg_type", "text", "image", "created_at"
    )
    # image — относительный путь, делаем полный URL
    result = []
    for m in messages:
        m["created_at"] = m["created_at"].strftime("%H:%M")
        if m["image"]:
            m["image"] = request.build_absolute_uri(f"/media/{m['image']}")
        result.append(m)

    return JsonResponse({"messages": result})


@login_required
@require_POST
def send_message(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id)

    if not request.user.is_staff and session.client != request.user:
        return JsonResponse({"error": "forbidden"}, status=403)

    sender = "admin" if request.user.is_staff else "client"
    msg_type = request.POST.get("msg_type", "text")
    text = request.POST.get("text", "").strip()
    image_file = request.FILES.get("image")

    msg = ChatMessage.objects.create(
        session=session,
        sender=sender,
        msg_type=msg_type,
        text=text,
        image=image_file,  # None если нет — Django обработает
    )
    return JsonResponse({"id": msg.id, "status": "ok"})


def unread_chat_count(request):
    """Количество сессий с непрочитанными сообщениями от клиентов."""
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"count": 0})

    count = (
        ChatSession.objects.filter(
            is_active=True,
            messages__sender="client",
            messages__is_read=False,
        )
        .distinct()
        .count()
    )

    return JsonResponse({"count": count})
