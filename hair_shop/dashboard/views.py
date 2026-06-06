# убери повторы импортов
from django.utils import timezone
from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import models
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect
from shop.models import Product, Order, OrderItem, ProductHairShade
from notifications.models import ChatSession, ChatMessage


from django.http import JsonResponse

from django.contrib.postgres.search import TrigramSimilarity

import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
# from users.models import (
#     User,
# )  # Оставил, если используете напрямую вместо get_user_model

import json
import os

from django.db import models as db_models
from django.views import View
from django_q.tasks import async_task

from shop.models import ProductImage
from .forms import ProductForm


User = get_user_model()
is_manager = lambda u: u.is_staff


class AdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "dashboard/admin_area.html"

    # Проверка, что зашел именно админ/стафф
    def test_func(self):
        return self.request.user.is_superuser

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     # Собираем данные из разных приложений
    #     context['total_products'] = Product.objects.count()
    #     context['total_users'] = User.objects.count()
    #     context['total_favorites'] = Favorite.objects.count()
    #     return context


# ── Миксин для проверки is_superuser ──────────────────────────────────────────
class SuperuserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser


def superuser_required(view_func):
    """Декоратор для function-based views"""
    decorated = login_required(user_passes_test(lambda u: u.is_superuser)(view_func))
    return decorated


# ── Шаг 1: Создание товара ────────────────────────────────────────────────────
class ProductCreateView(SuperuserRequiredMixin, View):
    template_name = "dashboard/product_form.html"

    def get(self, request):
        form = ProductForm()
        names = list(
            Product.objects.values_list("name", flat=True).distinct().order_by("name")
        )
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "title": "Добавить товар",
                "is_edit": False,
                "product_names_json": json.dumps(names, ensure_ascii=False),
                "shade_choices": Product.HAIR_SHADE,
            },
        )

    def post(self, request):
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            shades = request.POST.getlist("hair_shades")
            ProductHairShade.objects.filter(product=product).delete()
            for shade in shades:
                ProductHairShade.objects.create(product=product, shade=shade)
            return redirect("dashboard:product_media", pk=product.pk)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "title": "Добавить товар",
                "is_edit": False,
                "shade_choices": Product.HAIR_SHADE,
            },
        )


# ── Шаг 1: Редактирование товара ──────────────────────────────────────────────
class ProductEditView(SuperuserRequiredMixin, View):
    template_name = "dashboard/product_form.html"

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        form = ProductForm(instance=product)
        current_shades = list(product.hair_shades.values_list("shade", flat=True))
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "product": product,
                "title": f"Редактировать: {product.name}",
                "is_edit": True,
                "shade_choices": Product.HAIR_SHADE,
                "current_shades": current_shades,
            },
        )

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            shades = request.POST.getlist("hair_shades")
            ProductHairShade.objects.filter(product=product).delete()
            for shade in shades:
                ProductHairShade.objects.create(product=product, shade=shade)
            return redirect("dashboard:product_media", pk=product.pk)
        current_shades = list(product.hair_shades.values_list("shade", flat=True))
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "product": product,
                "title": f"Редактировать: {product.name}",
                "is_edit": True,
                "shade_choices": Product.HAIR_SHADE,
                "current_shades": current_shades,
            },
        )


# ── Шаг 1: Создание товара на основе существующего ───────────────────────────
class ProductCloneView(SuperuserRequiredMixin, View):
    template_name = "dashboard/product_form.html"

    def get(self, request, pk):
        source = get_object_or_404(Product, pk=pk)
        form = ProductForm(instance=source)
        # Очищаем артикул и выделяем поле
        form.initial["article"] = ""
        form.fields["article"].widget.attrs.update(
            {
                "autofocus": True,
                "placeholder": f"сменить !!!: {source.article}",
            }
        )
        current_shades = list(source.hair_shades.values_list("shade", flat=True))
        names = list(
            Product.objects.values_list("name", flat=True).distinct().order_by("name")
        )
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "title": f"Клонировать: {source.name}",
                "is_edit": False,
                "product_names_json": json.dumps(names, ensure_ascii=False),
                "shade_choices": Product.HAIR_SHADE,
                "current_shades": current_shades,
            },
        )

    def post(self, request, pk):
        # instance НЕ передаём — форма создаст новый объект
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            shades = request.POST.getlist("hair_shades")
            ProductHairShade.objects.filter(product=product).delete()
            for shade in shades:
                ProductHairShade.objects.create(product=product, shade=shade)
            return redirect("dashboard:product_media", pk=product.pk)

        source = get_object_or_404(Product, pk=pk)
        current_shades = request.POST.getlist("hair_shades") or list(
            source.hair_shades.values_list("shade", flat=True)
        )
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "title": f"Клонировать: {source.name}",
                "is_edit": False,
                "shade_choices": Product.HAIR_SHADE,
                "current_shades": current_shades,
            },
        )

    # ── Шаг 2: Страница медиа ─────────────────────────────────────────────────────


