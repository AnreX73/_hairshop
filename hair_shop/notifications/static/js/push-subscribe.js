// static/js/push-subscribe.js

// Кнопок подписки на странице может быть несколько (шапка, виджет чата,
// профиль). Ищем их по data-атрибуту и поддерживаем старые id для совместимости.
const PUSH_ENABLE_SELECTOR = '[data-push-toggle="enable"], #enable-push-btn';
const PUSH_DISABLE_SELECTOR = '[data-push-toggle="disable"], #disable-push-btn';

function pushButtons(selector) {
    return Array.from(document.querySelectorAll(selector));
}

function setPushState(subscribed) {
    pushButtons(PUSH_ENABLE_SELECTOR).forEach((btn) => {
        btn.style.display = subscribed ? 'none' : '';
    });
    pushButtons(PUSH_DISABLE_SELECTOR).forEach((btn) => {
        btn.style.display = subscribed ? '' : 'none';
    });
}

// ── При загрузке страницы: показываем нужные кнопки ──────────────────────
(async () => {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;

    try {
        const registration = await navigator.serviceWorker.ready;
        const subscription = await registration.pushManager.getSubscription();
        setPushState(Boolean(subscription));
    } catch (err) {
        console.warn('Push state check failed:', err);
    }
})();


// ── Подписка: клик на кнопку "Включить уведомления" ──────────────────────
async function enablePush(btn) {
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

        // Гарантированно дожидаемся активации Service Worker перед подпиской,
        // иначе PushManager.subscribe может выбросить AbortError
        // ("no active Service Worker") при первом клике.
        registration = await navigator.serviceWorker.ready;

        // Дополнительная защита: если по какой-то причине registration.active
        // всё ещё не установлен, ждём событие statechange у installing/waiting worker.
        if (!registration.active) {
            const worker = registration.installing || registration.waiting;
            if (worker) {
                await new Promise((resolve) => {
                    worker.addEventListener('statechange', () => {
                        if (worker.state === 'activated') resolve();
                    });
                });
            }
        }

        console.log('Service Worker is active and ready');
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

    setPushState(true);
}


// ── Отписка: клик на кнопку "Отключить уведомления" ──────────────────────
async function disablePush() {
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
        setPushState(false);
    }
}


document.addEventListener('click', (event) => {
    if (!(event.target instanceof Element)) return;
    const enableBtn = event.target.closest(PUSH_ENABLE_SELECTOR);
    if (enableBtn) {
        enablePush(enableBtn);
        return;
    }
    const disableBtn = event.target.closest(PUSH_DISABLE_SELECTOR);
    if (disableBtn) disablePush();
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
