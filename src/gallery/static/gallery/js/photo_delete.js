// src/gallery/static/gallery/js/photo_delete.js

document.addEventListener('DOMContentLoaded', () => {
    initPhotoDelete();
});


function initPhotoDelete() {
    document.addEventListener('click', async (event) => {
        const button = event.target.closest('[data-js-delete-photo]');

        if (!button) {
            return;
        }

        event.preventDefault();

        const url = button.dataset.deleteUrl;

        if (!url) {
            return;
        }

        if (!confirm('Delete this photo?')) {
            return;
        }

        const csrf = document.querySelector(
            '[name=csrfmiddlewaretoken]',
        );

        button.disabled = true;

        try {
            const response = await fetch(
                url,
                {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrf?.value || '',
                        'HX-Request': 'true',
                    },
                },
            );

            if (!response.ok) {
                throw new Error(
                    `Delete failed: ${response.status}`,
                );
            }

            window.location.reload();

        } catch (error) {
            console.error(
                '[gallery] Delete failed:',
                error,
            );

            button.disabled = false;
        }
    });
}