class ProductMediaView(SuperuserRequiredMixin, View):
    template_name = "dashboard/product_media.html"

    def get(self, request, pk):
        product = get_object_or_404(Product.objects.prefetch_related("images"), pk=pk)
        return render(
            request,
            self.template_name,
            {
                "product": product,
                "title": f"Медиа: {product.name}",
            },
        )


# ── AJAX: загрузка одного файла ───────────────────────────────────────────────
@superuser_required
@require_POST
def upload_product_media(request, pk):
    product = get_object_or_404(Product, pk=pk)
    file = request.FILES.get("file")
    if not file:
        return JsonResponse({"error": "Файл не передан"}, status=400)

    ext = os.path.splitext(file.name)[1].lower()
    is_video = ext in {".mp4", ".mov", ".avi", ".webm"}
    media_type = "video" if is_video else "image"

    last_order = (
        product.images.aggregate(max_order=db_models.Max("order"))["max_order"] or 0
    )

    obj = ProductImage(
        product=product,
        media_type=media_type,
        order=last_order + 1,
        status="pending",
    )
    if is_video:
        obj.video = file
    else:
        obj.image = file
    obj.save()

    if not is_video:
        async_task(
            "dashboard.tasks.compress_product_image",
            obj.pk,
            task_name=f"compress_image_{obj.pk}",
        )
    else:
        async_task(
            "dashboard.tasks.compress_product_video",
            obj.pk,
            task_name=f"compress_video_{obj.pk}",
        )

    return JsonResponse(
        {
            "id": obj.pk,
            "media_type": media_type,
            "status": obj.status,
            "preview_url": obj.preview_url,
        }
    )


# ── AJAX: новый порядок файлов ────────────────────────────────────────────────
@superuser_required
@require_POST
def reorder_product_media(request, pk):
    try:
        data = json.loads(request.body)
        ids = data.get("order", [])
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({"error": "Неверный формат"}, status=400)

    for index, media_id in enumerate(ids):
        ProductImage.objects.filter(pk=media_id, product_id=pk).update(order=index)

    return JsonResponse({"ok": True})


# ── AJAX: удаление файла ──────────────────────────────────────────────────────
@superuser_required
@require_POST
def delete_product_media(request, media_id):
    obj = get_object_or_404(ProductImage, pk=media_id)
    for field in (obj.image, obj.image_compressed, obj.video):
        if field:
            field.delete(save=False)
    obj.delete()
    return JsonResponse({"ok": True})


# ── AJAX: статус обработки одного файла (HTMX polling) ───────────────────────
@superuser_required
def media_status(request, media_id):
    obj = get_object_or_404(ProductImage, pk=media_id)
    return JsonResponse({"status": obj.status, "preview_url": obj.preview_url})


# ── HTMX: частичный шаблон одного медиа-элемента ─────────────────────────────
@superuser_required
def media_item_partial(request, media_id):
    obj = get_object_or_404(ProductImage, pk=media_id)
    return render(request, "dashboard/partials/media_item.html", {"media": obj})


# ─────────────────────────────────────────────────────────────
# Вспомогательная функция — рендерит partial карточки
# ─────────────────────────────────────────────────────────────


