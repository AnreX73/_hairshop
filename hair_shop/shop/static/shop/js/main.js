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

    
    // переписать с переменной во избежании множественных вызовов
    const categorySelect = document.getElementById('id_category');
    if (categorySelect) {
        categorySelect.addEventListener('change', function() {
        const categoryId = this.value;
        if (categoryId) {
            window.location.href = `/catalog/${categoryId}/`;
        } else {
            window.location.href = `/catalog/`;
        }
    });
    }


   


});
