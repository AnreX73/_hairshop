document.addEventListener('DOMContentLoaded', function() {
const videos = document.querySelectorAll('.video-wrapper video');

    videos.forEach(video => {
        const wrapper = video.closest('.video-wrapper');
        const playBtn = wrapper.querySelector('.play-btn');

        // 1. Показываем кнопку, когда видео на паузе или закончилось
        video.addEventListener('pause', () => {
            wrapper.classList.remove('is-playing');
        });

        video.addEventListener('ended', () => {
            wrapper.classList.remove('is-playing');
            // Сбрасываем время в начало для повторного просмотра
            video.currentTime = 0; 
        });

        // 2. Скрываем кнопку, когда видео играет
        video.addEventListener('play', () => {
            wrapper.classList.add('is-playing');
        });

        // 3. Клик по видео (или кнопке) запускает/ставит на паузу
        // Важно: снимаем muted после первого взаимодействия пользователя
        wrapper.addEventListener('click', () => {
            if (video.paused || video.ended) {
                video.muted = false; // Включаем звук
                video.currentTime = 0; // Начинаем сначала
                video.play();
            } else {
                video.pause();
            }
        });
    });


const swiper = new Swiper('.swiper', {
  // Optional parameters
  direction: 'horizontal',

  
  
  

  // If we need pagination
  pagination: {
    el: '.swiper-pagination',
  },

  // Navigation arrows
  navigation: {
    nextEl: '.swiper-button-next',
    prevEl: '.swiper-button-prev',
  },

  loop: true,
  
});

 const banner = document.getElementById('startBanner');
    const overlay = document.getElementById('bannerOverlay');
    const closeBtn = document.getElementById('bannerClose');

    // Показываем только если в этой сессии ещё не закрывали
    if (banner && !sessionStorage.getItem('startBannerShown')) {
        banner.style.display = 'block';
    }

    const hideBanner = () => {
        banner.style.display = 'none';
        sessionStorage.setItem('startBannerShown', 'true');
    };

    if (closeBtn) closeBtn.addEventListener('click', hideBanner);
    if (overlay) overlay.addEventListener('click', hideBanner);

    

function initReviewSwiper() {
    // Уничтожаем предыдущий Swiper в попапе, если есть
    const swiperElement = document.querySelector('.reviewPopupSwiper');
    if (swiperElement && !swiperElement.swiper) {
        new Swiper(swiperElement, {
            slidesPerView: 1,
            spaceBetween: 10,
            loop: true,
            pagination: {
                el: '.swiper-pagination',
                clickable: true,
            },
            navigation: {
                nextEl: '.swiper-button-next',
                prevEl: '.swiper-button-prev',
            },
        });
    }
}

// Закрытие по Escape
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const overlay = document.querySelector('.review_popup_overlay');
        if (overlay) overlay.remove();
    }
});
   

 

}); // конец DOMContentLoaded

