(function () {
    'use strict';

    var STORAGE_KEY = 'hairshop-theme';
    var root = document.documentElement;
    var buttons = Array.prototype.slice.call(document.querySelectorAll('[data-theme-toggle]'));
    var meta = document.querySelector('meta[name="theme-color"]');

    var META_LIGHT = '#4e3220';
    var META_DARK = '#15100d';

    function currentTheme() {
        return root.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
    }

    function updateControls(theme) {
        var isDark = theme === 'dark';

        buttons.forEach(function (button) {
            button.setAttribute('aria-pressed', isDark ? 'true' : 'false');

            var label = isDark ? 'Включить светлую тему' : 'Включить тёмную тему';
            button.setAttribute('aria-label', label);
            button.setAttribute('title', label);
        });

        if (meta) {
            meta.setAttribute('content', isDark ? META_DARK : META_LIGHT);
        }
    }

    function applyTheme(theme, persist) {
        var isDark = theme === 'dark';

        if (isDark) {
            root.setAttribute('data-theme', 'dark');
        } else {
            root.removeAttribute('data-theme');
        }

        root.style.colorScheme = isDark ? 'dark' : 'light';
        updateControls(theme);

        if (persist) {
            try {
                localStorage.setItem(STORAGE_KEY, theme);
            } catch (error) {
                /* Storage can be unavailable in private browsing. */
            }
        }
    }

    buttons.forEach(function (button) {
        button.addEventListener('click', function () {
            applyTheme(currentTheme() === 'dark' ? 'light' : 'dark', true);
        });
    });

    window.addEventListener('storage', function (event) {
        if (event.key === STORAGE_KEY) {
            applyTheme(event.newValue === 'dark' ? 'dark' : 'light', false);
        }
    });

    /* The head script has already applied the saved theme; sync the controls. */
    applyTheme(currentTheme(), false);
})();
