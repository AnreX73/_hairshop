// static/js/push-subscribe.js

// ── При загрузке страницы: показываем нужную кнопку ──────────────────────
(async () => {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;

    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.getSubscription();

    const enableBtn = document.getElementById('enable-push-btn');
    const disableBtn = document.getElementById('disable-push-btn');

    if (subscription) {
        if (enableBtn) enableBtn.style.display = 'none';
        if (disableBtn) disableBtn.style.display = '';
    } else {
        if (enableBtn) enableBtn.style.display = '';
        if (disableBtn) disableBtn.style.display = 'none';
    }
})();


// ── Подписка: клик на кнопку "Включить уведомления" ──────────────────────
document.getElementById('enable-push-btn')?.addEventListener('click', async () => {
    const btn = document.getElementById('enable-push-btn');
    const vapidPublicKey = btn.dataset.vapidKey;

    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        console.log('Push notifications are not supported in this browser');
        return;
    }

    if (!vapidPublicKey) {
        console.error('VAPID public key not provided. Add data-vapid-key attr to button.');
        return;
    }

    let registration;
    try {
        registration = await navigator.serviceWorker.register('/service-worker.js', { scope: '/' });
        console.log('Service Worker registered');
    } catch (err) {
        console.error('Service Worker registration failed:', err);
        return;
    }

    const permission = await Notification.requestPermission();
    console.log('Permission:', permission);
    if (permission !== 'granted') {
        console.log('Push permission denied');
        return;
    }

    let subscription = await registration.pushManager.getSubscription();

    if (!subscription) {
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
        await saveSubscriptionToServer(subscription);
    }

    // Переключаем кнопки
    btn.style.display = 'none';
    const disableBtn = document.getElementById('disable-push-btn');
    if (disableBtn) disableBtn.style.display = '';
});


// ── Отписка: клик на кнопку "Отключить уведомления" ──────────────────────
document.getElementById('disable-push-btn')?.addEventListener('click', async () => {
    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.getSubscription();

    if (subscription) {
        await subscription.unsubscribe();
        await fetch('/notifications/unsubscribe/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({ endpoint: subscription.endpoint })
        });
        console.log('Unsubscribed');

        // Переключаем кнопки
        document.getElementById('disable-push-btn').style.display = 'none';
        const enableBtn = document.getElementById('enable-push-btn');
        if (enableBtn) enableBtn.style.display = '';
    }
});


// ── Вспомогательные функции ───────────────────────────────────────────────
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