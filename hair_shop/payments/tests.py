from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from shop.models import Info, Order
from users.models import User


class OrderPaymentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="buyer@example.com",
            email="buyer@example.com",
            password="test-pass-123",
        )
        self.client.force_login(self.user)
        Info.objects.create(
            slug="atantion",
            title="Внимание",
            content="Проверьте заказ перед оплатой.",
        )

    def make_order(self, **kwargs):
        defaults = {
            "user": self.user,
            "subtotal": 1000,
            "delivery_cost": 0,
            "total": 1000,
            "customer_name": "Иван Иванов",
            "customer_email": "buyer@example.com",
            "customer_phone": "+79990000000",
            "delivery_address": "ул. Тестовая, 1",
            "delivery_city": "Москва",
            "delivery_postal_code": "101000",
        }
        defaults.update(kwargs)
        return Order.objects.create(**defaults)

    def test_pending_order_has_payment_link(self):
        order = self.make_order(payment_status="pending")

        response = self.client.get(reverse("users:profile"))

        self.assertContains(response, "Оплатить 1000 ₽")
        self.assertContains(
            response, reverse("payments:create_payment", args=[order.id])
        )

    def test_failed_order_has_retry_payment_link(self):
        self.make_order(payment_status="failed")

        response = self.client.get(reverse("users:profile"))

        self.assertContains(response, "Повторить оплату")

    def test_paid_order_has_no_payment_link(self):
        order = self.make_order(payment_status="paid")

        response = self.client.get(reverse("users:profile"))

        self.assertNotContains(
            response, reverse("payments:create_payment", args=[order.id])
        )

    def test_cancelled_order_has_no_payment_link(self):
        order = self.make_order(payment_status="pending", status="cancelled")

        response = self.client.get(reverse("users:profile"))

        self.assertNotContains(
            response, reverse("payments:create_payment", args=[order.id])
        )

    @patch("payments.views.YookassaPayment.create")
    def test_create_payment_does_not_charge_paid_order(self, create_payment):
        order = self.make_order(payment_status="paid")

        response = self.client.get(
            reverse("payments:create_payment", args=[order.id])
        )

        create_payment.assert_not_called()
        self.assertRedirects(
            response,
            f"{reverse('users:profile')}?tab=4",
            fetch_redirect_response=False,
        )

    @patch("payments.views.YookassaPayment.create")
    def test_retry_payment_resets_failed_status(self, create_payment):
        payment = create_payment.return_value
        payment.id = "yookassa-payment-1"
        payment.confirmation.confirmation_url = "https://yookassa.test/pay"
        order = self.make_order(payment_status="failed")

        response = self.client.get(
            reverse("payments:create_payment", args=[order.id])
        )

        create_payment.assert_called_once()
        self.assertRedirects(
            response,
            "https://yookassa.test/pay",
            fetch_redirect_response=False,
        )
        order.refresh_from_db()
        self.assertEqual(order.payment_status, "pending")
