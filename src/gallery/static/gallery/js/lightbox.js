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

    const closeButton = document.getElementById('lb-close');
    const backdrop = document.getElementById('lb-backdrop');

    const prevButton = document.getElementById('lb-prev');
    const nextButton = document.getElementById('lb-next');

    const detailContainer = document.getElementById(
        'lb-photo-detail',
    );

    let photos = [];
    let currentIndex = 0;
    let detailRequestController = null;


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
                title: element.dataset.photoTitle || '',
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
             * Some lightbox photos (for example system-managed post
             * attachments) are intentionally outside the regular gallery
             * detail endpoint for now. Keep the lightbox usable anyway.
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
             * Future comment partials will contain HTMX attributes.
             * Process dynamically inserted markup when HTMX is available.
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


    function render() {
        const photo = photos[currentIndex];

        if (!photo) {
            return;
        }

        lightbox.dataset.photoId = photo.id;

        if (image) {
            image.src = photo.url;

            /*
             * Title is kept only for image alt text.
             * It is not displayed in the lightbox UI.
             */
            image.alt = photo.title;
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
        document.body.classList.add('overflow-hidden');

        lightbox.scrollTop = 0;
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

        lightbox.scrollTo({
            top: 0,
            behavior: 'instant',
        });
    }


    function next() {
        if (photos.length <= 1) {
            return;
        }

        currentIndex = (
            currentIndex + 1
        ) % photos.length;

        render();

        lightbox.scrollTo({
            top: 0,
            behavior: 'instant',
        });
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