def _card_response(request, order):
    order = (
        Order.objects.select_related("user", "assigned_manager")
        .prefetch_related("items__product__images")
        .get(pk=order.pk)
    )
    managers = User.objects.filter(is_staff=True)
    return render(
        request,
        "dashboard/partials/_order_card.html",
        {
            "order": order,
            "managers": managers,
            "is_superuser": request.user.is_superuser,
        },
    )


# ─────────────────────────────────────────────────────────────
# Главная страница
# ─────────────────────────────────────────────────────────────


@login_required
@user_passes_test(is_manager)
def manage_orders(request):
    orders = (
        Order.objects.filter(is_archived=False)  # ← добавить
        .select_related("user", "assigned_manager")
        .prefetch_related("items__product__images")
        .order_by("-created_at")
    )
    managers = User.objects.filter(is_staff=True)

    if request.user.is_superuser:
        # Суперюзер: смотрит сессию — выбран ли конкретный менеджер
        active_manager_id = request.session.get("active_manager_id")
        active_manager = (
            managers.filter(id=active_manager_id).first() if active_manager_id else None
        )
        if active_manager:
            orders = orders.filter(assigned_manager=active_manager)
        # если active_manager = None — видит все заказы
    else:
        # Обычный менеджер — только свои заказы
        active_manager = request.user
        orders = orders.filter(
            models.Q(assigned_manager=request.user) | models.Q(assigned_manager=None)
        )

    return render(
        request,
        "dashboard/manage_orders.html",
        {
            "title": "Управление заказами",
            "orders": orders,
            "managers": managers,
            "active_manager": active_manager,
            "is_superuser": request.user.is_superuser,
        },
    )


# ─────────────────────────────────────────────────────────────
# Переключение активного менеджера (только для суперюзера)
# ─────────────────────────────────────────────────────────────


@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def set_active_manager(request):
    manager_id = request.POST.get("manager_id")
    if manager_id:
        request.session["active_manager_id"] = int(manager_id)
    else:
        request.session.pop("active_manager_id", None)
    # HX-Refresh перезагружает всю страницу через HTMX
    from django.http import HttpResponse

    return HttpResponse(status=204, headers={"HX-Refresh": "true"})


# ─────────────────────────────────────────────────────────────
# Назначить менеджера на заказ
# ─────────────────────────────────────────────────────────────


