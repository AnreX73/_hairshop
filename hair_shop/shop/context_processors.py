



def cart_context(request):
    if request.user.is_authenticated:
        user_favorite_ids = request.user.favorites.values_list('product_id', flat=True)
        try:
            cart_count = request.user.cart.total_items
        except Exception:
            cart_count = 0
    else:
        user_favorite_ids = []
        cart_count = 0

    return {
        'user_favorite_ids': user_favorite_ids,
        'cart_count': cart_count,
    }