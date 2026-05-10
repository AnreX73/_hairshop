// static/js/push-subscribe.js

document.getElementById('enable-push-btn')?.addEventListener('click', async () => {
    'use strict';
    (async () => {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;
    
    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.getSubscription();
    
    if (subscription) {
        const btn = document.getElementById('enable-push-btn');
        if (btn) btn.style.display = 'none';
    }
})();
    const btn = document.getElementById('enable-push-btn');
    const vapidPublicKey = btn.dataset.vapidKey;

    // ── 1. Проверяем поддержку браузера ──────────────────────────────────
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        console.log('Push notifications are not supported in this browser');
        return;
    }

    // ── 2. Проверяем VAPID ключ ───────────────────────────────────────────
    if (!vapidPublicKey) {
        console.error('VAPID public key not provided. Add data-vapid-key attr to button.');
        return;
    }

    // ── 3. Регистрируем Service Worker ───────────────────────────────────
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

    // ── 4. Запрашиваем разрешение ─────────────────────────────────────────
    const permission = await Notification.requestPermission();
    console.log('Permission:', permission); 
    if (permission !== 'granted') {
        console.log('Push permission denied');
        return;
    }

    // ── 5. Проверяем, есть ли уже подписка ───────────────────────────────
    let subscription = await registration.pushManager.getSubscription();
    console.log('Existing subscription:', subscription);  // ← есть уже?

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

    // Скрываем кнопку после успешной подписки
    btn.style.display = 'none';
});


function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/-/g, '+')
        .replace(/_/g, '/');
    const rawData = window.atob(base64);
    return Uint8Array.from([...rawData].map(char => char.charCodeAt(0)));
}

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

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
}

(async () => {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;
    
    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.getSubscription();
    
    if (subscription) {
        const btn = document.getElementById('enable-push-btn');
        if (btn) btn.style.display = 'none';
    }
})();