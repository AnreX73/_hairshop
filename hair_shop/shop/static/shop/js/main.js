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

  document.getElementById('id_category').addEventListener('change', function() {
        const categoryId = this.value;
        if (categoryId) {
            window.location.href = `/catalog/${categoryId}/`;
        } else {
            window.location.href = `/catalog/`;
        }
    });

});