(function() {
    console.log('IIFE запустился');
    const mediaDropzone = document.getElementById('media-dropzone');
    console.log('mediaDropzone:', mediaDropzone);
    if (!mediaDropzone) return;
    // ...
})();

   // ── Медиа-менеджер товара (страница /products/<id>/media/) ──────────────
    const mediaDropzone = document.getElementById('media-dropzone');
    if (mediaDropzone) {  // инициализируем только если элемент есть на странице

        Dropzone.autoDiscover = false;

        const _urls      = document.getElementById('js-urls').dataset;
        const CSRF_TOKEN = document.querySelector('[name=csrfmiddlewaretoken]')
                           ? document.querySelector('[name=csrfmiddlewaretoken]').value
                           : getCookie('csrftoken');

        function buildUrl(template, id) {
            return template.replace('/0/', `/${id}/`);
        }

        // Вспомогательная функция чтения CSRF из куки (если нет input на странице)
        function getCookie(name) {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
        }

        // ── Dropzone ──────────────────────────────────────────────────────────
        const dz = new Dropzone('#media-dropzone', {
            url: _urls.upload,
            headers: { 'X-CSRFToken': CSRF_TOKEN },
            paramName: 'file',
            maxFilesize: 100,
            acceptedFiles: 'image/jpeg,image/png,image/webp,image/gif,video/mp4,video/quicktime,video/x-msvideo,video/webm',
            addRemoveLinks: false,
            previewsContainer: false,
            parallelUploads: 2,
            clickable: true,

            init() {
                const progressWrap = document.getElementById('upload-progress');
                const progressFill = document.getElementById('progress-fill');
                const progressText = document.getElementById('progress-text');

                this.on('uploadprogress', (file, progress) => {
                    progressWrap.classList.remove('hidden');
                    progressFill.style.width = progress + '%';
                    progressText.textContent = `Загрузка: ${Math.round(progress)}%`;
                });

                this.on('success', (file, response) => {
                    const empty = document.getElementById('empty-placeholder');
                    if (empty) empty.remove();

                    htmx.ajax(
                        'GET',
                        buildUrl(_urls.partialBase, response.id),
                        { target: '#media-grid', swap: 'beforeend' }
                    );

                    updateMediaCount(1);
                    this.removeFile(file);
                    progressWrap.classList.add('hidden');
                    progressFill.style.width = '0%';
                });

                this.on('error', (file, msg) => {
                    progressWrap.classList.add('hidden');
                    alert('Ошибка загрузки: ' + (typeof msg === 'string' ? msg : msg.error || 'неизвестная ошибка'));
                    this.removeFile(file);
                });
            }
        });

        // ── SortableJS ────────────────────────────────────────────────────────
        const grid = document.getElementById('media-grid');
        Sortable.create(grid, {
            animation: 200,
            handle: '.drag-handle',
            ghostClass: 'sortable-ghost',
            chosenClass: 'sortable-chosen',
            onEnd() {
                const ids = [...grid.querySelectorAll('[data-media-id]')]
                    .map(el => parseInt(el.dataset.mediaId));
                fetch(_urls.reorder, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': CSRF_TOKEN,
                    },
                    body: JSON.stringify({ order: ids }),
                });
            }
        });

        // ── Удаление (глобальная функция, вызывается из onclick в шаблоне) ──
        window.deleteMedia = function(mediaId, btn) {
            if (!confirm('Удалить этот файл?')) return;
            fetch(buildUrl(_urls.deleteBase, mediaId), {
                method: 'POST',
                headers: { 'X-CSRFToken': CSRF_TOKEN },
            }).then(r => {
                if (r.ok) {
                    btn.closest('.media-item').remove();
                    updateMediaCount(-1);
                    if (grid.querySelectorAll('.media-item').length === 0) {
                        grid.innerHTML = '<div class="media-empty" id="empty-placeholder">Пока нет файлов.</div>';
                    }
                }
            });
        };

        // ── Счётчик файлов ────────────────────────────────────────────────────
        function updateMediaCount(delta) {
            const el = document.getElementById('media-count');
            const next = (parseInt(el.textContent) || 0) + delta;
            const forms = ['файл', 'файла', 'файлов'];
            const n = Math.abs(next) % 100, n1 = n % 10;
            const form = (n > 10 && n < 20) ? forms[2]
                       : n1 === 1            ? forms[0]
                       : (n1 >= 2 && n1 <= 4) ? forms[1]
                       : forms[2];
            el.textContent = `${next} ${form}`;
        }

    } // конец if (mediaDropzone)

