from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.db.models import Q
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.db.models import Sum
from django.template.loader import render_to_string
from .forms import OrderForm,ReviewForm 

from django.contrib import messages

from .models import Category, Product, ProductImage, SiteAssets, Favorite, CartItem, Cart, Order, OrderItem, Review, ReviewMedia


def index(request):
    # Проверяем кэш
    cache_key = 'site_assets_homepage'
    cached_data = cache.get(cache_key)
    categories = Category.objects.all()
    hit_products = Product.objects.filter(is_hit=True)
    if cached_data:
        context = cached_data
    else:
        try:
            # Один запрос для всех объектов
            assets = SiteAssets.objects.filter(
                Q(site_assets_name__in=['logo', 'logo_text', 'slogan', 'cart_icon', 'account_icon']) |
                Q(note='advantages')
            )
            
            # Формируем контекст
            context = {'title': 'Студия НР', 'advantages': []}
            for asset in assets:
                if asset.note == 'advantages':
                    context['advantages'].append(asset)
                elif asset.site_assets_name:
                    context[asset.site_assets_name] = asset


            # Кэшируем на 1 час
            cache.set(cache_key, context, 3600)

        except Exception:
            # Обработка ошибок
            context = {
                'title': 'Главная',
                'error': 'Не удалось загрузить данные сайта'
            }
    
    context['categories'] = categories
    context['hit_products'] = hit_products
    

    return render(request, 'shop/index.html', context)


def catalog(request):
    # Prefetch изображений (оставляем как есть)
    images_prefetch = Prefetch(
        'images',
        queryset=ProductImage.objects.filter(media_type='image').order_by('order'),
        to_attr='prefetched_images'
    )

    products = Product.objects.filter(is_available=True).prefetch_related(
        images_prefetch
    ).order_by('-popularity')

    paginator = Paginator(products, 20)

    # 1. Получаем номер страницы из GET или из сессии
    page_number = request.GET.get('page')
    if page_number is None:
        # Если параметр page не передан, пытаемся взять из сессии
        page_number = request.session.get('catalog_last_page', 1)
    else:
        # Если страница указана явно – сохраняем её в сессию
        request.session['catalog_last_page'] = page_number

    page_obj = paginator.get_page(page_number)

    return render(request, 'shop/catalog.html', {'page_obj': page_obj})

    


def product_page(request, slug, product_id):
    product = get_object_or_404(
        Product.objects.select_related('category').defer('created_at', 'updated_at'),
        id=product_id
    )
    
    product_gallery = ProductImage.objects.filter(product=product).order_by('-created_at')
    video_poster = product_gallery.filter(media_type='image').first()
    
    images_prefetch = Prefetch(
        'images',
        queryset=ProductImage.objects.filter(media_type='image').order_by('order'),
        to_attr='prefetched_images'
    )
    
    
    related_products = Product.objects.filter(
        group_slug=product.group_slug
    ).exclude(
        id=product_id
    ).select_related('category').prefetch_related(images_prefetch)
    
    return render(request, 'shop/product_page.html', {
        'product': product,
        'product_gallery': product_gallery,
        'video_poster': video_poster,
        'related_products': related_products
    })
    




