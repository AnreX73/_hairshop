# убери повторы импортов

from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import models
from django.db.models import Q

from shop.models import Product, Category, Favorite, Order, OrderItem
from users.models import User  # Оставил, если используете напрямую вместо get_user_model
from .forms import OrderShipForm



User = get_user_model()
is_manager = lambda u: u.is_staff


class AdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'dashboard/admin_area.html'

    # Проверка, что зашел именно админ/стафф
    def test_func(self):
        return self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Собираем данные из разных приложений
        context['total_products'] = Product.objects.count()
        context['total_users'] = User.objects.count()
        context['total_favorites'] = Favorite.objects.count()
        return context





# ─────────────────────────────────────────────────────────────
# Вспомогательная функция — рендерит partial карточки
# ─────────────────────────────────────────────────────────────
 
def _card_response(request, order):
    order = (
        Order.objects
        .select_related('user', 'assigned_manager')
        .prefetch_related('items__product__images')
        .get(pk=order.pk)
    )
    managers = User.objects.filter(is_staff=True)
    return render(request, 'dashboard/partials/_order_card.html', {
        'order': order,
        'managers': managers,
        'is_superuser': request.user.is_superuser,
    })
 
 
# ─────────────────────────────────────────────────────────────
# Главная страница
# ─────────────────────────────────────────────────────────────
 
@login_required
@user_passes_test(is_manager)
def manage_orders(request):
    orders = (
        Order.objects
        .select_related('user', 'assigned_manager')
        .prefetch_related('items__product__images')
        .order_by('-created_at')
    )
    managers = User.objects.filter(is_staff=True)
 
    if request.user.is_superuser:
        # Суперюзер: смотрит сессию — выбран ли конкретный менеджер
        active_manager_id = request.session.get('active_manager_id')
        active_manager = managers.filter(id=active_manager_id).first() if active_manager_id else None
        if active_manager:
            orders = orders.filter(assigned_manager=active_manager)
        # если active_manager = None — видит все заказы
    else:
        # Обычный менеджер — только свои заказы
        active_manager = request.user
        orders = orders.filter(
        models.Q(assigned_manager=request.user) | 
        models.Q(assigned_manager=None)
    )
 
    return render(request, 'dashboard/manage_orders.html', {
        'title': 'Управление заказами',
        'orders': orders,
        'managers': managers,
        'active_manager': active_manager,
        'is_superuser': request.user.is_superuser,
    })
 
 
# ─────────────────────────────────────────────────────────────
# Переключение активного менеджера (только для суперюзера)
# ─────────────────────────────────────────────────────────────
 
@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def set_active_manager(request):
    manager_id = request.POST.get('manager_id')
    if manager_id:
        request.session['active_manager_id'] = int(manager_id)
    else:
        request.session.pop('active_manager_id', None)
    # HX-Refresh перезагружает всю страницу через HTMX
    from django.http import HttpResponse
    return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
 
 
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
            manager_id = request.POST.get('manager_id')
            manager = get_object_or_404(User, id=manager_id, is_staff=True)
        else:
            # Обычный менеджер берёт себе
            manager = request.user
        order.assigned_manager = manager
        order.status = 'confirmed'
        order.save(update_fields=['assigned_manager', 'status', 'updated_at'])
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
    item.save(update_fields=['is_collected'])
    order = Order.objects.get(pk=item.order_id)
    return _card_response(request, order)
 
 
# ─────────────────────────────────────────────────────────────
# Статус → «В обработке»  (все товары должны быть собраны)
# ─────────────────────────────────────────────────────────────
 
@login_required
@user_passes_test(is_manager)
@require_POST
def order_set_processing(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related('items'), id=order_id
    )
    if not order.items.filter(is_collected=False).exists():
        order.status = 'processing'
        order.save(update_fields=['status', 'updated_at'])
    return _card_response(request, order)
 
 
# ─────────────────────────────────────────────────────────────
# Статус → «Отправлен»  (+ опциональный трек-номер)
# ─────────────────────────────────────────────────────────────
 
@login_required
@user_passes_test(is_manager)
@require_POST
def order_ship(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    tracking = request.POST.get('tracking_number', '').strip()
    if tracking:
        order.tracking_number = tracking
    order.status = 'shipped'
    order.save(update_fields=['status', 'tracking_number', 'updated_at'])
    return _card_response(request, order)
 
 
# ─────────────────────────────────────────────────────────────
# Статус → «Доставлен»
# ─────────────────────────────────────────────────────────────
 
@login_required
@user_passes_test(is_manager)
@require_POST
def order_deliver(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.status = 'delivered'
    order.save(update_fields=['status', 'updated_at'])
    return _card_response(request, order)
 
 
# ─────────────────────────────────────────────────────────────
# Отменить заказ
# ─────────────────────────────────────────────────────────────
 
@login_required
@user_passes_test(is_manager)
@require_POST
def order_cancel(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if order.status not in ('delivered', 'shipped'):
        order.status = 'cancelled'
        order.save(update_fields=['status', 'updated_at'])
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
        return JsonResponse({'ok': False, 'error': 'invalid json'}, status=400)
 
    new_status = body.get('payment_status')
    if new_status in dict(Order.PAYMENT_STATUS_CHOICES):
        order.payment_status = new_status
        order.save(update_fields=['payment_status', 'updated_at'])
        return JsonResponse({'ok': True})
 
    return JsonResponse({'ok': False, 'error': 'unknown status'}, status=400)