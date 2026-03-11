from django.core.cache import cache
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponse

from .models import Category, Product, ProductImage, SiteAssets, Favorite


def index(request):
    # Проверяем кэш
    cache_key = 'site_assets_homepage'
    cached_data = cache.get(cache_key)
    categories = Category.objects.all()
    if request.user.is_authenticated:
        user_favorite_ids = request.user.favorites.values_list('product_id', flat=True)
    else:
        user_favorite_ids = []
    hit_products = Product.objects.filter(is_hit=True).only('name', 'main_image', 'start_price', 'discount_percentage', 'rating', 'is_hit')
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
    context['user_favorite_ids'] = user_favorite_ids

    return render(request, 'shop/index.html', context)


def catalog(request):
    products = Product.objects.only('name', 'main_image', 'start_price', 'discount_percentage', 'rating', 'is_hit').filter(is_available=True)
    if request.user.is_authenticated:
        user_favorite_ids = request.user.favorites.values_list('product_id', flat=True)
    else:
        user_favorite_ids = []
    return render(request, 'shop/catalog.html', {'products': products, 'user_favorite_ids': user_favorite_ids})


def product_page(request, slug, product_id):
    product = get_object_or_404(Product.objects.prefetch_related('category').defer('created_at', 'updated_at','slug'), id=product_id, slug=slug)
    product_gallery = ProductImage.objects.filter(product=product)
    related_products = Product.objects.filter(slug=slug).exclude(id=product.id).only('id', 'main_image', 'color')
    return render(request, 'shop/product_page.html', {'product': product, 'related_products': related_products, 'product_gallery': product_gallery})



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


