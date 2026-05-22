from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.db.models import Q
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.template.loader import render_to_string
from .forms import OrderForm, ReviewForm, SmartSearchProductForm
from django.db.models import Min, Max, ExpressionWrapper, F, IntegerField

from django.contrib import messages

from .models import (
    Category,
    Product,
    ProductImage,
    SiteAssets,
    Favorite,
    CartItem,
    Cart,
    Order,
    OrderItem,
    Review,
    ReviewMedia,
    Contact,
    Info,
)
import os
from django.http import JsonResponse
from django_q.tasks import async_task
from django.db import models as db_models


def get_hit_ids():
    from django.core.cache import cache

    hit_ids = cache.get("hit_product_ids")
    if hit_ids is None:
        hit_ids = set(
            Product.objects.order_by("-popularity").values_list("id", flat=True)[:24]
        )
        cache.set("hit_product_ids", hit_ids, timeout=3600)
    return hit_ids


def index(request):
    # Проверяем кэш
    cache_key = "site_assets_homepage"
    cached_data = cache.get(cache_key)
    categories = Category.objects.all()
    contacts = Contact.objects.filter(is_active=True)
    # hit_products = Product.objects.filter(is_hit=True).prefetch_related('images').order_by('-popularity')[:12]
    hit_products = (
        Product.objects.all()
        .prefetch_related(
            Prefetch(
                "images",
                queryset=ProductImage.objects.filter(media_type="image"),
                to_attr="prefetched_images",
            )
        )
        .order_by("-popularity")
        .distinct("popularity")[:12]
    )
    info_objects = Info.objects.all()
    info = info_objects.exclude(slug="start_banner")
    start_banner = info_objects.filter(slug="start_banner").first()
    if cached_data:
        context = cached_data
    else:
        try:
            # Один запрос для всех объектов
            assets = SiteAssets.objects.filter(
                Q(
                    site_assets_name__in=[
                        "logo",
                        "logo_text",
                        "slogan",
                        "cart_icon",
                        "account_icon",
                    ]
                )
                | Q(note="advantages")
            )

            # Формируем контекст
            context = {"title": "Студия НР", "advantages": []}
            for asset in assets:
                if asset.note == "advantages":
                    context["advantages"].append(asset)
                elif asset.site_assets_name:
                    context[asset.site_assets_name] = asset

            # Кэшируем на 1 час
            cache.set(cache_key, context, 600)

        except Exception:
            # Обработка ошибок
            context = {"title": "Главная", "error": "Не удалось загрузить данные сайта"}

    context["categories"] = categories
    context["hit_products"] = hit_products
    context["contacts"] = {c.slug: c for c in contacts}
    context["start_banner"] = start_banner
    context["info"] = info
    context["hit_ids"] = get_hit_ids()

    return render(request, "shop/index.html", context)


