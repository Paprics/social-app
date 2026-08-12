// src/users/static/users/js/profile/avatar.js

(function () {
    'use strict';

    let selectedPhotoId = null;
    let previewUrl = null;

    // ─── Modal ─────────────────────────────────────────────────────

    function closeModal() {
        clearPreview();

        const container = document.getElementById('avatar-modal-container');

        if (container) {
            container.innerHTML = '';
        }

        selectedPhotoId = null;
        document.body.classList.remove('overflow-hidden');
    }

    // ─── CSRF ──────────────────────────────────────────────────────

    function getCsrfToken() {
        const modal = document.getElementById('avatar-modal');

        if (!modal) {
            return '';
        }

        const input = modal.querySelector(
            '[name="csrfmiddlewaretoken"]',
        );

        return input ? input.value : '';
    }

    // ─── HTTP ──────────────────────────────────────────────────────

    async function parseResponse(response) {
        if (response.status === 204) {
            return null;
        }

        const contentType = response.headers.get('content-type') || '';

        if (!contentType.includes('application/json')) {
            return null;
        }

        try {
            return await response.json();
        } catch {
            return null;
        }
    }

    async function post(url, formData) {
        const response = await fetch(url, {
            method: 'POST',
            body: formData,
        });

        const data = await parseResponse(response);

        if (!response.ok) {
            const message = (
                data?.message
                || data?.error
                || `HTTP ${response.status}`
            );

            const error = new Error(message);

            error.status = response.status;
            error.data = data;

            throw error;
        }

        return data;
    }

    // ─── Error message ──────────────────────────────────────────────

    function clearError() {
        const errorBox = document.getElementById('avatar-error');

        if (!errorBox) {
            return;
        }

        errorBox.textContent = '';
        errorBox.classList.add('hidden');
    }

    function showError(message) {
        const errorBox = document.getElementById('avatar-error');

        if (!errorBox) {
            return;
        }

        errorBox.textContent = message;
        errorBox.classList.remove('hidden');
    }

    // ─── Set button ────────────────────────────────────────────────

    function updateSetButton() {
        const button = document.getElementById('avatar-set-btn');
        const input = document.getElementById('avatar-file-input');

        if (!button) {
            return;
        }

        const hasFile = Boolean(input?.files?.length);

        button.disabled = !hasFile && !selectedPhotoId;
    }

    function setButtonLoading(button, text = 'Saving...') {
        if (!button.dataset.originalText) {
            button.dataset.originalText = button.textContent.trim();
        }

        button.disabled = true;
        button.textContent = text;
    }

    function restoreSetButton(button) {
        if (button.dataset.originalText) {
            button.textContent = button.dataset.originalText;
        }

        updateSetButton();
    }

    // ─── Existing photo selection ──────────────────────────────────

    function clearSelectedPhoto() {
        document.querySelectorAll('.avatar-photo-btn').forEach((button) => {
            button.classList.remove('border-blue-500');
            button.classList.add('border-transparent');
            button.setAttribute('aria-pressed', 'false');
        });
    }

    function resetSelectedPhoto() {
        selectedPhotoId = null;

        clearSelectedPhoto();
        updateSetButton();
    }

    function selectPhoto(button) {
        clearError();
        clearSelectedPhoto();
        clearFileSelection();

        button.classList.remove('border-transparent');
        button.classList.add('border-blue-500');
        button.setAttribute('aria-pressed', 'true');

        selectedPhotoId = button.dataset.photoId || null;

        updateSetButton();
    }

    // ─── Upload preview ─────────────────────────────────────────────

    function clearPreview() {
        if (previewUrl) {
            URL.revokeObjectURL(previewUrl);
            previewUrl = null;
        }

        const preview = document.getElementById('avatar-upload-preview');
        const image = document.getElementById('avatar-upload-preview-img');
        const name = document.getElementById('avatar-upload-preview-name');

        if (preview) {
            preview.classList.add('hidden');
            preview.classList.remove('flex');
        }

        if (image) {
            image.removeAttribute('src');
        }

        if (name) {
            name.textContent = '';
        }
    }

    function clearFileSelection() {
        const input = document.getElementById('avatar-file-input');

        if (input) {
            input.value = '';
        }

        clearPreview();
    }

    function selectFile(input) {
        clearError();

        const file = input.files?.[0];

        if (!file) {
            clearPreview();
            updateSetButton();
            return;
        }

        selectedPhotoId = null;

        clearSelectedPhoto();
        clearPreview();

        const preview = document.getElementById('avatar-upload-preview');
        const image = document.getElementById('avatar-upload-preview-img');
        const name = document.getElementById('avatar-upload-preview-name');

        if (!preview || !image) {
            updateSetButton();
            return;
        }

        previewUrl = URL.createObjectURL(file);
        image.src = previewUrl;

        if (name) {
            name.textContent = file.name;
        }

        preview.classList.remove('hidden');
        preview.classList.add('flex');

        updateSetButton();
    }

    // ─── Set avatar ────────────────────────────────────────────────

    async function setAvatar(button) {
        if (button.disabled) {
            return;
        }

        clearError();

        const input = document.getElementById('avatar-file-input');
        const file = input?.files?.[0];

        const formData = new FormData();

        formData.append(
            'csrfmiddlewaretoken',
            getCsrfToken(),
        );

        try {
            // Upload new photo.
            // Existing upload behaviour remains unchanged.
            if (file) {
                setButtonLoading(
                    button,
                    'Uploading...',
                );

                formData.append(
                    'photo',
                    file,
                );

                await post(
                    button.dataset.uploadUrl,
                    formData,
                );

                window.location.reload();
                return;
            }

            // Set an existing photo.
            if (selectedPhotoId) {
                setButtonLoading(
                    button,
                    'Saving...',
                );

                formData.append(
                    'photo_id',
                    selectedPhotoId,
                );

                const data = await post(
                    button.dataset.setUrl,
                    formData,
                );

                if (!data?.ok) {
                    throw new Error(
                        data?.message || 'Failed to update profile photo.',
                    );
                }

                window.location.reload();
                return;
            }

            restoreSetButton(button);

        } catch (error) {
            console.error(
                'Avatar update failed:',
                error,
            );

            showError(
                error.message || 'Failed to update profile photo.',
            );

            restoreSetButton(button);
        }
    }

    // ─── Remove avatar ─────────────────────────────────────────────

    async function removeAvatar(button) {
        clearError();

        const formData = new FormData();

        formData.append(
            'csrfmiddlewaretoken',
            getCsrfToken(),
        );

        button.disabled = true;

        try {
            await post(
                button.dataset.removeUrl,
                formData,
            );

            window.location.reload();

        } catch (error) {
            console.error(
                'Avatar remove failed:',
                error,
            );

            showError(
                error.message || 'Failed to remove profile photo.',
            );

            button.disabled = false;
        }
    }

    // ─── Click events ──────────────────────────────────────────────

    document.addEventListener('click', (event) => {
        if (event.target.closest('[data-avatar-modal-close]')) {
            event.preventDefault();

            closeModal();
            return;
        }

        const modal = document.getElementById('avatar-modal');

        if (event.target === modal) {
            closeModal();
            return;
        }

        const photoButton = event.target.closest('.avatar-photo-btn');

        if (photoButton) {
            event.preventDefault();

            selectPhoto(photoButton);
            return;
        }

        const setButton = event.target.closest('#avatar-set-btn');

        if (setButton) {
            event.preventDefault();

            setAvatar(setButton);
            return;
        }

        const removeButton = event.target.closest('#avatar-remove-btn');

        if (removeButton) {
            event.preventDefault();

            removeAvatar(removeButton);
        }
    });

    // ─── File input ────────────────────────────────────────────────

    document.addEventListener('change', (event) => {
        if (event.target.id === 'avatar-file-input') {
            selectFile(event.target);
        }
    });

    // ─── Keyboard ──────────────────────────────────────────────────

    document.addEventListener('keydown', (event) => {
        if (
            event.key === 'Escape'
            && document.getElementById('avatar-modal')
        ) {
            closeModal();
        }
    });

    // ─── HTMX ──────────────────────────────────────────────────────

    document.addEventListener('htmx:afterSwap', (event) => {
        const target = event.detail?.target;

        if (!target) {
            return;
        }

        // Modal was loaded into its container.
        if (target.id === 'avatar-modal-container') {
            selectedPhotoId = null;

            document.body.classList.add('overflow-hidden');
            clearError();
            updateSetButton();

            return;
        }

        // Previous/Next replaced the current photo page.
        if (target.id === 'avatar-photo-page') {
            clearError();
            resetSelectedPhoto();
        }
    });
})();