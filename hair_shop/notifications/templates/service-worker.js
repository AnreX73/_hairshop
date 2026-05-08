// static/js/service-worker.js
// Этот файл ОБЯЗАН лежать на корневом пути: /service-worker.js
// В Django это делается через отдельный URL (см. urls.py)

const CACHE_NAME = 'shop-v1';

// ─── Install ───────────────────────────────────────────────────────────────
self.addEventListener('install', (event) => {
    // Активируемся немедленно, не ждём закрытия старых вкладок
    self.skipWaiting();
});

// ─── Activate ──────────────────────────────────────────────────────────────
self.addEventListener('activate', (event) => {
    event.waitUntil(clients.claim());
});

// ─── Push: получение уведомления от сервера ────────────────────────────────
self.addEventListener('push', (event) => {
    let data = {
        title: 'Новый заказ',
        body: '',
        url: '/',
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/badge-72x72.png',
    };

    if (event.data) {
        try {
            data = { ...data, ...event.data.json() };
        } catch (e) {
            data.body = event.data.text();
        }
    }

    const options = {
        body: data.body,
        icon: data.icon,
        badge: data.badge,
        data: { url: data.url },          // передаём URL в обработчик клика
        vibrate: [200, 100, 200],         // вибро-паттерн на мобильных
        requireInteraction: true,          // уведомление не исчезает само
        actions: [
            { action: 'open', title: '📋 Открыть заказ' },
            { action: 'close', title: 'Закрыть' },
        ],
    };

    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

// ─── NotificationClick: клик по уведомлению ────────────────────────────────
self.addEventListener('notificationclick', (event) => {
    event.notification.close();

    if (event.action === 'close') return;

    const targetUrl = event.notification.data?.url || '/';

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((clientList) => {
                // Если магазин уже открыт — фокусируем вкладку и переходим
                for (const client of clientList) {
                    if (client.url.includes(self.location.origin) && 'focus' in client) {
                        client.focus();
                        client.navigate(targetUrl);
                        return;
                    }
                }
                // Иначе открываем новую вкладку
                if (clients.openWindow) {
                    return clients.openWindow(targetUrl);
                }
            })
    );
});
