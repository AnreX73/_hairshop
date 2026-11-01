GEO_PROMPT_EXCLUDED_NAMESPACES = {"users", "payments", "dashboard", "admin"}
GEO_PROMPT_EXCLUDED_URLS = {
    "shop:order_create",
    "shop:order_success",
    "shop:payment_stub",
}


def cart_context(request):
    if request.user.is_authenticated:
        user_favorite_ids = request.user.favorites.values_list("product_id", flat=True)
        try:
            cart_count = request.user.cart.total_items
        except Exception:
            cart_count = 0
    else:
        user_favorite_ids = []
        cart_count = 0

    return {
        "user_favorite_ids": user_favorite_ids,
        "cart_count": cart_count,
    }


def geo_prompt_context(request):
    """Можно ли показывать окно «Ваш город?» на текущей странице.

    Окно не показываем авторизованным и на служебных страницах: вход,
    регистрация, сброс пароля, оформление и оплата заказа, админка.
    """
    if request.user.is_authenticated:
        return {"geo_prompt_allowed": False}

    match = request.resolver_match
    if match is None:
        return {"geo_prompt_allowed": False}

    if match.namespace in GEO_PROMPT_EXCLUDED_NAMESPACES:
        return {"geo_prompt_allowed": False}

    if f"{match.namespace}:{match.url_name}" in GEO_PROMPT_EXCLUDED_URLS:
        return {"geo_prompt_allowed": False}

    return {"geo_prompt_allowed": True}