@login_required
@require_POST
def toggle_favorite(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    # Получаем желаемое состояние из Alpine (приходит строкой 'true' или 'false')
    is_favorite_requested = request.POST.get('is_favorite') == 'true'
    
    if is_favorite_requested:
        # Пытаемся создать запись, если её еще нет
        Favorite.objects.get_or_create(user=request.user, product=product)
    else:
        # Удаляем запись, если она существует
        Favorite.objects.filter(user=request.user, product=product).delete()
    
    return HttpResponse(status=204) # Успешно, без смены контента



@login_required
@require_POST
def toggle_cart(request, product_id):
    product = Product.objects.get(pk=product_id)
    cart, _ = Cart.objects.get_or_create(user=request.user)
    
    is_cart = request.POST.get('is_cart') == 'true'
    
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
    action = request.POST.get('action')
    cart = request.user.cart
    item = get_object_or_404(CartItem, id=item_id, cart=cart)  # ищем по id CartItem

    if action == 'plus':
        item.quantity += 1
    elif action == 'minus' and item.quantity > 1:
        item.quantity -= 1

    item.save()

    total = sum(i.total_price for i in cart.items.all())
    context = {
        'user_cart_products': cart.items.select_related('product').prefetch_related(
            Prefetch(
                'product__images',
                queryset=ProductImage.objects.filter(media_type='image').order_by('order'),
                to_attr='prefetched_images'
            )
        ).order_by('-added_at'),
        'user_cart_total': total,
        'user': request.user,
    }
    return render(request, 'users/includes/cart_block.html', context)



def remove_from_cart(request, item_id):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    
    # ищем CartItem напрямую по id
    CartItem.objects.filter(id=item_id, cart=cart).delete()
    
    user_cart_products = cart.items.select_related('product').prefetch_related(
        Prefetch(
            'product__images',
            queryset=ProductImage.objects.filter(media_type='image').order_by('order'),
            to_attr='prefetched_images'
        )
    ).order_by('-added_at')

    user_cart_total = sum(i.total_price for i in user_cart_products)

    partial = render_to_string('users/includes/cart_block.html', {
        'user_cart_products': user_cart_products,
        'user_cart_total': user_cart_total,
    }, request=request)

    cart_count = cart.total_items
    display = "none" if cart_count == 0 else "flex"

    oob_counter = (
        f'<span id="cart-counter" hx-swap-oob="true" '
        f'class="cart_count" style="display:{display}">'
        f'{cart_count}</span>'
    )

    return HttpResponse(oob_counter + partial)



@login_required(login_url="/register/")
def order_create(request):
    user = request.user
    
    try:
        cart = user.cart
        cart_items = cart.items.select_related('product').all()
    except Cart.DoesNotExist:
        return redirect('shop:catalog')
    
    if not cart_items.exists():
        return redirect('users:profile')  # пустая корзина — назад в профиль

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            # Считаем стоимости
            subtotal = cart.total_price
            delivery_cost = 0  # логику доставки добавишь позже
            total = subtotal + delivery_cost

            # Создаём заказ
            order = Order.objects.create(
                user=user,
                subtotal=subtotal,
                delivery_cost=delivery_cost,
                total=total,
                customer_name=form.cleaned_data['customer_name'],
                customer_email=form.cleaned_data['customer_email'],
                customer_phone=form.cleaned_data['customer_phone'],
                delivery_address=form.cleaned_data['delivery_address'],
                delivery_city=form.cleaned_data['delivery_city'],
                delivery_postal_code=form.cleaned_data['delivery_postal_code'],
                notes=form.cleaned_data.get('notes', ''),
            )

            # Переносим товары из корзины в заказ
            order_items = [
                OrderItem(
                    order=order,
                    product=item.product,
                    product_name=item.product.name,
                    product_price=item.product.final_price,
                    quantity=item.quantity,
                )
                for item in cart_items
            ]
            OrderItem.objects.bulk_create(order_items)

            # Очищаем корзину
            cart_items.delete()

            return redirect('shop:order_success', order_id=order.id)
    else:
        # Предзаполняем форму данными из профиля
        form = OrderForm(initial={
            'customer_name': f"{user.first_name} {user.last_name}".strip() or user.username,
            'customer_email': user.email,
            'customer_phone': user.phone_number,
            'delivery_address': user.delivery_address,
            'delivery_city': user.delivery_city,
            'delivery_postal_code': user.delivery_postal_code,
        })

    context = {
        'form': form,
        'cart_items': cart_items,
        'subtotal': cart.total_price,
        'delivery_cost': 0,
        'total': cart.total_price,
    }
    return render(request, 'shop/order_create.html', context)


@login_required(login_url="/register/")
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'shop/order_success.html', {'order': order})


@login_required(login_url="/register/")
def review_create(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    user = request.user

    # Проверяем право на отзыв
    has_valid_order = Order.objects.filter(
        user=user,
        status='delivered',
        payment_status='paid',
        items__product=product
    ).exists()

    if not has_valid_order:
        messages.error(request, 'Вы можете оставить отзыв только на купленный товар.')
        return redirect('users:profile')

    # Уже оставлял?
    if Review.objects.filter(user=user, product=product).exists():
        messages.info(request, 'Вы уже оставляли отзыв на этот товар.')
        return redirect('users:profile')

    if request.method == 'POST':
        form = ReviewForm(request.POST, request.FILES)
        if form.is_valid():
            review = Review.objects.create(
                product=product,
                user=user,
                rating=form.cleaned_data['rating'],
                title=form.cleaned_data['title'],
                text=form.cleaned_data['text'],
            )
            # Сохраняем медиафайлы
            for f in request.FILES.getlist('files'):
                ReviewMedia.objects.create(review=review, file=f)

            messages.success(request, 'Отзыв отправлен на модерацию, спасибо!')
            return redirect('users:profile')
    else:
        form = ReviewForm()

    return render(request, 'shop/review_create.html', {
        'form': form,
        'product': product,
    })

# ===== ЗАГЛУШКА ОПЛАТЫ — УДАЛИТЬ ПОСЛЕ ПОДКЛЮЧЕНИЯ ЭКВАЙРИНГА =====
@login_required(login_url="/register/")
def payment_stub(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if request.method == 'POST':
        order.payment_status = 'paid'
        order.status = 'delivered'
        order.save()
        messages.success(request, 'Заказ оплачен и доставлен (тестовый режим).')
        return redirect('users:profile')
    return redirect('shop:order_success', order_id=order.id)
# ===== КОНЕЦ ЗАГЛУШКИ =====