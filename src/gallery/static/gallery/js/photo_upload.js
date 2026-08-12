// src/gallery/static/gallery/js/photo_upload.js

document.addEventListener('DOMContentLoaded', () => {
    initPhotoUpload();
});


function initPhotoUpload() {
    const modal = document.getElementById('upload-modal');

    if (!modal) {
        return;
    }

    const dropzone = document.getElementById('upload-dropzone');
    const fileInput = document.getElementById('upload-file-input');
    const preview = document.getElementById('upload-preview');
    const submitButton = document.getElementById('upload-submit-btn');
    const counter = document.getElementById('upload-counter');

    const remainingSlots = Number.parseInt(
        modal.dataset.remainingSlots || '0',
        10,
    );

    let selectedFiles = [];

    document.querySelectorAll('[js-open-upload-modal]').forEach((button) => {
        button.addEventListener('click', openModal);
    });

    document.querySelectorAll('[js-close-upload-modal]').forEach((button) => {
        button.addEventListener('click', closeModal);
    });

    modal.addEventListener('click', (event) => {
        if (event.target === modal) {
            closeModal();
        }
    });

    document.addEventListener('keydown', (event) => {
        if (
            event.key === 'Escape'
            && !modal.classList.contains('hidden')
        ) {
            closeModal();
        }
    });

    if (dropzone) {
        dropzone.addEventListener('dragover', (event) => {
            event.preventDefault();

            dropzone.classList.add(
                'border-blue-500',
                'bg-blue-50',
            );
        });

        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove(
                'border-blue-500',
                'bg-blue-50',
            );
        });

        dropzone.addEventListener('drop', (event) => {
            event.preventDefault();

            dropzone.classList.remove(
                'border-blue-500',
                'bg-blue-50',
            );

            handleFiles(
                Array.from(event.dataTransfer.files),
            );
        });

        dropzone.addEventListener('click', () => {
            fileInput?.click();
        });
    }

    fileInput?.addEventListener('change', () => {
        handleFiles(
            Array.from(fileInput.files),
        );
    });

    submitButton?.addEventListener('click', uploadFiles);


    function openModal() {
        modal.classList.remove('hidden');
        document.body.classList.add('overflow-hidden');
    }


    function closeModal() {
        modal.classList.add('hidden');
        document.body.classList.remove('overflow-hidden');

        reset();
    }


    function handleFiles(files) {
        const images = files.filter((file) => {
            return file.type.startsWith('image/');
        });

        selectedFiles = [
            ...selectedFiles,
            ...images,
        ].slice(
            0,
            remainingSlots,
        );

        renderPreview();
        updateCounter();
    }


    function renderPreview() {
        if (!preview) {
            return;
        }

        preview.innerHTML = '';

        if (!selectedFiles.length) {
            preview.classList.add('hidden');

            if (submitButton) {
                submitButton.disabled = true;
            }

            return;
        }

        preview.classList.remove('hidden');

        if (submitButton) {
            submitButton.disabled = false;
        }

        selectedFiles.forEach((file, index) => {
            const reader = new FileReader();

            reader.onload = (event) => {
                const wrapper = document.createElement('div');

                wrapper.className = [
                    'relative',
                    'aspect-square',
                    'overflow-hidden',
                    'rounded-lg',
                    'border',
                    'border-slate-200',
                    'bg-slate-100',
                    'group',
                ].join(' ');

                wrapper.innerHTML = `
                    <img
                        src="${event.target.result}"
                        class="h-full w-full object-cover"
                        draggable="false"
                        alt=""
                    >

                    <button
                        type="button"
                        class="
                            absolute right-1 top-1
                            flex h-6 w-6 items-center justify-center
                            rounded-full border border-slate-200 bg-white
                            opacity-0 transition
                            group-hover:opacity-100
                        "
                        data-remove-upload="${index}"
                        aria-label="Remove photo"
                    >
                        <svg
                            class="h-3 w-3 text-slate-600"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2"
                            viewBox="0 0 24 24"
                            aria-hidden="true"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M6 18L18 6M6 6l12 12"
                            />
                        </svg>
                    </button>
                `;

                const removeButton = wrapper.querySelector(
                    '[data-remove-upload]',
                );

                removeButton?.addEventListener('click', () => {
                    selectedFiles.splice(
                        index,
                        1,
                    );

                    renderPreview();
                    updateCounter();
                });

                preview.appendChild(wrapper);
            };

            reader.readAsDataURL(file);
        });
    }


    function updateCounter() {
        if (!counter) {
            return;
        }

        counter.textContent = (
            `${selectedFiles.length} / ${remainingSlots}`
        );
    }


    async function uploadFiles() {
        if (
            !submitButton
            || !selectedFiles.length
        ) {
            return;
        }

        const uploadUrl = submitButton.dataset.uploadUrl;

        if (!uploadUrl) {
            return;
        }

        const formData = new FormData();

        selectedFiles.forEach((file) => {
            formData.append(
                'photos',
                file,
            );
        });

        const csrf = document.querySelector(
            '[name=csrfmiddlewaretoken]',
        );

        if (csrf) {
            formData.append(
                'csrfmiddlewaretoken',
                csrf.value,
            );
        }

        submitButton.disabled = true;

        const originalText = submitButton.textContent;
        submitButton.textContent = '…';

        try {
            const response = await fetch(
                uploadUrl,
                {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'HX-Request': 'true',
                    },
                },
            );

            if (!response.ok) {
                throw new Error(
                    `Upload failed: ${response.status}`,
                );
            }

            closeModal();
            window.location.reload();

        } catch (error) {
            console.error(
                '[gallery] Upload failed:',
                error,
            );

            submitButton.disabled = false;
            submitButton.textContent = originalText;
        }
    }


    function reset() {
        selectedFiles = [];

        renderPreview();
        updateCounter();

        if (fileInput) {
            fileInput.value = '';
        }
    }
}