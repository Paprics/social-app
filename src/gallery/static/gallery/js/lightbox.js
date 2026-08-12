// src/gallery/static/gallery/js/lightbox.js

document.addEventListener('DOMContentLoaded', () => {
    initLightbox();
});


function initLightbox() {
    const lightbox = document.getElementById('lightbox');

    if (!lightbox) {
        return;
    }

    const image = document.getElementById('lb-img');
    const counter = document.getElementById('lb-counter');
    const title = document.getElementById('lb-title');

    const closeButton = document.getElementById('lb-close');
    const prevButton = document.getElementById('lb-prev');
    const nextButton = document.getElementById('lb-next');

    const commentsToggle = document.getElementById(
        'lb-scroll-comments',
    );

    const commentsSection = document.getElementById(
        'lb-comments-section',
    );

    let photos = [];
    let currentIndex = 0;

    function collectPhotos() {
        photos = Array.from(
            document.querySelectorAll('.photo-thumb'),
        ).map((button) => {
            return {
                url: button.dataset.photoUrl,
                title: button.dataset.photoTitle || '',
                id: button.dataset.photoId,
            };
        });
    }

    function open(index) {
        collectPhotos();

        if (!photos.length) {
            return;
        }

        currentIndex = Math.max(
            0,
            Math.min(
                index,
                photos.length - 1,
            ),
        );

        render();

        lightbox.classList.remove('hidden');
        document.body.classList.add('overflow-hidden');
    }

    function close() {
        lightbox.classList.add('hidden');
        document.body.classList.remove('overflow-hidden');

        if (image) {
            image.src = '';
        }
    }

    function render() {
        const photo = photos[currentIndex];

        if (!photo) {
            return;
        }

        if (image) {
            image.src = photo.url;
            image.alt = photo.title;
        }

        if (title) {
            title.textContent = photo.title;
        }

        if (counter) {
            counter.textContent = (
                `${currentIndex + 1} / ${photos.length}`
            );
        }

        [
            'lb-likes',
            'lb-views',
            'lb-favorites',
            'lb-comments-count',
        ].forEach((id) => {
            const element = document.getElementById(id);

            if (element) {
                element.textContent = '0';
            }
        });

        commentsSection?.classList.add('hidden');

        prevButton?.classList.toggle(
            'invisible',
            photos.length <= 1,
        );

        nextButton?.classList.toggle(
            'invisible',
            photos.length <= 1,
        );
    }

    function previous() {
        if (!photos.length) {
            return;
        }

        currentIndex = (
            currentIndex - 1 + photos.length
        ) % photos.length;

        render();
    }

    function next() {
        if (!photos.length) {
            return;
        }

        currentIndex = (
            currentIndex + 1
        ) % photos.length;

        render();
    }

    document.addEventListener('click', (event) => {
        const thumbnail = event.target.closest('.photo-thumb');

        if (!thumbnail) {
            return;
        }

        event.preventDefault();

        const index = parseInt(
            thumbnail.dataset.photoIndex,
            10,
        );

        open(
            Number.isNaN(index)
                ? 0
                : index,
        );
    });

    closeButton?.addEventListener(
        'click',
        close,
    );

    prevButton?.addEventListener(
        'click',
        previous,
    );

    nextButton?.addEventListener(
        'click',
        next,
    );

    lightbox.addEventListener('click', (event) => {
        if (event.target === lightbox) {
            close();
        }
    });

    if (commentsToggle && commentsSection) {
        commentsToggle.addEventListener('click', () => {
            commentsSection.classList.toggle('hidden');
        });
    }

    document.addEventListener('keydown', (event) => {
        if (lightbox.classList.contains('hidden')) {
            return;
        }

        if (event.key === 'ArrowLeft') {
            previous();
            return;
        }

        if (event.key === 'ArrowRight') {
            next();
            return;
        }

        if (event.key === 'Escape') {
            close();
        }
    });
}