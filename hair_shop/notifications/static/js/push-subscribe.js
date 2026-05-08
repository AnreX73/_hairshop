// static/js/push-subscribe.js

(async function () {
    'use strict';

    // ── ВАЖНО: читаем currentScript ДО первого await ──────────────────────
    const scriptTag = document.currentScript;
    const vapidPublicKey = scriptTag?.dataset?.vapidKey;

    // ── 1. Проверяем поддержку браузера ──────────────────────────────────
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        console.log('Push notifications are not supported in this browser');
        return;
    }

    // ── 2. Регистрируем Service Worker ───────────────────────────────────
    let registration;
    try {
        registration = await navigator.serviceWorker.register('/service-worker.js', {
            scope: '/'
        });
        console.log('Service Worker registered');
    } catch (err) {
        console.error('Service Worker registration failed:', err);
        return;
    }

    // ── 3. Проверяем VAPID ключ ───────────────────────────────────────────
    if (!vapidPublicKey) {
        console.error('VAPID public key not provided. Add data-vapid-key attr to <script>.');
        return;
    }

    // ── 4. Проверяем текущее разрешение ──────────────────────────────────
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') {
        console.log('Push permission denied');
        return;
    }

    // ── 5. Проверяем, есть ли уже подписка ───────────────────────────────
    let subscription = await registration.pushManager.getSubscription();

    if (!subscription) {
        // ── 6. Создаём новую подписку ────────────────────────────────────
        try {
            subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(vapidPublicKey)
            });
            console.log('Push subscription created');
        } catch (err) {
            console.error('Failed to subscribe:', err);
            return;
        }

        // ── 7. Сохраняем подписку на сервере ─────────────────────────────
        await saveSubscriptionToServer(subscription);
    }
})();


// ── Вспомогательная функция: конвертирует VAPID ключ ─────────────────────
function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/-/g, '+')
        .replace(/_/g, '/');
    const rawData = window.atob(base64);
    return Uint8Array.from([...rawData].map(char => char.charCodeAt(0)));
}


// ── Отправляет subscription на Django backend ─────────────────────────────
async function saveSubscriptionToServer(subscription) {
    const subJson = subscription.toJSON();

    try {
        const response = await fetch('/notifications/subscribe/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({
                endpoint: subJson.endpoint,
                keys: {
                    p256dh: subJson.keys.p256dh,
                    auth: subJson.keys.auth,
                }
            })
        });

        if (response.ok) {
            console.log('Subscription saved to server ✓');
        } else {
            console.error('Failed to save subscription:', await response.text());
        }
    } catch (err) {
        console.error('Network error saving subscription:', err);
    }
}


// ── Читает CSRF-токен из cookie ───────────────────────────────────────────
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
}