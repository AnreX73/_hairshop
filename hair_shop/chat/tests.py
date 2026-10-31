import tempfile
import uuid
from io import BytesIO
from typing import Any, cast

from asgiref.sync import async_to_sync
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TransactionTestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Conversation, Message
from .routing import websocket_urlpatterns
from .utils import compress_chat_image


class ChatTests(TransactionTestCase):
    client: Any

    def setUp(self):
        cache.clear()
        self.conversation = Conversation.objects.create()

    def communicator(self, conversation=None, operator=None):
        if operator:
            assert conversation is not None
        path = (
            f"/ws/chat/operator/{conversation.pk}/"
            if operator and conversation
            else "/ws/chat/"
        )
        socket = WebsocketCommunicator(URLRouter(websocket_urlpatterns), path)
        scope = cast(dict[str, Any], socket.scope)
        scope["user"] = operator or AnonymousUser()
        scope["session"] = (
            {"chat_conversation": str(conversation.pk)} if conversation else {}
        )
        return socket

    @staticmethod
    def image_file(name="photo.jpg", size=(3000, 2000)):
        buffer = BytesIO()
        Image.new("RGB", size, "red").save(buffer, format="JPEG")
        return SimpleUploadedFile(
            name, buffer.getvalue(), content_type="image/jpeg"
        )

    def test_start_is_post_only_and_reuses_guest_session(self):
        self.assertEqual(self.client.get(reverse("chat:start")).status_code, 405)
        self.assertEqual(self.client.post(reverse("chat:start")).status_code, 200)
        key = self.client.session["chat_conversation"]
        self.client.post(reverse("chat:start"))
        self.assertEqual(self.client.session["chat_conversation"], key)
        self.assertTrue(Conversation.objects.filter(pk=key).exists())

    def test_start_requires_csrf(self):
        response = cast(
            Any,
            Client(enforce_csrf_checks=True).post(reverse("chat:start")),
        )
        self.assertEqual(response.status_code, 403)

    def test_start_binds_authenticated_user(self):
        user = get_user_model().objects.create_user(
            username="client", password="test"
        )
        self.client.force_login(user)
        self.client.post(reverse("chat:start"))
        conversation = Conversation.objects.get(
            pk=self.client.session["chat_conversation"]
        )
        self.assertEqual(conversation.user, user)
        self.assertEqual(conversation.client_label, "client")

    def test_operator_http_is_protected(self):
        self.assertEqual(self.client.get(reverse("chat:inbox")).status_code, 302)
        user = get_user_model().objects.create_user(
            username="staff", is_staff=True
        )
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("chat:inbox")).status_code, 200)

    def test_operator_conversation_page_renders(self):
        Message.objects.create(
            conversation=self.conversation, text="Здравствуйте"
        )
        user = get_user_model().objects.create_user(
            username="staff", password="test", is_staff=True
        )
        self.client.force_login(user)
        response = self.client.get(
            reverse("chat:conversation", args=[self.conversation.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "operator-page-chat-input")
        self.assertContains(
            response, f"/ws/chat/operator/{self.conversation.pk}/"
        )

    def test_visitor_widget_template_renders(self):
        from django.template.loader import render_to_string

        html = render_to_string(
            "chat/widget.html",
            {"VAPID_PUBLIC_KEY": "test-key"},
        )
        self.assertIn("supportChat", html)
        self.assertIn(reverse("chat:start"), html)
        self.assertIn(reverse("chat:upload"), html)

    def test_websocket_requires_session(self):
        async def run():
            socket = self.communicator()
            connected, code = await socket.connect()
            self.assertFalse(connected)
            self.assertEqual(code, 4403)
            await socket.disconnect()

        async_to_sync(run)()

    def test_malformed_session_conversation_is_rejected(self):
        async def run():
            socket = WebsocketCommunicator(
                URLRouter(websocket_urlpatterns), "/ws/chat/"
            )
            scope = cast(dict[str, Any], socket.scope)
            scope["user"] = AnonymousUser()
            scope["session"] = {"chat_conversation": "not-a-uuid"}
            connected, code = await socket.connect()
            self.assertFalse(connected)
            self.assertEqual(code, 4403)
            await socket.disconnect()

        async_to_sync(run)()

    def test_guest_messages_are_persisted_and_deduplicated(self):
        async def run():
            socket = self.communicator(self.conversation)
            self.assertTrue((await socket.connect())[0])
            self.assertEqual(
                (await socket.receive_json_from())["type"], "history"
            )
            payload = {
                "text": "Нужны белые пряди",
                "client_id": str(uuid.uuid4()),
                "is_staff": True,
            }
            await socket.send_json_to(payload)
            first = await socket.receive_json_from()
            self.assertFalse(first["message"]["is_staff"])
            await socket.send_json_to(payload)
            self.assertEqual(
                (await socket.receive_json_from())["message"]["id"],
                first["message"]["id"],
            )
            await socket.disconnect()

        async_to_sync(run)()
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(Message.objects.get().text, "Нужны белые пряди")

    def test_operator_and_guest_exchange_messages(self):
        operator = get_user_model().objects.create_user(
            username="operator", password="test", is_staff=True
        )

        async def run():
            guest = self.communicator(self.conversation)
            staff = self.communicator(self.conversation, operator)
            for socket in (guest, staff):
                self.assertTrue((await socket.connect())[0])
                await socket.receive_json_from()
            await staff.send_json_to(
                {
                    "text": "Уточните, пожалуйста, оттенок",
                    "client_id": str(uuid.uuid4()),
                }
            )
            self.assertTrue(
                (await guest.receive_json_from())["message"]["is_staff"]
            )
            self.assertTrue(
                (await staff.receive_json_from())["message"]["is_staff"]
            )
            await guest.disconnect()
            await staff.disconnect()

        async_to_sync(run)()

    def test_other_sessions_cannot_read_messages(self):
        other = Conversation.objects.create()
        Message.objects.create(
            conversation=self.conversation, text="Приватное сообщение"
        )

        async def run():
            socket = self.communicator(other)
            self.assertTrue((await socket.connect())[0])
            self.assertEqual(
                (await socket.receive_json_from())["messages"], []
            )
            await socket.disconnect()

        async_to_sync(run)()

    def test_invalid_messages_and_rate_limit(self):
        async def run():
            socket = self.communicator(self.conversation)
            await socket.connect()
            await socket.receive_json_from()
            for payload in (
                [],
                {"text": "x", "client_id": "bad"},
                {"text": "x" * 2001, "client_id": str(uuid.uuid4())},
            ):
                await socket.send_json_to(payload)
                self.assertEqual(
                    (await socket.receive_json_from())["type"], "error"
                )
            await socket.send_to(text_data="not-json")
            self.assertEqual(
                (await socket.receive_json_from())["type"], "error"
            )
            for _ in range(20):
                await socket.send_json_to(
                    {"text": "Вопрос", "client_id": str(uuid.uuid4())}
                )
                self.assertEqual(
                    (await socket.receive_json_from())["type"], "message"
                )
            await socket.send_json_to(
                {"text": "Вопрос", "client_id": str(uuid.uuid4())}
            )
            self.assertEqual(
                (await socket.receive_json_from())["type"], "error"
            )
            await socket.disconnect()

        async_to_sync(run)()
        self.assertEqual(Message.objects.count(), 20)

    def test_non_staff_operator_is_denied(self):
        user = get_user_model().objects.create_user(
            username="no-access", is_staff=False
        )

        async def run():
            socket = self.communicator(self.conversation, user)
            connected, code = await socket.connect()
            self.assertFalse(connected)
            self.assertEqual(code, 4403)
            await socket.disconnect()

        async_to_sync(run)()

    def test_cleanup_old_conversations(self):
        from datetime import timedelta

        from django.utils import timezone

        from .tasks import cleanup_old_conversations

        old = Conversation.objects.create()
        Message.objects.create(conversation=old, text="Старое сообщение")
        Message.objects.filter(conversation=old).update(
            created_at=timezone.now() - timedelta(days=31)
        )
        empty = Conversation.objects.create()
        Message.objects.create(
            conversation=self.conversation, text="Свежее сообщение"
        )

        result = cleanup_old_conversations()

        self.assertFalse(Conversation.objects.filter(pk=old.pk).exists())
        self.assertTrue(Conversation.objects.filter(pk=empty.pk).exists())
        self.assertTrue(
            Conversation.objects.filter(pk=self.conversation.pk).exists()
        )
        self.assertIn("1", result)

    def test_compress_chat_image_returns_webp(self):
        content = compress_chat_image(self.image_file())
        image = Image.open(content)
        self.assertEqual(image.format, "WEBP")
        self.assertLessEqual(max(image.size), 1920)

    def test_guest_image_upload_creates_webp_message(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                self.client.post(reverse("chat:start"))
                response = self.client.post(
                    reverse("chat:upload"),
                    {
                        "client_id": str(uuid.uuid4()),
                        "image": self.image_file(),
                    },
                )
                self.assertEqual(response.status_code, 200)
                message = Message.objects.get()
                self.assertTrue(message.image.name.endswith(".webp"))
                self.assertEqual(message.text, "")
                self.assertEqual(response.json()["message"]["image"][-5:], ".webp")

    def test_image_upload_requires_open_chat(self):
        response = self.client.post(
            reverse("chat:upload"),
            {"client_id": str(uuid.uuid4()), "image": self.image_file()},
        )
        self.assertEqual(response.status_code, 403)

    def test_operator_image_upload_requires_staff(self):
        user = get_user_model().objects.create_user(
            username="client", password="test"
        )
        self.client.force_login(user)
        response = self.client.post(
            reverse("chat:operator_upload", args=[self.conversation.pk]),
            {"client_id": str(uuid.uuid4()), "image": self.image_file()},
        )
        self.assertEqual(response.status_code, 403)

        staff = get_user_model().objects.create_user(
            username="staff", password="test", is_staff=True
        )
        self.client.force_login(staff)
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.post(
                    reverse(
                        "chat:operator_upload",
                        args=[self.conversation.pk],
                    ),
                    {
                        "client_id": str(uuid.uuid4()),
                        "image": self.image_file(),
                    },
                )
                self.assertEqual(response.status_code, 200)
                self.assertTrue(Message.objects.get().is_staff)
