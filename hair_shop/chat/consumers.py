import uuid

from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from django.core.exceptions import ValidationError

from .models import Conversation
from .services import (
    OPERATORS_GROUP,
    ChatError,
    RateLimited,
    can_reply,
    create_message,
    publish_message,
    summary,
)


class ChatConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.group_name = None
        self.conversation = None
        route = self.scope.get("url_route", {}).get("kwargs", {})
        self.operator = "pk" in route
        user = self.scope.get("user")

        if self.operator:
            if not can_reply(user):
                self.close(code=4403)
                return
            conversation_id = route["pk"]
        else:
            session = self.scope.get("session")
            conversation_id = session.get("chat_conversation") if session else None

        if conversation_id:
            try:
                self.conversation = (
                    Conversation.objects.select_related("user")
                    .filter(pk=conversation_id)
                    .first()
                )
            except (ValidationError, ValueError):
                self.conversation = None

        if self.conversation is None:
            self.close(code=4403)
            return

        self.group_name = f"chat.{self.conversation.pk.hex}"
        # Подписываемся до accept: сообщения, отправленные параллельно,
        # браузер отсеет по ID.
        async_to_sync(self.channel_layer.group_add)(
            self.group_name, self.channel_name
        )
        self.accept()

        messages = list(self.conversation.messages.order_by("-id")[:100])
        self.send_json(
            {
                "type": "history",
                "messages": [m.payload() for m in reversed(messages)],
            }
        )

    def disconnect(self, code):
        if self.group_name:
            async_to_sync(self.channel_layer.group_discard)(
                self.group_name, self.channel_name
            )

    def receive(self, text_data=None, bytes_data=None, **kwargs):
        if (
            bytes_data is not None
            or text_data is None
            or len(text_data.encode("utf-8")) > 16384
        ):
            self.close(code=1009)
            return
        try:
            content = self.decode_json(text_data)
        except (ValueError, TypeError):
            self.send_json(
                {"type": "error", "message": "Некорректный формат сообщения."}
            )
            return
        self.receive_json(content)

    def receive_json(self, content, **kwargs):
        if not isinstance(content, dict):
            self.send_json(
                {"type": "error", "message": "Некорректный формат сообщения."}
            )
            return

        try:
            client_id = uuid.UUID(str(content.get("client_id")))
        except (ValueError, TypeError):
            self.send_json(
                {"type": "error", "message": "Некорректный идентификатор сообщения."}
            )
            return

        text = content.get("text")
        if not isinstance(text, str) or not text.strip() or len(text) > 2000:
            self.send_json(
                {"type": "error", "message": "Введите сообщение от 1 до 2000 символов."}
            )
            return

        user = self.scope.get("user")
        if self.operator and not can_reply(user):
            self.close(code=4403)
            return

        try:
            message, created = create_message(
                self.conversation,
                is_staff=self.operator,
                author=user if self.operator else None,
                text=text,
                client_id=client_id,
            )
        except RateLimited as exc:
            self.send_json({"type": "error", "message": str(exc)})
            return
        except ChatError as exc:
            self.send_json({"type": "error", "message": str(exc)})
            return

        if created:
            publish_message(self.conversation, message, created=True)
        else:
            self.send_json({"type": "message", "message": message.payload()})

    def chat_message(self, event):
        self.send_json({"type": "message", "message": event["message"]})


class OperatorInboxConsumer(JsonWebsocketConsumer):
    """Список диалогов для виджета оператора: снимок и живые обновления."""

    def connect(self):
        self.joined = False
        if not can_reply(self.scope.get("user")):
            self.close(code=4403)
            return
        async_to_sync(self.channel_layer.group_add)(
            OPERATORS_GROUP, self.channel_name
        )
        self.joined = True
        self.accept()
        self.send_json({"type": "inbox", "conversations": self.snapshot()})

    def disconnect(self, code):
        if self.joined:
            async_to_sync(self.channel_layer.group_discard)(
                OPERATORS_GROUP, self.channel_name
            )

    def receive(self, text_data=None, bytes_data=None, **kwargs):
        pass  # Клиент ничего не присылает, только слушает.

    def snapshot(self):
        result = []
        conversations = (
            Conversation.objects.filter(messages__isnull=False)
            .select_related("user")
            .distinct()[:50]
        )
        for conversation in conversations:
            last = conversation.messages.order_by("-id").first()
            if last:
                result.append(summary(conversation, last))
        return result

    def inbox_update(self, event):
        self.send_json({"type": "update", "conversation": event["conversation"]})