def catalog(request):
    data = request.GET.copy()
    hx_trigger = request.headers.get("HX-Trigger-Name", "")
    # Сбрасываем длины только при смене категории, не при движении слайдера
    if hx_trigger == 'id_category':
        data.pop('hair_length_min', None)
    form = SmartSearchProductForm(data or None)

    images_prefetch = Prefetch(
        "images",
        queryset=ProductImage.objects.filter(media_type="image").order_by("order"),
        to_attr="prefetched_images",
    )

    # Базовый queryset
    products = Product.objects.filter(
        Q(stock__gt=0) | Q(out_of_stock_behavior="show")
    ).annotate(
        computed_final_price=ExpressionWrapper(
            F("price") * (1 - F("discount_percentage") / 100.0),
            output_field=IntegerField(),
        )
    )

    # Фильтры по категории и оттенку
    if form.is_valid():
        if category := form.cleaned_data.get("category"):
            products = products.filter(category=category)
        if hair_shade := form.cleaned_data.get("hair_shade"):
            products = products.filter(hair_shade=hair_shade)

    # Диапазон цен считаем ДО фильтра по цене
    price_agg = products.aggregate(
        min_price=Min("computed_final_price"),
        max_price=Max("computed_final_price"),
    )
    min_price = price_agg["min_price"] or 0
    max_price = price_agg["max_price"] or 10000

    # Фильтр по цене
    if form.is_valid():
        if max_price_filter := form.cleaned_data.get("final_price"):
            products = products.filter(computed_final_price__lte=max_price_filter)

    # Диапазон длин считаем ДО фильтра по длине
    length_agg = products.filter(hair_length__isnull=False).aggregate(
        min_length=Min("hair_length"),
        max_length=Max("hair_length"),
    )
    min_length = length_agg["min_length"] or 0
    max_length = length_agg["max_length"] or 100
    has_length_filter = (
        length_agg["min_length"] is not None
        and bool(form.cleaned_data.get("category") if form.is_valid() else None)
    )

    # Фильтр по длине
    if form.is_valid() and has_length_filter:
        if min_l := form.cleaned_data.get("hair_length_min"):
            products = products.filter(
                Q(hair_length__gte=min_l) | Q(hair_length__isnull=True)
            )


    # Prefetch и сортировка
    products = products.prefetch_related(images_prefetch).order_by("-popularity").distinct("popularity")

    # Пагинация
    # Пагинация — сбрасываем на 1 только если изменился именно фильтр,
    # а не просто пришёл запрос с фильтрами + page
    filter_keys = {"category", "hair_shade", "final_price", "hair_length_min"}
    is_filter_change = (
        any(k in request.GET for k in filter_keys) and "page" not in request.GET
    )

    if is_filter_change:
        page_number = 1
    else:
        page_number = request.GET.get("page", 1)
        request.session["catalog_last_page"] = page_number

    paginator = Paginator(products, 20)
    page_obj = paginator.get_page(page_number)

    hit_ids = get_hit_ids()

    # Атрибуты слайдера цены
    form.fields["final_price"].widget.attrs["min"] = min_price
    form.fields["final_price"].widget.attrs["max"] = max_price
    current_price_value = (
        form.cleaned_data.get("final_price")
        if form.is_valid() and form.cleaned_data.get("final_price")
        else max_price
    )
    form.fields["final_price"].widget.attrs["value"] = current_price_value

    # Атрибуты слайдера длины ← добавь сюда
    form.fields["hair_length_min"].widget.attrs["min"] = min_length
    form.fields["hair_length_min"].widget.attrs["max"] = max_length
    current_length_value = (
        form.cleaned_data.get("hair_length_min")
        if form.is_valid() and form.cleaned_data.get("hair_length_min")
        else min_length
    )
    form.fields["hair_length_min"].widget.attrs["value"] = current_length_value
    context = {
    "form": form,
    "page_obj": page_obj,
    "hit_ids": hit_ids,
    "min_price": min_price,
    "max_price": max_price,
    "current_price": current_price_value,
    "min_length": min_length,
    "max_length": max_length,
    "has_length_filter": has_length_filter,
    "current_get_params": request.GET.copy(),
}

    is_htmx = bool(request.headers.get("HX-Request"))
    show_length_oob = hx_trigger != "hair_length_min" and is_htmx
    context["show_length_oob"] = show_length_oob

    if request.headers.get("HX-Request"):
        return render(request, "shop/includes/catalog_results.html", context)

    return render(request, "shop/catalog.html", context)


def product_page(request, slug, product_id):
    product = get_object_or_404(
        Product.objects.select_related("category").defer("created_at", "updated_at"),
        id=product_id,
    )

    product_gallery = ProductImage.objects.filter(product=product).order_by(
        "-created_at"
    )
    video_poster = product_gallery.filter(media_type="image").first()

    images_prefetch = Prefetch(
        "images",
        queryset=ProductImage.objects.filter(media_type="image").order_by("order"),
        to_attr="prefetched_images",
    )
    reviews = Review.objects.filter(product=product, is_approved=True).prefetch_related(
        "media"
    )

    related_products = (
        Product.objects.filter(
            category=product.category,
            name=product.name,
            hair_length=product.hair_length,  # None == None — работает корректно
        )
        .exclude(id=product_id)
        .select_related("category")
        .prefetch_related(images_prefetch)
    )

    return render(
        request,
        "shop/product_page.html",
        {
            "product": product,
            "product_gallery": product_gallery,
            "video_poster": video_poster,
            "related_products": related_products,
            "reviews": reviews,
            "hit_ids": get_hit_ids(),
        },
    )