@login_required
@user_passes_test(is_manager)
@require_POST
def order_assign(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if not order.assigned_manager:
        if request.user.is_superuser:
            # Суперюзер назначает выбранного менеджера из select
            manager_id = request.POST.get("manager_id")
            manager = get_object_or_404(User, id=manager_id, is_staff=True)
        else:
            # Обычный менеджер берёт себе
            manager = request.user
        order.assigned_manager = manager
        order.status = "confirmed"
        order.save(update_fields=["assigned_manager", "status", "updated_at"])
    return _card_response(request, order)


# ─────────────────────────────────────────────────────────────
# Галочка «товар собран»
# ─────────────────────────────────────────────────────────────


@login_required
@user_passes_test(is_manager)
@require_POST
def order_item_toggle(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id)
    item.is_collected = not item.is_collected
    item.save(update_fields=["is_collected"])
    order = Order.objects.get(pk=item.order_id)
    return _card_response(request, order)


# ─────────────────────────────────────────────────────────────
# Статус → «В обработке»  (все товары должны быть собраны)
# ─────────────────────────────────────────────────────────────


@login_required
@user_passes_test(is_manager)
@require_POST
def order_set_processing(request, order_id):
    order = get_object_or_404(Order.objects.prefetch_related("items"), id=order_id)
    if not order.items.filter(is_collected=False).exists():
        order.status = "processing"
        order.save(update_fields=["status", "updated_at"])
    return _card_response(request, order)


# ─────────────────────────────────────────────────────────────
# Статус → «Отправлен»  (+ опциональный трек-номер)
# ─────────────────────────────────────────────────────────────


@login_required
@user_passes_test(is_manager)
@require_POST
def order_ship(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    tracking = request.POST.get("tracking_number", "").strip()
    if tracking:
        order.tracking_number = tracking
    order.status = "shipped"
    order.save(update_fields=["status", "tracking_number", "updated_at"])
    return _card_response(request, order)


# ─────────────────────────────────────────────────────────────
# Статус → «Доставлен»
# ─────────────────────────────────────────────────────────────


@login_required
@user_passes_test(is_manager)
@require_POST
def order_deliver(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.status = "delivered"
    order.delivered_at = timezone.now()
    order.save(update_fields=["status", "delivered_at", "updated_at"])
    return _card_response(request, order)


# ─────────────────────────────────────────────────────────────
# Отменить заказ
# ─────────────────────────────────────────────────────────────


@login_required
@user_passes_test(is_manager)
@require_POST
def order_cancel(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if order.status not in ("delivered", "shipped"):
        order.status = "cancelled"
        order.save(update_fields=["status", "updated_at"])
    return _card_response(request, order)


# ─────────────────────────────────────────────────────────────
# Webhook от платёжной системы
# ─────────────────────────────────────────────────────────────


@require_POST
def order_payment_webhook(request, order_id):
    # Раскомментируй и настрой проверку подписи под свою платёжку:
    # secret = request.headers.get('X-Webhook-Secret')
    # if secret != settings.PAYMENT_WEBHOOK_SECRET:
    #     return JsonResponse({'ok': False}, status=403)

    order = get_object_or_404(Order, id=order_id)
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "invalid json"}, status=400)

    new_status = body.get("payment_status")
    if new_status in dict(Order.PAYMENT_STATUS_CHOICES):
        order.payment_status = new_status
        order.save(update_fields=["payment_status", "updated_at"])
        return JsonResponse({"ok": True})

    return JsonResponse({"ok": False, "error": "unknown status"}, status=400)


@login_required
@user_passes_test(is_manager)
@require_POST
def order_archive(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if order.status == "delivered" and order.payment_status == "paid":
        order.is_archived = True
        order.save(update_fields=["is_archived", "updated_at"])
    # Возвращаем пустой div — карточка исчезает со страницы
    from django.http import HttpResponse

    return HttpResponse(f'<div id="order-{order.id}"></div>')


@login_required
@user_passes_test(is_manager)
def archived_orders(request):
    orders = (
        Order.objects.filter(is_archived=True)
        .select_related("user", "assigned_manager")
        .prefetch_related("items__product__images")
        .order_by("-updated_at")
    )
    return render(
        request,
        "dashboard/archived_orders.html",
        {
            "title": "Архив заказов",
            "orders": orders,
        },
    )


@login_required
@user_passes_test(is_manager)
def archive_order_card(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related("user", "assigned_manager").prefetch_related(
            "items__product__images"
        ),
        id=order_id,
    )
    return render(request, "dashboard/archive_order_card.html", {"order": order})


# поиск по артикулу


class ProductSearchView(SuperuserRequiredMixin, View):
    def get(self, request):
        query = request.GET.get("q", "").strip()
        products = []

        if query:
            products = (
                Product.objects.annotate(similarity=TrigramSimilarity("article", query))
                .filter(similarity__gt=0.45)
                .order_by("-similarity")
            )

        return render(
            request,
            "dashboard/product_search.html",
            {
                "products": products,
                "query": query,
            },
        )

    # admin_chat view — добавить отдельным url /admin-chat/<session_id>/


@login_required
def admin_chat_view(request, session_id):
    if not request.user.is_staff:
        return redirect("/")
    session = get_object_or_404(ChatSession, id=session_id)
    return render(request, "dashboard/admin_chat.html", {"session": session})


# Кнопка "Запросить фото" — отдельный endpoint
@login_required
@require_POST
def request_photo(request, session_id):
    if not request.user.is_staff:
        return JsonResponse({"error": "forbidden"}, status=403)
    session = get_object_or_404(ChatSession, id=session_id)
    ChatMessage.objects.create(
        session=session,
        sender="admin",
        msg_type="photo_request",
        text="Пожалуйста, пришлите фото для подбора оттенка",
    )
    return JsonResponse({"status": "ok"})
    # сигнал сам отправит push клиенту


@login_required
def chat_list(request):
    if not request.user.is_staff:
        return redirect("/")

    sessions = (
        ChatSession.objects.filter(is_active=True)
        .select_related("client")
        .order_by("-created_at")
    )

    from django.db.models import Count, Q

    sessions = sessions.annotate(
        unread_count=Count(
            "messages", filter=Q(messages__sender="client", messages__is_read=False)
        )
    )

    total_unread = sum(s.unread_count for s in sessions)

    return render(
        request,
        "dashboard/chat_list.html",
        {
            "sessions": sessions,
            "total_unread": total_unread,
        },
    )


@login_required
def admin_chat(request, session_id):
    if not request.user.is_staff:
        return redirect("/")
    session = get_object_or_404(ChatSession, id=session_id)

    # помечаем все сообщения от клиента как прочитанные
    session.messages.filter(sender="client", is_read=False).update(is_read=True)

    return render(request, "dashboard/admin_chat.html", {"session": session})


@login_required
@require_POST
def close_session(request, session_id):
    if not request.user.is_staff:
        return JsonResponse({"error": "forbidden"}, status=403)
    session = get_object_or_404(ChatSession, id=session_id)
    session.is_active = False
    session.save()
    return JsonResponse({"status": "ok"})


# ВСПОМОГАТЕЛЬНЫЕ ФУНЦИИ, МОЖНО УДАЛИТЬ ПОТОМ

# функция для заполнения поля hair_length у товар, где поле отсутствует, исключая категорию"ободки" через шаблон html
# views.py


# @staff_member_required
# def update_hair_length_view(request):
#     products_without_hair_length = (
#         Product.objects.filter(hair_length__isnull=True)
#         .exclude(category__name__icontains="ободк")
#         .prefetch_related(
#             Prefetch(
#                 "images",
#                 queryset=ProductImage.objects.filter(
#                     media_type="image",
#                 ).order_by("order", "id"),
#                 to_attr="prefetched_images",
#             )
#         )
#         .order_by("id")
#     )

#     if request.method == "POST":
#         product_id = request.POST.get("product_id")
#         hair_length = request.POST.get("hair_length")

#         # HTMX-запрос → отвечаем JSON
#         if request.headers.get("HX-Request"):
#             if not product_id or not hair_length:
#                 return JsonResponse({"ok": False, "error": "Нет данных"}, status=400)
#             try:
#                 product = Product.objects.get(id=product_id)
#                 product.hair_length = int(hair_length)
#                 product.save()
#                 return JsonResponse(
#                     {
#                         "ok": True,
#                         "message": f'"{product.name}" → {hair_length} см',
#                     }
#                 )
#             except Product.DoesNotExist:
#                 return JsonResponse(
#                     {"ok": False, "error": "Товар не найден"}, status=404
#                 )
#             except ValueError:
#                 return JsonResponse(
#                     {"ok": False, "error": "Некорректное значение"}, status=400
#                 )

#         # Обычный POST (без HTMX) — старый путь через messages + redirect
#         if product_id and hair_length:
#             try:
#                 product = Product.objects.get(id=product_id)
#                 product.hair_length = int(hair_length)
#                 product.save()
#                 messages.success(request, f'✅ "{product.name}" → {hair_length} см')
#             except Product.DoesNotExist:
#                 messages.error(request, "❌ Товар не найден")
#             except ValueError:
#                 messages.error(request, "❌ Некорректное значение")

#         return redirect("dashboard:update_hair_length")

#     context = {
#         "products": products_without_hair_length,
#         "total_count": products_without_hair_length.count(),
#     }
#     return render(request, "dashboard/update_hair_length.html", context)


# @staff_member_required
# def update_hair_shade_view(request):
#     products_without_shade = (
#         Product.objects.filter(hair_shade="not_defined")
#         .exclude(category__name__icontains="ободк")
#         .prefetch_related(
#             Prefetch(
#                 "images",
#                 queryset=ProductImage.objects.filter(
#                     media_type="image",
#                 ).order_by("order", "id"),
#                 to_attr="prefetched_images",
#             )
#         )
#         .order_by("id")
#     )

#     if request.method == "POST":
#         if request.headers.get("HX-Request"):
#             product_id = request.POST.get("product_id")
#             hair_shade = request.POST.get("hair_shade")

#             if not product_id or not hair_shade:
#                 return JsonResponse({"ok": False, "error": "Нет данных"}, status=400)

#             # проверяем что значение допустимое
#             valid_values = [v for v, _ in Product.HAIR_SHADE]
#             if hair_shade not in valid_values:
#                 return JsonResponse(
#                     {"ok": False, "error": "Недопустимое значение"}, status=400
#                 )

#             try:
#                 product = Product.objects.get(id=product_id)
#                 product.hair_shade = hair_shade
#                 product.save()
#                 shade_label = dict(Product.HAIR_SHADE).get(hair_shade, hair_shade)
#                 return JsonResponse(
#                     {
#                         "ok": True,
#                         "message": f'"{product.name}" → {shade_label}',
#                     }
#                 )
#             except Product.DoesNotExist:
#                 return JsonResponse(
#                     {"ok": False, "error": "Товар не найден"}, status=404
#                 )

#         return redirect("dashboard:update_hair_shade")

#     context = {
#         "products": products_without_shade,
#         "total_count": products_without_shade.count(),
#         "shade_choices": Product.HAIR_SHADE,  # передаём в шаблон
#     }
#     return render(request, "dashboard/update_hair_shade.html", context)


# функция редактирования группы товаров, после переделал логику и она вообще не используется, но пускай лежит
# @staff_member_required
# def group_editor(request):
#     if request.method == "POST":
#         group_slug = request.POST.get("group_slug")
#         note = request.POST.get("note_for_manager", "").strip()
#         if group_slug:
#             updated = Product.objects.filter(group_slug=group_slug).update(
#                 note_for_manager=note
#             )
#             messages.success(
#                 request, f"Сохранено для {updated} товаров группы «{group_slug}»"
#             )
#         return redirect("dashboard:group_editor")

#     # Все товары с превью — один запрос
#     images_prefetch = Prefetch(
#         "images",
#         queryset=ProductImage.objects.filter(media_type="image").order_by("id"),
#         to_attr="prefetched_images",
#     )
#     products = (
#         Product.objects.select_related("category")
#         .prefetch_related(images_prefetch)
#         .order_by("group_slug", "article")
#     )

#     # Группируем в питоне — не делаем лишних запросов
#     groups = {}
#     for p in products:
#         slug = p.group_slug or "(без группы)"
#         if slug not in groups:
#             groups[slug] = {
#                 "group_slug": p.group_slug,
#                 "product_group": p.product_group,
#                 "note_for_manager": p.note_for_manager,  # берём у первого товара группы
#                 "products": [],
#             }
#         groups[slug]["products"].append(p)

#     return render(request, "dashboard/group_editor.html", {"groups": groups.values()})


# Поменяйте путь если модель Product живёт в другом приложении


@staff_member_required
def stock_sync(request):
    return render(request, "dashboard/stock_sync.html")


@staff_member_required
@require_http_methods(["POST"])
def stock_import(request):
    """
    Принимает .xlsx / .xls от Dropzone.
    Колонка A — name   (игнорируется)
    Колонка B — article
    Колонка C — stock
    Строка 1  — заголовок, пропускается.
    """
    uploaded = request.FILES.get("file")
    if not uploaded:
        return JsonResponse({"success": False, "error": "Файл не получен."}, status=400)

    if not uploaded.name.lower().endswith((".xlsx", ".xls")):
        return JsonResponse(
            {"success": False, "error": "Поддерживаются только .xlsx и .xls"},
            status=400,
        )

    try:
        wb = openpyxl.load_workbook(uploaded, read_only=True, data_only=True)
        ws = wb.active
    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"Не удалось открыть файл: {e}"}, status=400
        )

    updated, not_found, errors = 0, [], []

    for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or all(v is None for v in row):
            continue
        try:
            article = (
                str(row[1]).strip() if len(row) > 1 and row[1] is not None else None
            )
            stock = row[2] if len(row) > 2 else None

            if not article:
                errors.append(f"Строка {i}: пустой артикул")
                continue
            if stock is None:
                errors.append(f"Строка {i} ({article}): пустой остаток")
                continue
            try:
                stock_value = int(float(stock))
            except (ValueError, TypeError):
                errors.append(f"Строка {i} ({article}): некорректный остаток «{stock}»")
                continue

            count = Product.objects.filter(article=article).update(stock=stock_value)
            if count:
                updated += count
            else:
                not_found.append(article)

        except Exception as e:
            errors.append(f"Строка {i}: {e}")

    wb.close()
    return JsonResponse(
        {
            "success": True,
            "updated": updated,
            "not_found": not_found,
            "not_found_count": len(not_found),
            "errors": errors,
            "errors_count": len(errors),
        }
    )


@staff_member_required
def stock_export(request):
    """Выгружает остатки всех товаров в Excel."""
    products = (
        Product.objects.all().order_by("article").values("name", "article", "stock")
    )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Остатки"

    hdr_fill = PatternFill("solid", fgColor="0F2137")
    hdr_font = Font(bold=True, color="FFFFFF", size=11, name="Calibri")
    hdr_align = Alignment(horizontal="center", vertical="center")
    thin = Side(style="thin", color="D1D9E6")
    brd = Border(left=thin, right=thin, top=thin, bottom=thin)
    alt_fill = PatternFill("solid", fgColor="F3F6FA")

    for ci, (h, w) in enumerate(
        zip(["Наименование", "Артикул", "Остаток"], [42, 26, 12]), 1
    ):
        cell = ws.cell(row=1, column=ci, value=h)
        cell.font = hdr_font
        cell.fill = hdr_fill
        cell.alignment = hdr_align
        cell.border = brd
        ws.column_dimensions[get_column_letter(ci)].width = w
    ws.row_dimensions[1].height = 24

    for ri, p in enumerate(products, 2):
        for ci, val in enumerate(
            [p.get("name", ""), p.get("article", ""), p.get("stock", 0)], 1
        ):
            cell = ws.cell(row=ri, column=ci, value=val)
            cell.border = brd
            if ri % 2 == 0:
                cell.fill = alt_fill
            if ci == 3:
                cell.alignment = Alignment(horizontal="center")

    ws.freeze_panes = "A2"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    response = HttpResponse(
        buf.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="stock_export.xlsx"'
    return response


# class ShadeReviewView(SuperuserRequiredMixin, View):
#     template_name = "dashboard/shade_review.html"

#     def _get_next(self):
#         return (
#             Product.objects.filter(variants_reviewed=False)
#             .prefetch_related(
#                 Prefetch(
#                     "images",
#                     queryset=ProductImage.objects.filter(media_type="image").order_by(
#                         "order"
#                     ),
#                     to_attr="prefetched_images",
#                 )
#             )
#             .order_by("pk")
#             .first()
#         )

#     def get(self, request):
#         product = self._get_next()
#         remaining = Product.objects.filter(variants_reviewed=False).count()
#         total = Product.objects.count()
#         reviewed = total - remaining
#         progress_pct = round(reviewed / total * 100) if total else 0

#         current_shades = (
#             list(product.hair_shades.values_list("shade", flat=True)) if product else []
#         )

#         return render(
#             request,
#             self.template_name,
#             {
#                 "title": "Расстановка оттенков",
#                 "product": product,
#                 "remaining": remaining,
#                 "progress_pct": progress_pct,
#                 "shade_choices": Product.HAIR_SHADE,
#                 "current_shades": current_shades,
#             },
#         )

#     def post(self, request):
#         pk = request.POST.get("product_pk")
#         product = get_object_or_404(Product, pk=pk)
#         action = request.POST.get("action")

#         if action == "skip":
#             # просто помечаем как проверенный без изменения оттенков
#             product.variants_reviewed = True
#             product.save(update_fields=["variants_reviewed"])
#             return redirect("dashboard:shade_review")

#         shades = request.POST.getlist("hair_shades")
#         ProductHairShade.objects.filter(product=product).delete()
#         for shade in shades:
#             ProductHairShade.objects.create(product=product, shade=shade)
#         product.variants_reviewed = True
#         product.save(update_fields=["variants_reviewed"])
#         return redirect("dashboard:shade_review")
