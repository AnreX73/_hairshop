from unittest.mock import Mock, patch
from urllib.parse import quote

import requests
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.urls import resolve, reverse

from shop.context_processors import geo_prompt_context
from shop.geoip import normalize_location
from users.models import User

from .models import Cart, CartItem, Category, Product, VideoInstruction


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

# ── Определение города по IP ─────────────────────────────────────────────────

GEOIP_TEST_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}


def _dadata_payload(
    city="Иваново",
    region="Ивановская",
    kladr="3700000000000",
    postal="153000",
):
    return {
        "location": {
            "data": {
                "city": city,
                "settlement": None,
                "region": region,
                "region_kladr_id": kladr,
                "postal_code": postal,
            }
        }
    }


def _dadata_response(**kwargs):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = _dadata_payload(**kwargs)
    return response


class NormalizeLocationTests(TestCase):
    def test_extracts_city_data(self):
        self.assertEqual(
            normalize_location(_dadata_payload()),
            {
                "city": "Иваново",
                "region": "Ивановская",
                "region_code": "37",
                "postal_code": "153000",
            },
        )

    def test_uses_settlement_when_city_is_empty(self):
        payload = {
            "location": {
                "data": {
                    "city": None,
                    "settlement": "Красная Пахра",
                    "region": "Московская",
                    "region_kladr_id": "5000000000000",
                }
            }
        }

        self.assertEqual(normalize_location(payload)["city"], "Красная Пахра")

    def test_returns_none_without_location(self):
        self.assertIsNone(normalize_location({"location": None}))
        self.assertIsNone(normalize_location({}))


@override_settings(CACHES=GEOIP_TEST_CACHES)
class DetectCityViewTests(TestCase):
    url = "/api/geo/city/"

    def setUp(self):
        cache.clear()

    def test_returns_city_from_dadata(self):
        with patch(
            "shop.geoip.requests.post", return_value=_dadata_response()
        ) as post:
            response = self.client.get(self.url, REMOTE_ADDR="8.8.8.8")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "found": True,
                "city": "Иваново",
                "region": "Ивановская",
                "region_code": "37",
                "postal_code": "153000",
            },
        )
        post.assert_called_once()

    def test_result_is_cached_between_requests(self):
        with patch(
            "shop.geoip.requests.post", return_value=_dadata_response()
        ) as post:
            first = self.client.get(self.url, REMOTE_ADDR="8.8.8.8")
            second = self.client.get(self.url, REMOTE_ADDR="8.8.8.8")

        self.assertEqual(first.json()["city"], "Иваново")
        self.assertEqual(second.json()["city"], "Иваново")
        post.assert_called_once()

    def test_private_ip_skips_api(self):
        with patch("shop.geoip.requests.post") as post:
            response = self.client.get(self.url, REMOTE_ADDR="127.0.0.1")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["found"])
        post.assert_not_called()

    def test_dadata_error_is_silent(self):
        with patch(
            "shop.geoip.requests.post",
            side_effect=requests.RequestException("boom"),
        ):
            response = self.client.get(self.url, REMOTE_ADDR="8.8.8.8")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["found"])

    def test_empty_location_is_cached(self):
        with patch(
            "shop.geoip.requests.post",
            return_value=Mock(
                raise_for_status=Mock(return_value=None),
                json=Mock(return_value={"location": None}),
            ),
        ) as post:
            self.client.get(self.url, REMOTE_ADDR="8.8.8.8")
            second = self.client.get(self.url, REMOTE_ADDR="8.8.8.8")

        self.assertFalse(second.json()["found"])
        post.assert_called_once()


class RegisterGeoCityTests(TestCase):
    def register(self, extra=None):
        data = {
            "email": "geo@mail.ru",
            "password1": "Gfhjkm12345",
            "password2": "Gfhjkm12345",
        }
        if extra:
            data.update(extra)
        return self.client.post(reverse("users:register"), data)

    def test_geo_city_is_saved_to_profile(self):
        response = self.register({"geo_city": "  Иваново  "})

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email="geo@mail.ru")
        self.assertEqual(user.delivery_city, "Иваново")

    def test_cookie_is_used_as_fallback(self):
        self.client.cookies["hairshop_city"] = quote("Иваново")

        response = self.register({"geo_city": ""})

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email="geo@mail.ru")
        self.assertEqual(user.delivery_city, "Иваново")

    def test_existing_city_is_not_overwritten(self):
        from users.views import _apply_geo_city

        user = User.objects.create_user(
            username="existing@mail.ru",
            email="existing@mail.ru",
            password="Gfhjkm12345",
            delivery_city="Москва",
        )
        request = RequestFactory().post("/users/register/", {"geo_city": "Иваново"})

        _apply_geo_city(request, user)

        user.refresh_from_db()
        self.assertEqual(user.delivery_city, "Москва")


