// src/gallery/static/gallery/js/lightbox.js

document.addEventListener('DOMContentLoaded', () => {
    initLightbox();
});


function initLightbox() {
    const lightbox = document.getElementById('lightbox');

    if (!lightbox) {
        return;
    }

    const scrollContainer = document.getElementById('lb-scroll');

    const image = document.getElementById('lb-img');
    const counter = document.getElementById('lb-counter');

    const closeButton = document.getElementById('lb-close');
    const backdrop = document.getElementById('lb-backdrop');

    const prevButton = document.getElementById('lb-prev');
    const nextButton = document.getElementById('lb-next');

    const photoStage = document.getElementById('lb-photo-stage');

    const detailContainer = document.getElementById(
        'lb-photo-detail',
    );

    let photos = [];
    let currentIndex = 0;
    let detailRequestController = null;

    let touchStartX = 0;
    let touchStartY = 0;

    const SWIPE_THRESHOLD = 50;


    function getPhotoElements(trigger) {
        const group = trigger.closest(
            '[data-lightbox-group]',
        );

        const root = group || document;

        return Array.from(
            root.querySelectorAll('.photo-thumb'),
        );
    }


    function collectPhotos(trigger) {
        const elements = getPhotoElements(trigger);

        photos = elements.map((element) => {
            return {
                id: element.dataset.photoId || '',
                url: element.dataset.photoUrl || '',
                description: element.dataset.photoDescription || '',
            };
        });

        return elements.indexOf(trigger);
    }


    function buildDetailUrl(photoId) {
        const template = (
            detailContainer?.dataset.detailUrlTemplate
            || ''
        );

        if (!template || !photoId) {
            return '';
        }

        /*
         * Django generated the template URL with photo_pk=0.
         * Replace only that path segment with the real photo id.
         */
        return template.replace(
            /\/0\/lightbox\/?$/,
            `/${photoId}/lightbox/`,
        );
    }


    function showDetailPlaceholder(message = '') {
        if (!detailContainer) {
            return;
        }

        detailContainer.innerHTML = `
            <div class="px-4 py-8 text-center text-sm text-slate-400 sm:px-6">
                ${message}
            </div>
        `;
    }


    async function loadPhotoDetail(photo) {
        detailRequestController?.abort();

        if (!detailContainer || !photo?.id) {
            return;
        }

        const url = buildDetailUrl(photo.id);

        if (!url) {
            return;
        }

        const controller = new AbortController();
        detailRequestController = controller;

        showDetailPlaceholder();

        try {
            const response = await fetch(
                url,
                {
                    method: 'GET',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    signal: controller.signal,
                },
            );

            /*
             * Some lightbox photos may intentionally be outside
             * the regular gallery detail endpoint.
             * Keep the lightbox usable anyway.
             */
            if (!response.ok) {
                showDetailPlaceholder();
                return;
            }

            const html = await response.text();

            /*
             * Ignore a response that finished after the user already
             * switched to another photo.
             */
            if (
                lightbox.dataset.photoId
                !== String(photo.id)
            ) {
                return;
            }

            detailContainer.innerHTML = html;

            /*
             * Process dynamically inserted HTMX markup when available.
             */
            window.htmx?.process(
                detailContainer,
            );

        } catch (error) {
            if (error.name === 'AbortError') {
                return;
            }

            console.error(
                '[lightbox] failed to load photo detail:',
                error,
            );

            showDetailPlaceholder();
        }
    }


    function scrollToTop() {
        if (!scrollContainer) {
            return;
        }

        scrollContainer.scrollTo({
            top: 0,
            behavior: 'auto',
        });
    }


    function render() {
        const photo = photos[currentIndex];

        if (!photo) {
            return;
        }

        lightbox.dataset.photoId = photo.id;

        if (image) {
            image.src = photo.url;
            image.alt = photo.description;
        }

        if (counter) {
            counter.textContent = (
                `${currentIndex + 1} / ${photos.length}`
            );
        }

        const hasMultiplePhotos = photos.length > 1;

        prevButton?.classList.toggle(
            'hidden',
            !hasMultiplePhotos,
        );

        nextButton?.classList.toggle(
            'hidden',
            !hasMultiplePhotos,
        );

        loadPhotoDetail(photo);
    }


    function open(trigger) {
        const index = collectPhotos(trigger);

        if (!photos.length || index < 0) {
            return;
        }

        currentIndex = index;

        render();

        lightbox.classList.remove('hidden');

        document.body.classList.add(
            'overflow-hidden',
        );

        scrollToTop();
    }


    function close() {
        detailRequestController?.abort();
        detailRequestController = null;

        lightbox.classList.add('hidden');

        document.body.classList.remove(
            'overflow-hidden',
        );

        lightbox.removeAttribute(
            'data-photo-id',
        );

        if (image) {
            image.src = '';
            image.alt = '';
        }

        photos = [];
        currentIndex = 0;

        showDetailPlaceholder();
    }


    function previous() {
        if (photos.length <= 1) {
            return;
        }

        currentIndex = (
            currentIndex - 1 + photos.length
        ) % photos.length;

        render();
        scrollToTop();
    }


    function next() {
        if (photos.length <= 1) {
            return;
        }

        currentIndex = (
            currentIndex + 1
        ) % photos.length;

        render();
        scrollToTop();
    }


    document.addEventListener('click', (event) => {
        const thumbnail = event.target.closest(
            '.photo-thumb',
        );

        if (!thumbnail) {
            return;
        }

        if (
            event.target.closest(
                '[data-media-reveal]',
            )
        ) {
            return;
        }

        if (
            thumbnail.querySelector(
                '.media-image.is-blurred',
            )
        ) {
            return;
        }

        event.preventDefault();

        open(thumbnail);
    });


    closeButton?.addEventListener(
        'click',
        close,
    );


    backdrop?.addEventListener(
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


    // ─── Touch swipe navigation ────────────────────────────────

    photoStage?.addEventListener(
        'touchstart',
        (event) => {
            if (event.touches.length !== 1) {
                return;
            }

            const touch = event.touches[0];

            touchStartX = touch.clientX;
            touchStartY = touch.clientY;
        },
        {
            passive: true,
        },
    );


    photoStage?.addEventListener(
        'touchend',
        (event) => {
            if (
                !touchStartX
                || event.changedTouches.length !== 1
            ) {
                return;
            }

            const touch = event.changedTouches[0];

            const deltaX = touch.clientX - touchStartX;
            const deltaY = touch.clientY - touchStartY;

            touchStartX = 0;
            touchStartY = 0;

            /*
             * Ignore short gestures and predominantly vertical movement.
             * Vertical gestures remain available for normal scrolling.
             */
            if (
                Math.abs(deltaX) < SWIPE_THRESHOLD
                || Math.abs(deltaX) <= Math.abs(deltaY)
            ) {
                return;
            }

            if (deltaX < 0) {
                next();
                return;
            }

            previous();
        },
        {
            passive: true,
        },
    );


    // ─── Keyboard navigation ───────────────────────────────────

    document.addEventListener('keydown', (event) => {
        if (
            lightbox.classList.contains(
                'hidden',
            )
        ) {
            return;
        }

        if (event.key === 'ArrowLeft') {
            event.preventDefault();
            previous();
            return;
        }

        if (event.key === 'ArrowRight') {
            event.preventDefault();
            next();
            return;
        }

        if (event.key === 'Escape') {
            event.preventDefault();
            close();
        }
    });
}