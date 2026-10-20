from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from users.models import User

from .models import Category, Product, VideoInstruction


class VideoInstructionSeriesTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Пряди", slug="pryadi")
        self.other_category = Category.objects.create(name="Парики", slug="pariki")
        self.product = Product.objects.create(
            name="Пряди на заколках",
            article="A-001",
            category=self.category,
            hair_length=60,
        )
        self.sibling = Product.objects.create(
            name="Пряди на заколках",
            article="A-002",
            category=self.category,
            hair_length=60,
            stock=0,
            out_of_stock_behavior="hide",
        )
        self.other_length = Product.objects.create(
            name="Пряди на заколках",
            article="A-003",
            category=self.category,
            hair_length=70,
        )
        self.other_name = Product.objects.create(
            name="Пряди на ленте",
            article="A-004",
            category=self.category,
            hair_length=60,
        )

    def make_video(self, product, **kwargs):
        defaults = {
            "title": "Как закрепить",
            "product": product,
            "status": "done",
            "is_active": True,
            "apply_to_series": True,
        }
        defaults.update(kwargs)
        return VideoInstruction.objects.create(**defaults)

    def test_direct_and_series_videos_included(self):
        direct = self.make_video(self.product, apply_to_series=False)
        series = self.make_video(self.product)

        result = set(VideoInstruction.for_product(self.product))

        self.assertIn(direct, result)
        self.assertIn(series, result)

    def test_series_video_visible_on_sibling_without_stock(self):
        series = self.make_video(self.product)

        result = set(VideoInstruction.for_product(self.sibling))

        self.assertIn(series, result)

    def test_other_series_not_included(self):
        series = self.make_video(self.product)

        self.assertNotIn(series, VideoInstruction.for_product(self.other_length))
        self.assertNotIn(series, VideoInstruction.for_product(self.other_name))

    def test_only_direct_video_when_series_disabled(self):
        direct = self.make_video(self.product, apply_to_series=False)

        self.assertIn(direct, VideoInstruction.for_product(self.product))
        self.assertNotIn(direct, VideoInstruction.for_product(self.sibling))

    def test_inactive_and_unfinished_videos_hidden(self):
        self.make_video(self.product, is_active=False)
        self.make_video(self.product, status="processing")
        self.make_video(self.product, status="error")

        self.assertEqual(VideoInstruction.for_product(self.product).count(), 0)

    def test_product_page_context_contains_series_video(self):
        video = self.make_video(self.product)
        VideoInstruction.objects.filter(pk=video.pk).update(
            compressed_file="video_instructions/test.mp4"
        )
        video.refresh_from_db()

        response = self.client.get(
            reverse(
                "shop:product_page",
                args=[self.sibling.group_slug, self.sibling.id],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(video, response.context["video_instructions"])
        self.assertContains(response, video.title)
        self.assertContains(response, "video-instruction-cta")
        self.assertNotContains(response, "Есть видео-инструкция")
        self.assertNotContains(response, "video-instructions-grid")

    def test_product_page_without_videos_has_no_button(self):
        response = self.client.get(
            reverse(
                "shop:product_page",
                args=[self.product.group_slug, self.product.id],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "video-instruction-cta")


class VideoInstructionAdminTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Пряди", slug="pryadi")
        self.product = Product.objects.create(
            name="Пряди на заколках",
            article="B-001",
            category=self.category,
            hair_length=60,
        )
        self.superuser = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="secret123"
        )
        self.user = User.objects.create_user(
            username="manager", email="manager@example.com", password="secret123"
        )

    def upload(self, **overrides):
        data = {
            "title": "Инструкция",
            "description": "Короткое описание",
            "admin_note": "Проверить звук",
            "apply_to_series": "on",
            "is_active": "on",
        }
        data.update(overrides)
        data["file"] = SimpleUploadedFile(
            "instruction.mp4", b"fake-video-bytes", content_type="video/mp4"
        )
        return self.client.post(
            reverse("dashboard:upload_video_instruction", args=[self.product.pk]),
            data,
        )

    @patch("dashboard.tasks.async_task")
    def test_upload_requires_superuser(self, async_task):
        self.client.force_login(self.user)
        response = self.upload()

        self.assertEqual(response.status_code, 302)
        self.assertFalse(VideoInstruction.objects.exists())
        async_task.assert_not_called()

    @patch("dashboard.tasks.async_task")
    def test_superuser_upload_creates_video_and_schedules_compression(
        self, async_task
    ):
        self.client.force_login(self.superuser)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.upload()

        self.assertEqual(response.status_code, 200)
        video = VideoInstruction.objects.get()
        self.assertEqual(video.title, "Инструкция")
        self.assertEqual(video.status, "pending")
        self.assertTrue(video.apply_to_series)
        async_task.assert_called_once()

    def test_product_videos_page_available_for_superuser(self):
        self.client.force_login(self.superuser)

        response = self.client.get(
            reverse("dashboard:product_videos", args=[self.product.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Новое видео")
        self.assertContains(response, "Видео-инструкции")

    def test_admin_and_public_navigation_render(self):
        self.client.force_login(self.superuser)

        for url in (
            reverse("dashboard:admin_area"),
            reverse("dashboard:video_instructions"),
            reverse("dashboard:product_videos", args=[self.product.pk]),
            self.product.get_absolute_url(),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

    def test_video_list_page_search_and_status_filter(self):
        VideoInstruction.objects.create(
            title="Готовое видео",
            product=self.product,
            status="done",
            compressed_file="video_instructions/ready.mp4",
        )
        VideoInstruction.objects.create(
            title="Видео в очереди",
            product=self.product,
            status="pending",
        )
        self.client.force_login(self.superuser)
        url = reverse("dashboard:video_instructions")

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Готовое видео")
        self.assertContains(response, "Видео в очереди")
        self.assertContains(response, self.product.article)

        response = self.client.get(url, {"status": "pending"})
        self.assertContains(response, "Видео в очереди")
        self.assertNotContains(response, "Готовое видео")

        response = self.client.get(url, {"q": self.product.article})
        self.assertContains(response, "Готовое видео")

        response = self.client.get(url, {"q": "несуществующий-артикул"})
        self.assertContains(response, "видео не найдено")

    def test_video_list_pagination(self):
        for index in range(31):
            VideoInstruction.objects.create(
                title=f"Видео {index}",
                product=self.product,
                status="pending",
            )
        self.client.force_login(self.superuser)

        response = self.client.get(
            reverse("dashboard:video_instructions"), {"page": 2}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["videos"].number, 2)
        self.assertContains(response, "Страница 2 из 2")

    def test_video_list_requires_superuser(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashboard:video_instructions"))

        self.assertEqual(response.status_code, 403)

    @patch("dashboard.tasks.async_task")
    def test_invalid_extension_rejected(self, async_task):
        self.client.force_login(self.superuser)
        response = self.client.post(
            reverse("dashboard:upload_video_instruction", args=[self.product.pk]),
            {
                "title": "Инструкция",
                "file": SimpleUploadedFile(
                    "instruction.txt", b"not-a-video", content_type="text/plain"
                ),
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(VideoInstruction.objects.exists())
        async_task.assert_not_called()

    def test_update_metadata(self):
        video = VideoInstruction.objects.create(
            title="Старое название",
            product=self.product,
            status="done",
        )
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse("dashboard:update_video_instruction", args=[video.pk]),
            {
                "title": "Новое название",
                "description": "Обновлено",
                "admin_note": "",
                "apply_to_series": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        video.refresh_from_db()
        self.assertEqual(video.title, "Новое название")
        self.assertTrue(video.is_active is False)
        self.assertTrue(video.apply_to_series)
