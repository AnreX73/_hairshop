/**
 * Определение и подтверждение города посетителя.
 *
 * Город определяется в фоне по IP через /api/geo/city/ (ключ DaData остаётся
 * на сервере). Если город найден, показываем окно «Ваш город …?».
 *
 * localStorage['hairshop-city']      — подтверждённый город (до регистрации);
 * cookie hairshop_city               — зеркало для сервера при регистрации;
 * sessionStorage + cookie declined   — отказ до конца визита (до закрытия браузера);
 * sessionStorage prompt-shown        — окно уже показывали в этой сессии.
 */
(function () {
    'use strict';

    const CITY_KEY = 'hairshop-city';
    const CITY_COOKIE = 'hairshop_city';
    const DECLINED_COOKIE = 'hairshop_city_declined';
    const DECLINED_KEY = 'hairshop-city-declined';
    const PROMPT_SHOWN_KEY = 'hairshop-city-prompt-shown';
    const DETECTED_KEY = 'hairshop-geo-detected';
    const FAILED_KEY = 'hairshop-geo-failed-until';

    const DETECT_DELAY = 1500;   // не мешаем первой отрисовке страницы
    const SHOW_DELAY = 1200;     // пауза после ответа — окно не «выпрыгивает»
    const DETECTED_TTL = 6 * 60 * 60 * 1000;
    const FAILED_TTL = 60 * 60 * 1000;
    const COOKIE_MAX_AGE = 365 * 24 * 60 * 60;

    const overlay = document.getElementById('city-prompt');
    const cityLabel = document.getElementById('city-prompt-city');
    const yesBtn = document.getElementById('city-prompt-yes');
    const noBtn = document.getElementById('city-prompt-no');
    const closeBtn = document.getElementById('city-prompt-close');

    let lastFocused = null;
    let hideTimer = null;
    let pendingCity = null;

    // ── хранилища ────────────────────────────────────────────────────────────

    function storageGet(storage, key) {
        try {
            return storage.getItem(key);
        } catch (error) {
            return null;
        }
    }

    function storageSet(storage, key, value) {
        try {
            storage.setItem(key, value);
        } catch (error) {
            /* приватный режим или переполненное хранилище */
        }
    }

    function storageRemove(storage, key) {
        try {
            storage.removeItem(key);
        } catch (error) {
            /* ignore */
        }
    }

    function getCookie(name) {
        const match = document.cookie.match(
            new RegExp('(?:^|; )' + name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '=([^;]*)')
        );
        return match ? decodeURIComponent(match[1]) : '';
    }

    function setCookie(name, value, maxAge) {
        let cookie = name + '=' + encodeURIComponent(value) + '; path=/; samesite=lax';
        if (typeof maxAge === 'number') {
            cookie += '; max-age=' + maxAge;
        }
        document.cookie = cookie;
    }

    function deleteCookie(name) {
        document.cookie = name + '=; path=/; max-age=0; samesite=lax';
    }

    // ── город ────────────────────────────────────────────────────────────────

    function getStoredCity() {
        const raw = storageGet(window.localStorage, CITY_KEY);
        if (!raw) return null;
        try {
            const parsed = JSON.parse(raw);
            if (parsed && typeof parsed.city === 'string' && parsed.city.trim()) {
                return parsed;
            }
        } catch (error) {
            /* повреждённое значение — сбрасываем ниже */
        }
        storageRemove(window.localStorage, CITY_KEY);
        return null;
    }

    function saveCity(city) {
        const payload = {
            city: city.city,
            region: city.region || '',
            region_code: city.region_code || '',
            postal_code: city.postal_code || '',
            ts: Date.now(),
        };
        storageSet(window.localStorage, CITY_KEY, JSON.stringify(payload));
        setCookie(CITY_COOKIE, payload.city, COOKIE_MAX_AGE);
    }

    function getDetectedCity() {
        const raw = storageGet(window.sessionStorage, DETECTED_KEY);
        if (!raw) return null;
        try {
            const parsed = JSON.parse(raw);
            if (!parsed || !parsed.city || !parsed.ts) return null;
            if (Date.now() - parsed.ts > DETECTED_TTL) return null;
            return parsed;
        } catch (error) {
            return null;
        }
    }

    function isDeclined() {
        return (
            storageGet(window.sessionStorage, DECLINED_KEY) === '1' ||
            getCookie(DECLINED_COOKIE) === '1'
        );
    }

    function markDeclined() {
        storageSet(window.sessionStorage, DECLINED_KEY, '1');
        // Без max-age: кука живёт до закрытия браузера, общая для всех вкладок.
        setCookie(DECLINED_COOKIE, '1');
    }

    function wasPromptShown() {
        return storageGet(window.sessionStorage, PROMPT_SHOWN_KEY) === '1';
    }

    function markPromptShown() {
        storageSet(window.sessionStorage, PROMPT_SHOWN_KEY, '1');
    }

    // ── регистрация ──────────────────────────────────────────────────────────

    function fillRegisterInput() {
        const input = document.getElementById('geo-city-input');
        if (!input || input.value) return;

        const stored = getStoredCity();
        const city = stored ? stored.city : getCookie(CITY_COOKIE);
        if (city) {
            input.value = city;
        }
    }

    // ── окно ─────────────────────────────────────────────────────────────────

    function showPrompt(city, attempt) {
        attempt = attempt || 0;
        if (!overlay || !city || !city.city) return;
        if (isDeclined() || getStoredCity() || wasPromptShown()) return;

        // Не спорим с уже открытыми попапами — попробуем чуть позже.
        if (document.querySelector('.review_popup_overlay')) {
            if (attempt < 3) {
                window.setTimeout(function () {
                    showPrompt(city, attempt + 1);
                }, 4000);
            }
            return;
        }

        // Если вкладка в фоне — ждём, когда посетитель вернётся.
        if (document.visibilityState === 'hidden') {
            const onVisible = function () {
                document.removeEventListener('visibilitychange', onVisible);
                showPrompt(city, attempt);
            };
            document.addEventListener('visibilitychange', onVisible);
            return;
        }

        if (cityLabel) cityLabel.textContent = city.city;

        pendingCity = city;
        markPromptShown();
        lastFocused = document.activeElement;

        window.clearTimeout(hideTimer);
        overlay.hidden = false;
        // Принудительный reflow, чтобы сработала transition.
        void overlay.offsetWidth;
        overlay.classList.add('is-open');

        if (yesBtn) yesBtn.focus();
    }

    function hidePrompt() {
        if (!overlay) return;
        overlay.classList.remove('is-open');
        hideTimer = window.setTimeout(function () {
            overlay.hidden = true;
        }, 200);

        if (lastFocused && typeof lastFocused.focus === 'function') {
            lastFocused.focus();
        }
    }

    function confirmCity(city) {
        saveCity(city);
        hidePrompt();
        document.dispatchEvent(
            new CustomEvent('hairshop:city-confirmed', { detail: city })
        );
    }

    function declineCity() {
        markDeclined();
        hidePrompt();
    }

    // ── определение ──────────────────────────────────────────────────────────

    function detectCity() {
        if (getStoredCity() || isDeclined() || wasPromptShown()) return;

        const cached = getDetectedCity();
        if (cached) {
            window.setTimeout(function () {
                showPrompt(cached);
            }, SHOW_DELAY);
            return;
        }

        const failedUntil = Number(storageGet(window.sessionStorage, FAILED_KEY) || 0);
        if (failedUntil > Date.now()) return;

        const endpoint = document.body.dataset.geoCityUrl;
        if (!endpoint || typeof window.fetch !== 'function') return;

        window
            .fetch(endpoint, {
                method: 'GET',
                headers: { Accept: 'application/json' },
                credentials: 'same-origin',
            })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error('HTTP ' + response.status);
                }
                return response.json();
            })
            .then(function (data) {
                if (!data || !data.found || !data.city) {
                    storageSet(
                        window.sessionStorage,
                        FAILED_KEY,
                        String(Date.now() + FAILED_TTL)
                    );
                    return;
                }

                const city = {
                    city: data.city,
                    region: data.region || '',
                    region_code: data.region_code || '',
                    postal_code: data.postal_code || '',
                    ts: Date.now(),
                };
                storageSet(window.sessionStorage, DETECTED_KEY, JSON.stringify(city));

                window.setTimeout(function () {
                    showPrompt(city);
                }, SHOW_DELAY);
            })
            .catch(function () {
                storageSet(
                    window.sessionStorage,
                    FAILED_KEY,
                    String(Date.now() + FAILED_TTL)
                );
            });
    }

    function scheduleDetection() {
        const run = function () {
            if (getStoredCity() || isDeclined() || wasPromptShown()) return;
            detectCity();
        };

        if ('requestIdleCallback' in window) {
            window.setTimeout(function () {
                window.requestIdleCallback(run, { timeout: 2000 });
            }, DETECT_DELAY);
        } else {
            window.setTimeout(run, DETECT_DELAY);
        }
    }

    // ── события ──────────────────────────────────────────────────────────────

    function bindEvents() {
        if (!overlay) return;

        if (yesBtn) {
            yesBtn.addEventListener('click', function () {
                if (pendingCity) confirmCity(pendingCity);
                else hidePrompt();
                pendingCity = null;
            });
        }

        if (noBtn) noBtn.addEventListener('click', declineCity);
        if (closeBtn) closeBtn.addEventListener('click', declineCity);

        overlay.addEventListener('click', function (event) {
            if (event.target === overlay) declineCity();
        });

        document.addEventListener('keydown', function (event) {
            if (overlay.hidden) return;

            if (event.key === 'Escape') {
                event.preventDefault();
                declineCity();
                return;
            }

            // Простой focus trap внутри диалога.
            if (event.key === 'Tab') {
                const focusable = [closeBtn, yesBtn, noBtn].filter(Boolean);
                if (!focusable.length) return;

                const first = focusable[0];
                const last = focusable[focusable.length - 1];

                if (event.shiftKey && document.activeElement === first) {
                    event.preventDefault();
                    last.focus();
                } else if (!event.shiftKey && document.activeElement === last) {
                    event.preventDefault();
                    first.focus();
                }
            }
        });
    }

    function init() {
        fillRegisterInput();
        bindEvents();

        if (document.body.dataset.geoEnabled !== '1') return;
        if (!overlay) return;
        if (getStoredCity() || isDeclined() || wasPromptShown()) return;

        scheduleDetection();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