@login_required
@require_POST
def toggle_favorite(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    # Получаем желаемое состояние из Alpine (приходит строкой 'true' или 'false')
    is_favorite_requested = request.POST.get("is_favorite") == "true"

    if is_favorite_requested:
        # Пытаемся создать запись, если её еще нет
        Favorite.objects.get_or_create(user=request.user, product=product)
    else:
        # Удаляем запись, если она существует
        Favorite.objects.filter(user=request.user, product=product).delete()

    return HttpResponse(status=204)  # Успешно, без смены контента


@login_required
@require_POST
def toggle_cart(request, product_id):
    product = Product.objects.get(pk=product_id)
    cart, _ = Cart.objects.get_or_create(user=request.user)

    is_cart = request.POST.get("is_cart") == "true"

    if is_cart:
        CartItem.objects.get_or_create(cart=cart, product=product)
    else:
        CartItem.objects.filter(cart=cart, product=product).delete()

    # Обновляем счётчик в иконке через OOB swap
    cart_count = cart.total_items
    return HttpResponse(
        f'<span id="cart-counter" hx-swap-oob="true" '
        f'x-data="{{ cart_count: {cart_count} }}" '
        f'class="cart_count" x-show="{cart_count} > 0">{cart_count}</span>'
    )


@login_required
def update_cart(request, item_id):
    action = request.POST.get("action")
    cart = request.user.cart
    item = get_object_or_404(CartItem, id=item_id, cart=cart)  # ищем по id CartItem

    if action == "plus":
        item.quantity += 1
    elif action == "minus" and item.quantity > 1:
        item.quantity -= 1

    item.save()

    total = sum(i.total_price for i in cart.items.all())
    context = {
        "user_cart_products": cart.items.select_related("product")
        .prefetch_related(
            Prefetch(
                "product__images",
                queryset=ProductImage.objects.filter(media_type="image").order_by(
                    "order"
                ),
                to_attr="prefetched_images",
            )
        )
        .order_by("-added_at"),
        "user_cart_total": total,
        "user": request.user,
    }
    return render(request, "users/includes/cart_block.html", context)


def remove_from_cart(request, item_id):
    cart, _ = Cart.objects.get_or_create(user=request.user)

    # ищем CartItem напрямую по id
    CartItem.objects.filter(id=item_id, cart=cart).delete()

    user_cart_products = (
        cart.items.select_related("product")
        .prefetch_related(
            Prefetch(
                "product__images",
                queryset=ProductImage.objects.filter(media_type="image").order_by(
                    "order"
                ),
                to_attr="prefetched_images",
            )
        )
        .order_by("-added_at")
    )

    user_cart_total = sum(i.total_price for i in user_cart_products)

    partial = render_to_string(
        "users/includes/cart_block.html",
        {
            "user_cart_products": user_cart_products,
            "user_cart_total": user_cart_total,
        },
        request=request,
    )

    cart_count = cart.total_items
    display = "none" if cart_count == 0 else "flex"

    oob_counter = (
        f'<span id="cart-counter" hx-swap-oob="true" '
        f'class="cart_count" style="display:{display}">'
        f"{cart_count}</span>"
    )

    return HttpResponse(oob_counter + partial)


@login_required(login_url="/register/")
def order_create(request):
    user = request.user

    try:
        cart = user.cart
        cart_items = cart.items.select_related("product").all()
    except Cart.DoesNotExist:
        return redirect("shop:catalog")

    if not cart_items.exists():
        return redirect("users:profile")

    if request.method == "POST":
        form = OrderForm(user, request.POST)
        if form.is_valid():
            data = form.cleaned_data

            subtotal = cart.total_price
            delivery_cost = 0
            total = subtotal + delivery_cost

            order = Order.objects.create(
                user=user,
                subtotal=subtotal,
                delivery_cost=delivery_cost,
                total=total,
                customer_name=f"{data['first_name']} {data['last_name']}".strip(),
                customer_email=data["customer_email"],
                customer_phone=data["customer_phone"],
                delivery_address=data["delivery_address"],
                delivery_city=data["delivery_city"],
                delivery_postal_code=data["delivery_postal_code"],
                notes=data.get("notes", ""),
            )

            OrderItem.objects.bulk_create(
                [
                    OrderItem(
                        order=order,
                        product=item.product,
                        product_name=item.product.name,
                        product_price=item.product.final_price,
                        quantity=item.quantity,
                    )
                    for item in cart_items
                ]
            )

            for item in cart_items:
                item.product.stock -= item.quantity
                item.product.save(update_fields=["stock"])

            cart_items.delete()

            _update_profile_from_order(user, data)

            return redirect("payments:create_payment", order_id=order.id)
            # return redirect('shop:order_success', order_id=order.id)

    else:
        form = OrderForm(user)

    context = {
        "form": form,
        "cart_items": cart_items,
        "subtotal": cart.total_price,
        "delivery_cost": 0,
        "total": cart.total_price,
    }
    return render(request, "shop/order_create.html", context)


def _update_profile_from_order(user, data):
    user_changed = False
    profile_changed = False

    user_fields = {
        "first_name": data["first_name"],
        "last_name": data["last_name"],
    }
    for attr, value in user_fields.items():
        if value and getattr(user, attr) != value:
            setattr(user, attr, value)
            user_changed = True

    if user_changed:
        user.save(update_fields=list(user_fields.keys()))

    profile_fields = {
        "phone_number": data["customer_phone"],
        "delivery_city": data["delivery_city"],
        "delivery_address": data["delivery_address"],
        "delivery_postal_code": data["delivery_postal_code"],
    }
    for attr, value in profile_fields.items():
        if value and getattr(user, attr, None) != value:
            setattr(user, attr, value)
            profile_changed = True

    if profile_changed:
        user.save(update_fields=list(profile_fields.keys()))


@login_required(login_url="/register/")
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "shop/order_success.html", {"order": order})


# views.py (в приложении shop или reviews — где у тебя review_create)