class GeoPromptContextTests(TestCase):
    def make_request(self, path, user=None):
        request = RequestFactory().get(path)
        request.user = user or AnonymousUser()
        request.resolver_match = resolve(path)
        return request

    def test_allowed_on_homepage(self):
        context = geo_prompt_context(self.make_request("/"))

        self.assertTrue(context["geo_prompt_allowed"])

    def test_not_allowed_on_login(self):
        context = geo_prompt_context(self.make_request("/users/login/"))

        self.assertFalse(context["geo_prompt_allowed"])

    def test_not_allowed_on_order_create(self):
        context = geo_prompt_context(self.make_request("/order-create/"))

        self.assertFalse(context["geo_prompt_allowed"])

    def test_not_allowed_for_authenticated_user(self):
        user = User.objects.create_user(
            username="user@mail.ru",
            email="user@mail.ru",
            password="Gfhjkm12345",
        )

        context = geo_prompt_context(self.make_request("/", user=user))

        self.assertFalse(context["geo_prompt_allowed"])


@override_settings(CACHES=GEOIP_TEST_CACHES)
class GeoPromptTemplateTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_prompt_markup_is_rendered_on_homepage(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="city-prompt"')
        self.assertContains(response, 'data-geo-enabled="1"')

    def test_prompt_is_not_rendered_on_login_page(self):
        response = self.client.get(reverse("users:login"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="city-prompt"')
        self.assertContains(response, 'data-geo-enabled="0"')


class OrderCreatePageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="order@mail.ru",
            email="order@mail.ru",
            password="Gfhjkm12345",
            first_name="Мария",
            last_name="Иванова",
            phone_number="+79991234567",
            delivery_city="Москва",
            delivery_address="ул. Тверская, д. 1",
            delivery_postal_code="125009",
        )
        self.client.force_login(self.user)

        category = Category.objects.create(name="Пряди", slug="pryadi")
        product = Product.objects.create(
            name="Пряди на заколках",
            article="ORDER-001",
            category=category,
            hair_length=60,
            price=5000,
            stock=10,
        )
        # Корзина создаётся сигналом post_save при регистрации пользователя.
        cart = Cart.objects.get(user=self.user)
        CartItem.objects.create(cart=cart, product=product, quantity=1)

        self.url = reverse("shop:order_create")

    def order_data(self, **overrides):
        data = {
            "first_name": "Мария",
            "last_name": "Иванова",
            "customer_email": "order@mail.ru",
            "customer_phone": "+79991234567",
            "delivery_city": "Москва",
            "delivery_address": "ул. Тверская, д. 1",
            "delivery_postal_code": "125009",
            "notes": "",
        }
        data.update(overrides)
        return data

    def test_profile_address_is_prefilled(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-initial-address="ул. Тверская, д. 1"')
        self.assertContains(response, 'value="ул. Тверская, д. 1"')

    def test_delivery_has_single_heading_and_clear_address_label(self):
        response = self.client.get(self.url)

        self.assertContains(response, "<legend>Доставка</legend>", html=True)
        self.assertContains(response, ">Адрес</label>")
        self.assertNotContains(response, "<legend>Адрес доставки</legend>", html=True)

    def test_submitted_address_survives_validation_error(self):
        response = self.client.post(
            self.url,
            self.order_data(customer_email="broken-email", delivery_address="Новый адрес, 5"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="Новый адрес, 5"')
        self.assertContains(response, 'id="form-errors"')

    def test_comment_is_outside_delivery_fieldset(self):
        response = self.client.get(self.url)
        content = response.content.decode()

        delivery = content.split("checkout-fieldset--delivery", 1)[1].split("</fieldset>", 1)[0]

        self.assertNotIn('name="notes"', delivery)
        self.assertContains(response, "<legend>Комментарий</legend>", html=True)

    def test_profile_values_are_truncated_to_model_limits(self):
        from shop.views import _update_profile_from_order

        _update_profile_from_order(
            self.user,
            {
                "first_name": "Мария",
                "last_name": "Иванова",
                "customer_phone": "+79991234567",
                "delivery_city": "Очень длинное название города " * 5,
                "delivery_address": "Очень длинный адрес доставки " * 10,
                "delivery_postal_code": "125009",
            },
        )

        self.user.refresh_from_db()
        self.assertLessEqual(len(self.user.delivery_city), 30)
        self.assertLessEqual(len(self.user.delivery_address), 100)
