import os
import subprocess
import tempfile
import uuid
import wave
from datetime import timedelta
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
from django.utils import timezone
from PIL import Image

from shop.models import Cart, CartItem, Category, Product

from .models import Conversation, Message
from .routing import websocket_urlpatterns
from .services import client_status, summary
from .tasks import cleanup_old_conversations
from .utils import _ffmpeg_binary, compress_chat_image, convert_chat_audio


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

    @staticmethod
    def audio_file(seconds=1, name="voice.wav"):
        buffer = BytesIO()
        sample_rate = 8000
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(b"\x00\x00" * sample_rate * seconds)
        return SimpleUploadedFile(
            name, buffer.getvalue(), content_type="audio/wav"
        )

    @staticmethod
    def webm_audio_file(seconds=2, name="voice.webm"):
        """WebM/Opus без Duration в заголовке — так пишет MediaRecorder."""
        result = subprocess.run(
            [
                _ffmpeg_binary(),
                "-y",
                "-hide_banner",
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency=440:duration={seconds}",
                "-c:a",
                "libopus",
                "-f",
                "webm",
                "-live",
                "1",
                "pipe:1",
            ],
            capture_output=True,
            timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.decode("utf-8", "replace"))
        return SimpleUploadedFile(
            name, result.stdout, content_type="audio/webm"
        )

    def make_user(self, username, *, is_staff=False):
        return get_user_model().objects.create_user(
            username=username,
            password="test",
            is_staff=is_staff,
        )

    def add_cart_item(self, user):
        cart, _ = Cart.objects.get_or_create(user=user)
        category, _ = Category.objects.get_or_create(
            slug="chat-tests",
            defaults={"name": "Chat tests"},
        )
        product = Product.objects.create(
            article=f"chat-{uuid.uuid4().hex[:8]}",
            category=category,
        )
        return CartItem.objects.create(cart=cart, product=product)

    @staticmethod
    def age_last_message(conversation, **delta):
        Message.objects.filter(conversation=conversation).update(
            created_at=timezone.now() - timedelta(**delta)
        )

    def conversation_with_message(self, **kwargs):
        conversation = Conversation.objects.create(**kwargs)
        Message.objects.create(conversation=conversation, text="Сообщение")
        return conversation

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
        self.assertIn("🎤 Голос", html)
        self.assertIn("chat-message-audio", html)
        self.assertIn("pauseOtherAudio($event.currentTarget)", html)

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

    def test_cleanup_removes_guest_conversations_after_seven_days(self):
        fresh = self.conversation_with_message()
        self.age_last_message(fresh, days=6)
        stale = self.conversation_with_message()
        self.age_last_message(stale, days=8)

        result = cleanup_old_conversations()

        self.assertTrue(Conversation.objects.filter(pk=fresh.pk).exists())
        self.assertFalse(Conversation.objects.filter(pk=stale.pk).exists())
        self.assertIn("гости: 1", result)

    def test_cleanup_keeps_registered_conversations_for_45_days(self):
        user = self.make_user("registered")
        # Пустая корзина не должна давать статус «с корзиной».
        Cart.objects.get_or_create(user=user)
        fresh = self.conversation_with_message(user=user)
        self.age_last_message(fresh, days=44)
        stale = self.conversation_with_message(user=user)
        self.age_last_message(stale, days=46)

        cleanup_old_conversations()

        self.assertTrue(Conversation.objects.filter(pk=fresh.pk).exists())
        self.assertFalse(Conversation.objects.filter(pk=stale.pk).exists())

    def test_cleanup_keeps_cart_conversations_for_90_days(self):
        user = self.make_user("cart-client")
        self.add_cart_item(user)
        fresh = self.conversation_with_message(user=user)
        self.age_last_message(fresh, days=89)
        recent = self.conversation_with_message(user=user)
        # Диалог старше 45 дней, но у клиента есть товар в корзине.
        self.age_last_message(recent, days=46)
        stale = self.conversation_with_message(user=user)
        self.age_last_message(stale, days=91)

        cleanup_old_conversations()

        self.assertTrue(Conversation.objects.filter(pk=fresh.pk).exists())
        self.assertTrue(Conversation.objects.filter(pk=recent.pk).exists())
        self.assertFalse(Conversation.objects.filter(pk=stale.pk).exists())

    def test_cleanup_removes_empty_conversations_after_12_hours(self):
        fresh = Conversation.objects.create()
        stale = Conversation.objects.create()
        Conversation.objects.filter(pk=stale.pk).update(
            created_at=timezone.now() - timedelta(hours=13)
        )

        cleanup_old_conversations()

        self.assertTrue(Conversation.objects.filter(pk=fresh.pk).exists())
        self.assertFalse(Conversation.objects.filter(pk=stale.pk).exists())

    def test_client_status_uses_cart_items_not_cart_row(self):
        registered = self.conversation_with_message(
            user=self.make_user("client")
        )
        empty_cart_user = self.make_user("empty-cart")
        Cart.objects.get_or_create(user=empty_cart_user)
        empty_cart = self.conversation_with_message(user=empty_cart_user)
        cart_user = self.make_user("with-item")
        self.add_cart_item(cart_user)
        with_item = self.conversation_with_message(user=cart_user)

        self.assertEqual(client_status(self.conversation), "guest")
        self.assertEqual(client_status(registered), "registered")
        self.assertEqual(client_status(empty_cart), "registered")
        self.assertEqual(client_status(with_item), "cart")

    def test_inbox_and_conversation_show_client_status(self):
        staff = self.make_user("staff", is_staff=True)
        self.conversation_with_message()
        self.conversation_with_message(user=self.make_user("client"))
        cart_user = self.make_user("cart-client")
        self.add_cart_item(cart_user)
        cart = self.conversation_with_message(user=cart_user)

        self.client.force_login(staff)
        inbox = self.client.get(reverse("chat:inbox"))
        self.assertContains(inbox, "chat-status-guest")
        self.assertContains(inbox, "chat-status-registered")
        self.assertContains(inbox, "chat-status-cart")

        page = self.client.get(reverse("chat:conversation", args=[cart.pk]))
        self.assertContains(page, "chat-status-cart")
        self.assertContains(page, "С корзиной")

    def test_cleanup_deletes_message_image_file(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                conversation = Conversation.objects.create()
                message = Message.objects.create(
                    conversation=conversation,
                    image=SimpleUploadedFile(
                        "photo.webp",
                        b"fake-webp",
                        content_type="image/webp",
                    ),
                )
                path = message.image.path
                self.assertTrue(os.path.exists(path))

                conversation.delete()

                self.assertFalse(os.path.exists(path))

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

    def test_convert_chat_audio_returns_mp3(self):
        content, duration = convert_chat_audio(self.audio_file(seconds=2))
        self.assertTrue(content.name.endswith(".mp3"))
        self.assertEqual(duration, 2)
        self.assertGreater(content.size, 0)

    def test_convert_chat_audio_accepts_webm_without_duration(self):
        content, duration = convert_chat_audio(
            self.webm_audio_file(seconds=2)
        )
        self.assertTrue(content.name.endswith(".mp3"))
        self.assertEqual(duration, 2)
        self.assertGreater(content.size, 0)

    def test_convert_chat_audio_rejects_too_short_recording(self):
        with self.assertRaisesMessage(ValueError, "слишком короткая"):
            convert_chat_audio(self.webm_audio_file(seconds=0.05))

    def test_convert_chat_audio_rejects_empty_recording(self):
        empty = SimpleUploadedFile(
            "voice.webm", b"", content_type="audio/webm"
        )
        with self.assertRaisesMessage(ValueError, "Файл не передан"):
            convert_chat_audio(empty)

    def test_convert_chat_audio_rejects_long_recording(self):
        with self.assertRaisesMessage(ValueError, "длиннее 60"):
            convert_chat_audio(self.audio_file(seconds=62))

    def test_convert_chat_audio_rejects_non_audio_file(self):
        fake = SimpleUploadedFile(
            "note.txt", b"not audio", content_type="text/plain"
        )
        with self.assertRaisesMessage(ValueError, "не является аудио"):
            convert_chat_audio(fake)

    def test_guest_audio_upload_creates_message(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                self.client.post(reverse("chat:start"))
                response = self.client.post(
                    reverse("chat:upload"),
                    {
                        "client_id": str(uuid.uuid4()),
                        "audio": self.audio_file(seconds=2),
                    },
                )
                self.assertEqual(response.status_code, 200)
                message = Message.objects.get()
                self.assertTrue(message.audio.name.endswith(".mp3"))
                self.assertEqual(message.audio_duration, 2)
                payload = response.json()["message"]
                self.assertEqual(payload["audio"][-4:], ".mp3")
                self.assertEqual(payload["audio_duration"], 2)

    def test_guest_audio_upload_accepts_webm_without_duration(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                self.client.post(reverse("chat:start"))
                response = self.client.post(
                    reverse("chat:upload"),
                    {
                        "client_id": str(uuid.uuid4()),
                        "audio": self.webm_audio_file(seconds=2),
                    },
                )
                self.assertEqual(response.status_code, 200, response.content)
                message = Message.objects.get()
                self.assertTrue(message.audio.name.endswith(".mp3"))
                self.assertEqual(message.audio_duration, 2)
                self.assertGreater(message.audio.size, 0)

    def test_operator_audio_upload_creates_staff_message(self):
        staff = self.make_user("staff-audio", is_staff=True)
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
                        "audio": self.audio_file(),
                    },
                )
                self.assertEqual(response.status_code, 200)
                message = Message.objects.get()
                self.assertTrue(message.is_staff)
                self.assertTrue(message.audio.name.endswith(".mp3"))

    def test_operator_audio_upload_accepts_webm_without_duration(self):
        staff = self.make_user("staff-webm", is_staff=True)
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
                        "audio": self.webm_audio_file(seconds=2),
                    },
                )
                self.assertEqual(response.status_code, 200, response.content)
                message = Message.objects.get()
                self.assertTrue(message.is_staff)
                self.assertTrue(message.audio.name.endswith(".mp3"))
                self.assertEqual(message.audio_duration, 2)
                self.assertGreater(message.audio.size, 0)

    def test_audio_upload_requires_open_chat(self):
        response = self.client.post(
            reverse("chat:upload"),
            {"client_id": str(uuid.uuid4()), "audio": self.audio_file()},
        )
        self.assertEqual(response.status_code, 403)

    def test_summary_previews_audio_message(self):
        message = Message.objects.create(
            conversation=self.conversation,
            audio=SimpleUploadedFile(
                "voice.mp3", b"fake-audio", content_type="audio/mpeg"
            ),
        )
        summary_data = summary(self.conversation, message)
        self.assertEqual(summary_data["last_text"], "🎤 Голосовое сообщение")
        self.assertTrue(summary_data["has_audio"])

    def test_cleanup_deletes_message_audio_file(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                conversation = Conversation.objects.create()
                message = Message.objects.create(
                    conversation=conversation,
                    audio=SimpleUploadedFile(
                        "voice.mp3", b"fake-audio", content_type="audio/mpeg"
                    ),
                )
                path = message.audio.path
                self.assertTrue(os.path.exists(path))

                conversation.delete()

                self.assertFalse(os.path.exists(path))