@login_required(login_url="/register/")
def review_create(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    user = request.user

    has_valid_order = Order.objects.filter(
        user=user, status="delivered", payment_status="paid", items__product=product
    ).exists()

    if not has_valid_order:
        messages.error(request, "Вы можете оставить отзыв только на купленный товар.")
        return redirect("users:profile")

    if Review.objects.filter(user=user, product=product).exists():
        messages.info(request, "Вы уже оставляли отзыв на этот товар.")
        return redirect("users:profile")

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = Review.objects.create(
                product=product,
                user=user,
                rating=form.cleaned_data["rating"],
                title=form.cleaned_data["title"],
                text=form.cleaned_data["text"],
            )
        return redirect("shop:review_media", review_id=review.pk)
    else:
        form = ReviewForm()

    return render(
        request,
        "shop/review_create.html",
        {
            "form": form,
            "product": product,
        },
    )


@login_required(login_url="/register/")
def review_media(request, review_id):
    """Шаг 2 — загрузка медиафайлов к отзыву"""
    review = get_object_or_404(
        Review.objects.prefetch_related("media"),
        pk=review_id,
        user=request.user,  # только свой отзыв
    )
    return render(
        request,
        "shop/review_media.html",
        {
            "review": review,
            "product": review.product,
            "max_photos": Review.MAX_PHOTOS,
            "max_videos": Review.MAX_VIDEOS,
        },
    )


@login_required(login_url="/register/")
@require_POST
def upload_review_media(request, review_id):
    """AJAX: загрузка одного файла"""
    review = get_object_or_404(Review, pk=review_id, user=request.user)
    file = request.FILES.get("file")
    if not file:
        return JsonResponse({"error": "Файл не передан"}, status=400)

    ext = os.path.splitext(file.name)[1].lower()
    is_video = ext in {".mp4", ".mov", ".avi", ".webm"}
    media_type = "video" if is_video else "photo"

    # Проверяем лимиты до сохранения
    existing_count = review.media.filter(media_type=media_type).count()
    limit = Review.MAX_VIDEOS if is_video else Review.MAX_PHOTOS
    if existing_count >= limit:
        return JsonResponse(
            {"error": f"Максимум {limit} файлов типа {media_type}"}, status=400
        )

    last_order = (
        review.media.aggregate(max_order=db_models.Max("order"))["max_order"] or 0
    )

    obj = ReviewMedia(
        review=review,
        media_type=media_type,
        file=file,
        order=last_order + 1,
        status="pending",
    )
    obj.save()

    async_task(
        "shop.tasks.compress_review_media",  # поправь путь
        obj.pk,
        task_name=f"compress_review_media_{obj.pk}",
    )

    return JsonResponse(
        {
            "id": obj.pk,
            "media_type": media_type,
            "status": obj.status,
            "preview_url": obj.preview_url,
        }
    )


@login_required(login_url="/register/")
@require_POST
def delete_review_media(request, media_id):
    obj = get_object_or_404(ReviewMedia, pk=media_id, review__user=request.user)
    if obj.file:
        obj.file.delete(save=False)
    if obj.file_compressed:
        obj.file_compressed.delete(save=False)
    obj.delete()
    return JsonResponse({"ok": True})


@login_required(login_url="/register/")
def review_media_status(request, media_id):
    obj = get_object_or_404(ReviewMedia, pk=media_id, review__user=request.user)
    return JsonResponse(
        {
            "status": obj.status,
            "preview_url": obj.preview_url,
        }
    )


@login_required(login_url="/register/")
def review_media_item_partial(request, media_id):
    obj = get_object_or_404(ReviewMedia, pk=media_id, review__user=request.user)
    return render(request, "shop/includes/review_media_item.html", {"media": obj})




def info_page(request):
    # Получаем все активные записи
    info_items = Info.objects.filter(is_active=True)
    
    # Получаем активную вкладку из GET-параметра
    active_tab = request.GET.get('tab', None)
    
    return render(
        request,
        "shop/info_page.html",
        {
            "info_items": info_items,
            "active_tab": active_tab,
        },
    )

def review_popup(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    return render(
        request,
        "shop/includes/review_popup.html",
        {"review": review, "media": review.media.all()},
    )


# ===== ЗАГЛУШКА ОПЛАТЫ — УДАЛИТЬ ПОСЛЕ ПОДКЛЮЧЕНИЯ ЭКВАЙРИНГА =====
@login_required(login_url="/register/")
def payment_stub(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if request.method == "POST":
        order.payment_status = "paid"
        order.status = "delivered"
        order.save()
        messages.success(request, "Заказ оплачен и доставлен (тестовый режим).")
        return redirect("users:profile")
    return redirect("shop:order_success", order_id=order.id)


# ===== КОНЕЦ ЗАГЛУШКИ =====
