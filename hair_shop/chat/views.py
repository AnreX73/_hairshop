import uuid

from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import ValidationError
from django.db.models import Exists, OuterRef
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from shop.models import CartItem

from .models import Conversation
from .services import (
    CLIENT_STATUS_LABELS,
    ChatError,
    RateLimited,
    can_reply,
    client_status,
    create_message,
    publish_message,
)
from .utils import compress_chat_image, convert_chat_audio


def _staff_required(view):
    return login_required(user_passes_test(lambda user: user.is_staff)(view))


@require_POST
def start(request):
    """Открывает диалог посетителя.

    Браузер получает только cookie сессии; ключ диалога остаётся на сервере.
    Авторизованному посетителю диалог дополнительно привязывается к аккаунту.
    """
    conversation = None
    conversation_id = request.session.get("chat_conversation")
    if conversation_id:
        try:
            conversation = Conversation.objects.filter(pk=conversation_id).first()
        except (ValidationError, ValueError):
            conversation = None

    if conversation is None:
        conversation = Conversation.objects.create(
            user=request.user if request.user.is_authenticated else None
        )
        request.session["chat_conversation"] = str(conversation.pk)
    elif request.user.is_authenticated and conversation.user_id is None:
        conversation.user = request.user
        conversation.save(update_fields=["user"])

    return JsonResponse({"socket_path": "/ws/chat/"})


def _handle_upload(request, conversation, *, is_staff):
    image_file = request.FILES.get("image")
    audio_file = request.FILES.get("audio")
    if not image_file and not audio_file:
        return JsonResponse({"error": "Файл не передан."}, status=400)
    if image_file and audio_file:
        return JsonResponse(
            {"error": "Прикрепите фото или голосовое, но не оба сразу."},
            status=400,
        )

    try:
        client_id = uuid.UUID(str(request.POST.get("client_id")))
    except (ValueError, TypeError):
        return JsonResponse(
            {"error": "Некорректный идентификатор сообщения."}, status=400
        )

    image = None
    audio = None
    audio_duration = 0
    try:
        if image_file:
            image = compress_chat_image(image_file)
        else:
            audio, audio_duration = convert_chat_audio(audio_file)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    try:
        message, created = create_message(
            conversation,
            is_staff=is_staff,
            author=request.user if is_staff else None,
            text=request.POST.get("text", ""),
            image=image,
            audio=audio,
            audio_duration=audio_duration,
            client_id=client_id,
        )
    except RateLimited as exc:
        return JsonResponse({"error": str(exc)}, status=429)
    except ChatError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    if created:
        publish_message(conversation, message, created=True)

    return JsonResponse({"status": "ok", "message": message.payload()})


@require_POST
def upload_image(request):
    """Загрузка фото или голосового посетителем: диалог из сессии."""
    conversation_id = request.session.get("chat_conversation")
    conversation = None
    if conversation_id:
        try:
            conversation = Conversation.objects.filter(pk=conversation_id).first()
        except (ValidationError, ValueError):
            conversation = None
    if conversation is None:
        return JsonResponse({"error": "Чат не открыт."}, status=403)
    return _handle_upload(request, conversation, is_staff=False)


@login_required
@require_POST
def upload_operator_image(request, pk):
    if not can_reply(request.user):
        return JsonResponse({"error": "forbidden"}, status=403)
    conversation = get_object_or_404(Conversation, pk=pk)
    return _handle_upload(request, conversation, is_staff=True)


@_staff_required
def inbox(request):
    conversations = (
        Conversation.objects.filter(messages__isnull=False)
        .select_related("user")
        .annotate(
            has_cart=Exists(
                CartItem.objects.filter(cart__user_id=OuterRef("user_id"))
            )
        )
        .distinct()[:100]
    )
    return render(request, "chat/inbox.html", {"conversations": conversations})


@_staff_required
def conversation(request, pk):
    conversation = get_object_or_404(
        Conversation.objects.select_related("user"), pk=pk
    )
    status = client_status(conversation)
    return render(
        request,
        "chat/conversation.html",
        {
            "conversation": conversation,
            "client_status": status,
            "client_status_label": CLIENT_STATUS_LABELS[status],
        },
    )
