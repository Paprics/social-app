// src/posts/static/posts/js/post_form.js

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-post-form]').forEach((form) => {
        initPostForm(form);
    });
});


function initPostForm(form) {
    if (form.dataset.postFormInitialized === 'true') {
        return;
    }

    form.dataset.postFormInitialized = 'true';

    const fileInput = form.querySelector(
        '[data-post-photo-input]',
    );

    const previewSection = form.querySelector(
        '[data-post-photo-preview-section]',
    );

    const preview = form.querySelector(
        '[data-post-photo-preview]',
    );

    const counter = form.querySelector(
        '[data-post-photo-count]',
    );

    const clearButton = form.querySelector(
        '[data-post-photo-clear]',
    );

    const errorBox = form.querySelector(
        '[data-post-photo-error]',
    );

    const contentInput = form.querySelector(
        '[name="content"]',
    );

    const maxPhotos = Number.parseInt(
        form.dataset.maxPhotos || '10',
        10,
    );

    const maxPhotoSize = Number.parseInt(
        form.dataset.maxPhotoSizeBytes || '5242880',
        10,
    );

    let selectedFiles = [];
    let previewUrls = [];


    function showError(message) {
        if (!errorBox) {
            return;
        }

        errorBox.textContent = message;
        errorBox.classList.remove('hidden');
    }


    function clearError() {
        if (!errorBox) {
            return;
        }

        errorBox.textContent = '';
        errorBox.classList.add('hidden');
    }


    function getServerError(xhr) {
        const fallbackMessage = (
            'Failed to publish post.'
        );

        if (!xhr?.responseText) {
            return fallbackMessage;
        }

        try {
            const data = JSON.parse(
                xhr.responseText,
            );

            if (
                typeof data.error === 'string'
                && data.error.trim()
            ) {
                return data.error;
            }

            return fallbackMessage;

        } catch (error) {
            console.error(
                '[post-form] failed to parse server error:',
                error,
            );

            return fallbackMessage;
        }
    }


    function revokePreviewUrls() {
        previewUrls.forEach((url) => {
            URL.revokeObjectURL(url);
        });

        previewUrls = [];
    }


    function syncInputFiles() {
        if (!fileInput) {
            return;
        }

        const transfer = new DataTransfer();

        selectedFiles.forEach((file) => {
            transfer.items.add(file);
        });

        fileInput.files = transfer.files;
    }


    function updateCounter() {
        if (!counter) {
            return;
        }

        counter.textContent = (
            `${selectedFiles.length} / ${maxPhotos}`
        );
    }


    function createRemoveButton(index) {
        const button = document.createElement('button');

        button.type = 'button';
        button.dataset.postPhotoRemove = String(index);

        button.setAttribute(
            'aria-label',
            preview?.dataset.removeLabel || 'Remove photo',
        );

        button.className = [
            'absolute',
            'right-1',
            'top-1',
            'flex',
            'h-7',
            'w-7',
            'items-center',
            'justify-center',
            'rounded-full',
            'bg-black/60',
            'text-white',
            'shadow-sm',
            'transition',
            'hover:bg-black/80',
            'focus:outline-none',
            'focus:ring-2',
            'focus:ring-white',
        ].join(' ');

        button.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg"
                 class="h-4 w-4"
                 viewBox="0 0 24 24"
                 fill="none"
                 stroke="currentColor"
                 stroke-width="2"
                 stroke-linecap="round"
                 stroke-linejoin="round"
                 aria-hidden="true">
                <line x1="18"
                      y1="6"
                      x2="6"
                      y2="18">
                </line>
                <line x1="6"
                      y1="6"
                      x2="18"
                      y2="18">
                </line>
            </svg>
        `;

        return button;
    }


    function renderPreview() {
        if (!preview || !previewSection) {
            return;
        }

        revokePreviewUrls();
        preview.replaceChildren();

        updateCounter();

        if (!selectedFiles.length) {
            previewSection.classList.add('hidden');
            return;
        }

        previewSection.classList.remove('hidden');

        selectedFiles.forEach((file, index) => {
            const url = URL.createObjectURL(file);

            previewUrls.push(url);

            const wrapper = document.createElement('div');

            wrapper.className = [
                'relative',
                'aspect-square',
                'overflow-hidden',
                'rounded-lg',
                'border',
                'border-slate-200',
                'bg-slate-100',
            ].join(' ');

            const image = document.createElement('img');

            image.src = url;
            image.alt = file.name;
            image.className = 'h-full w-full object-cover';

            wrapper.append(
                image,
                createRemoveButton(index),
            );

            preview.appendChild(wrapper);
        });
    }


    function fileIdentity(file) {
        return [
            file.name,
            file.size,
            file.lastModified,
        ].join(':');
    }


    function validateFile(file) {
        if (
            file.type
            && !file.type.startsWith('image/')
        ) {
            return {
                valid: false,
                message: (
                    `${file.name}: `
                    + (
                        form.dataset.invalidPhotoMessage
                        || 'The selected file is not an image.'
                    )
                ),
            };
        }

        if (file.size > maxPhotoSize) {
            return {
                valid: false,
                message: (
                    `${file.name}: `
                    + (
                        form.dataset.photoTooLargeMessage
                        || 'The selected photo is larger than 5 MB.'
                    )
                ),
            };
        }

        return {
            valid: true,
        };
    }


    function addFiles(files) {
        clearError();

        const existingFiles = new Set(
            selectedFiles.map(fileIdentity),
        );

        const validNewFiles = [];
        let firstError = null;

        for (const file of files) {
            const identity = fileIdentity(file);

            if (existingFiles.has(identity)) {
                continue;
            }

            const validation = validateFile(file);

            if (!validation.valid) {
                if (!firstError) {
                    firstError = validation.message;
                }

                continue;
            }

            existingFiles.add(identity);
            validNewFiles.push(file);
        }

        const availableSlots = (
            maxPhotos - selectedFiles.length
        );

        if (validNewFiles.length > availableSlots) {
            if (!firstError) {
                firstError = (
                    form.dataset.tooManyPhotosMessage
                    || `You can attach up to ${maxPhotos} photos.`
                );
            }
        }

        selectedFiles.push(
            ...validNewFiles.slice(
                0,
                Math.max(availableSlots, 0),
            ),
        );

        if (firstError) {
            showError(firstError);
        }

        syncInputFiles();
        renderPreview();
    }


    function removeFile(index) {
        if (
            index < 0
            || index >= selectedFiles.length
        ) {
            return;
        }

        selectedFiles.splice(
            index,
            1,
        );

        clearError();
        syncInputFiles();
        renderPreview();
    }


    function clearPhotos() {
        selectedFiles = [];

        clearError();
        syncInputFiles();
        renderPreview();
    }


    function resetForm() {
        form.reset();

        selectedFiles = [];

        clearError();
        revokePreviewUrls();

        preview?.replaceChildren();
        previewSection?.classList.add('hidden');

        updateCounter();
    }


    fileInput?.addEventListener(
        'change',
        () => {
            const files = Array.from(
                fileInput.files || [],
            );

            if (!files.length) {
                return;
            }

            addFiles(files);
        },
    );


    preview?.addEventListener(
        'click',
        (event) => {
            const button = event.target.closest(
                '[data-post-photo-remove]',
            );

            if (!button) {
                return;
            }

            const index = Number.parseInt(
                button.dataset.postPhotoRemove,
                10,
            );

            if (Number.isNaN(index)) {
                return;
            }

            removeFile(index);
        },
    );


    clearButton?.addEventListener(
        'click',
        clearPhotos,
    );


    contentInput?.addEventListener(
        'input',
        clearError,
    );


    form.addEventListener(
        'htmx:beforeRequest',
        () => {
            clearError();
        },
    );


    form.addEventListener(
        'htmx:responseError',
        (event) => {
            showError(
                getServerError(
                    event.detail.xhr,
                ),
            );
        },
    );


    form.addEventListener(
        'htmx:afterRequest',
        (event) => {
            if (!event.detail.successful) {
                return;
            }

            resetForm();

            document
                .getElementById('wall-empty-state')
                ?.remove();
        },
    );


    window.addEventListener(
        'beforeunload',
        revokePreviewUrls,
    );
}