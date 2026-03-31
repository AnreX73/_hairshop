from django.core.cache import cache
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.db.models import Sum
from django.template.loader import render_to_string
from .forms import OrderCreateForm

from .models import Category, Product, ProductImage, SiteAssets, Favorite, CartItem, Cart


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
    products = Product.objects.filter(is_available=True).order_by('?') # потом убрать order_by('?') и выводить по популярности
    
        
    
        
    return render(request, 'shop/catalog.html', {'products': products})

    


def product_page(request, slug, product_id):
    # Оставляем только QuerySet (в нем уже есть информация о модели Product)
    product = get_object_or_404(
        Product.objects.select_related('series').defer('created_at', 'updated_at'), 
        id=product_id
    )
    
    product_gallery = ProductImage.objects.filter(product=product).order_by('-created_at')
    related_products = Product.objects.filter(series=product.series).exclude(id=product_id).select_related('series') 
    return render(request, 'shop/product_page.html', {'product': product, 'product_gallery': product_gallery, 'related_products': related_products})
    




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




def remove_from_cart(request, product_id):
    product = Product.objects.get(pk=product_id)
    cart, _ = Cart.objects.get_or_create(user=request.user)
    
    
    CartItem.objects.filter(cart=cart, product=product).delete()
    
    user_cart_products = Product.objects.filter(
        cart_items__cart=cart
    ).order_by('-cart_items__added_at')
    
    user_cart_total = sum(p.final_price for p in user_cart_products)

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

def order_create(request):
    return HttpResponse("Order created")