// ── Медиа к отзыву ───────────────────────────────────────────────────────────
(function() {
    const reviewDropzone = document.getElementById('review-dropzone');
    if (!reviewDropzone) return;

    Dropzone.autoDiscover = false;

    const _urls      = document.getElementById('js-review-urls').dataset;
    const CSRF_TOKEN = getCookie('csrftoken');

    // getCookie уже определена выше в файле — если нет, добавь:
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }

    function buildUrl(template, id) {
        return template.replace('/0/', `/${id}/`);
    }

    // Счётчики фото/видео из уже загруженных
    const grid = document.getElementById('review-media-grid');
    let photoCount = [...grid.querySelectorAll('[data-media-type="photo"]')].length;
    let videoCount = [...grid.querySelectorAll('[data-media-type="video"]')].length;

    function updateLimitCounters() {
        const pc = document.getElementById('photo-count');
        const vc = document.getElementById('video-count');
        if (pc) pc.textContent = photoCount;
        if (vc) vc.textContent = videoCount;
    }
    updateLimitCounters();

        const dz = new Dropzone('#review-dropzone', {
        url: _urls.upload,
        headers: { 'X-CSRFToken': CSRF_TOKEN },
        paramName: 'file',
        maxFilesize: 100,
        acceptedFiles: 'image/jpeg,image/png,image/webp,video/mp4,video/quicktime,video/x-msvideo',
        addRemoveLinks: false,
        previewsContainer: false,
        parallelUploads: 1,
        clickable: true,
        autoProcessQueue: true,
        dictDefaultMessage: '',
        dictFallbackMessage: '',
        dictFileTooBig: 'Файл слишком большой ({{filesize}}MB). Максимум {{maxFilesize}}MB.',
        dictInvalidFileType: 'Недопустимый тип файла.',
        dictResponseError: '',  // ← это отключает встроенный alert при ошибке сервера
        // ...

        init() {
            const progressWrap = document.getElementById('upload-progress');
            const progressFill = document.getElementById('progress-fill');
            const progressText = document.getElementById('progress-text');

            this.on('uploadprogress', (file, progress) => {
                progressWrap.classList.remove('hidden');
                progressFill.style.width = progress + '%';
                progressText.textContent = `Загрузка: ${Math.round(progress)}%`;
            });

            this.on('success', (file, response) => {
                const empty = document.getElementById('review-empty');
                if (empty) empty.remove();

                htmx.ajax(
                    'GET',
                    buildUrl(_urls.partialBase, response.id),
                    { target: '#review-media-grid', swap: 'beforeend' }
                );

                if (response.media_type === 'photo') photoCount++;
                else videoCount++;
                updateLimitCounters();

                this.removeFile(file);
                progressWrap.classList.add('hidden');
                progressFill.style.width = '0%';
            });

            this.on('error', (file, msg) => {
    console.log('Dropzone error msg:', msg);  // ← временно
    progressWrap.classList.add('hidden');
    const errMsg = typeof msg === 'string' ? msg : msg.error || 'Ошибка загрузки';
    this.on('error', (file, msg) => {
    progressWrap.classList.add('hidden');
    const errMsg = typeof msg === 'string' ? msg : msg.error || 'Ошибка загрузки';
    
    const errorBlock = document.getElementById('upload-error');
    const errorText = document.getElementById('upload-error-text');
    if (errorBlock && errorText) {
        errorText.textContent = errMsg;
        errorBlock.classList.remove('hidden');
        setTimeout(() => errorBlock.classList.add('hidden'), 4000);
    }
    this.removeFile(file);
});
    this.removeFile(file);
});
        }
    });

    window.deleteReviewMedia = function(mediaId, btn) {
        if (!confirm('Удалить файл?')) return;
        fetch(buildUrl(_urls.deleteBase, mediaId), {
            method: 'POST',
            headers: { 'X-CSRFToken': CSRF_TOKEN },
        }).then(r => {
            if (r.ok) {
                const item = btn.closest('.media-item');
                if (item.dataset.mediaType === 'photo') photoCount--;
                else videoCount--;
                item.remove();
                updateLimitCounters();
            }
        });
    };

})();
document.body.addEventListener('htmx:beforeRequest', function(e) {
    if (e.detail.target.id === 'catalog-section') {
        document.querySelector('.products-grid')?.classList.add('loading');
    }
});

document.body.addEventListener('htmx:afterSwap', function(e) {
    if (e.detail.target.id === 'catalog-section') {
        setTimeout(() => {
            document.querySelectorAll('.product-card').forEach((card, i) => {
                card.style.animationDelay = `${i * 30}ms`;
                card.classList.add('card-enter');
            });
        }, 10);
    }
});

