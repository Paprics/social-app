// static/js/gallery.js
// Модуль: вкладки, загрузка фото, lightbox

document.addEventListener('DOMContentLoaded', function () {
    initTabs();
    initUploadModal();
    initLightbox();
    initDeletePhoto();
});

// ─── ВКЛАДКИ ────────────────────────────────────────────────

function initTabs() {
    const tabs = document.querySelectorAll('.tab-btn');
    if (!tabs.length) return;

    const contentMap = {};
    tabs.forEach(btn => {
        const id = btn.dataset.tab;
        contentMap[id] = document.getElementById('tab-' + id);
    });

    function activateTab(tabId) {
        Object.values(contentMap).forEach(el => { if (el) el.classList.add('hidden'); });
        if (contentMap[tabId]) contentMap[tabId].classList.remove('hidden');
        tabs.forEach(btn => {
            const active = btn.dataset.tab === tabId;
            btn.classList.toggle('border-blue-600', active);
            btn.classList.toggle('text-slate-700', active);
            btn.classList.toggle('border-transparent', !active);
            btn.classList.toggle('text-slate-500', !active);
        });
    }

    tabs.forEach(btn => {
        btn.addEventListener('click', function () {
            activateTab(this.dataset.tab);
            localStorage.setItem('activePhotoTab', this.dataset.tab);
        });
    });

    const saved = localStorage.getItem('activePhotoTab');
    activateTab(saved && contentMap[saved] ? saved : (tabs[0]?.dataset.tab || 'albums'));
}

// ─── UPLOAD MODAL ────────────────────────────────────────────

function initUploadModal() {
    const modal = document.getElementById('upload-modal');
    if (!modal) return;

    const dropzone = document.getElementById('upload-dropzone');
    const fileInput = document.getElementById('upload-file-input');
    const preview = document.getElementById('upload-preview');
    const submitBtn = document.getElementById('upload-submit-btn');
    const counter = document.getElementById('upload-counter');
    const remaining = parseInt(modal.dataset.remainingSlots || '0', 10);

    let selectedFiles = [];

    // Открытие
    document.querySelectorAll('[js-open-upload-modal]').forEach(btn => {
        btn.addEventListener('click', openModal);
    });

    // Закрытие
    document.querySelectorAll('[js-close-upload-modal]').forEach(btn => {
        btn.addEventListener('click', closeModal);
    });

    modal.addEventListener('click', e => { if (e.target === modal) closeModal(); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

    function openModal() {
        modal.classList.remove('hidden');
        document.body.classList.add('overflow-hidden');
    }

    function closeModal() {
        modal.classList.add('hidden');
        document.body.classList.remove('overflow-hidden');
        reset();
    }

    // Drag & drop
    if (dropzone) {
        dropzone.addEventListener('dragover', e => {
            e.preventDefault();
            dropzone.classList.add('border-blue-500', 'bg-blue-50');
        });
        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('border-blue-500', 'bg-blue-50');
        });
        dropzone.addEventListener('drop', e => {
            e.preventDefault();
            dropzone.classList.remove('border-blue-500', 'bg-blue-50');
            handleFiles(Array.from(e.dataTransfer.files));
        });
        dropzone.addEventListener('click', () => fileInput && fileInput.click());
    }

    if (fileInput) {
        fileInput.addEventListener('change', () => handleFiles(Array.from(fileInput.files)));
    }

    function handleFiles(files) {
        const images = files.filter(f => f.type.startsWith('image/'));
        selectedFiles = [...selectedFiles, ...images].slice(0, remaining);
        renderPreview();
        updateCounter();
    }

    function renderPreview() {
        if (!preview) return;
        preview.innerHTML = '';
        if (!selectedFiles.length) {
            preview.classList.add('hidden');
            if (submitBtn) submitBtn.disabled = true;
            return;
        }
        preview.classList.remove('hidden');
        if (submitBtn) submitBtn.disabled = false;

        selectedFiles.forEach((file, idx) => {
            const reader = new FileReader();
            reader.onload = e => {
                const wrap = document.createElement('div');
                wrap.className = 'relative aspect-square bg-slate-100 rounded-lg overflow-hidden border border-slate-200 group';
                wrap.innerHTML = `
                    <img src="${e.target.result}" class="w-full h-full object-cover" draggable="false">
                    <button type="button"
                            class="absolute top-1 right-1 w-6 h-6 bg-white border border-slate-200 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition"
                            data-remove-idx="${idx}">
                        <svg class="w-3 h-3 text-slate-600" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
                        </svg>
                    </button>`;
                wrap.querySelector('[data-remove-idx]').addEventListener('click', () => {
                    selectedFiles.splice(idx, 1);
                    renderPreview();
                    updateCounter();
                });
                preview.appendChild(wrap);
            };
            reader.readAsDataURL(file);
        });
    }

    function updateCounter() {
        if (counter) counter.textContent = `${selectedFiles.length} / ${remaining}`;
    }

    // Отправка
    if (submitBtn) {
        submitBtn.addEventListener('click', () => {
            if (!selectedFiles.length) return;
            const fd = new FormData();
            selectedFiles.forEach(f => fd.append('photos', f));
            const csrf = document.querySelector('[name=csrfmiddlewaretoken]');
            if (csrf) fd.append('csrfmiddlewaretoken', csrf.value);

            submitBtn.disabled = true;
            const originalText = submitBtn.textContent;
            submitBtn.textContent = '…';

            fetch(submitBtn.dataset.uploadUrl, {
                method: 'POST',
                body: fd,
                headers: { 'HX-Request': 'true' },
            })
                .then(r => r.text())
                .then(() => {
                    // После успешной загрузки — перезагружаем страницу,
                    // чтобы обложка альбома и сетка обновились корректно
                    closeModal();
                    window.location.reload();
                })
                .catch(err => {
                    console.error('[gallery] Ошибка загрузки:', err);
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;
                });
        });
    }

    function reset() {
        selectedFiles = [];
        renderPreview();
        updateCounter();
        if (fileInput) fileInput.value = '';
    }
}

// ─── LIGHTBOX ────────────────────────────────────────────────

function initLightbox() {
    const lb = document.getElementById('lightbox');
    if (!lb) return;

    const lbImg = document.getElementById('lb-img');
    const lbCounter = document.getElementById('lb-counter');
    const lbTitle = document.getElementById('lb-title');
    const lbClose = document.getElementById('lb-close');
    const lbPrev = document.getElementById('lb-prev');
    const lbNext = document.getElementById('lb-next');
    const lbCommentsToggle = document.getElementById('lb-scroll-comments');
    const lbCommentsSection = document.getElementById('lb-comments-section');

    let photos = [];
    let current = 0;

    function collectPhotos() {
        photos = Array.from(document.querySelectorAll('.photo-thumb')).map(btn => ({
            url: btn.dataset.photoUrl,
            title: btn.dataset.photoTitle || '',
            id: btn.dataset.photoId,
        }));
    }

    function open(idx) {
        collectPhotos();
        if (!photos.length) return;
        current = Math.max(0, Math.min(idx, photos.length - 1));
        render();
        lb.classList.remove('hidden');
        document.body.classList.add('overflow-hidden');
    }

    function close() {
        lb.classList.add('hidden');
        document.body.classList.remove('overflow-hidden');
        lbImg.src = '';
    }

    function render() {
        const p = photos[current];
        lbImg.src = p.url;
        lbImg.alt = p.title;
        lbTitle.textContent = p.title;
        lbCounter.textContent = `${current + 1} / ${photos.length}`;
        // Заглушки статистики — обнуляем (в будущем — fetch)
        ['lb-likes', 'lb-views', 'lb-favorites', 'lb-comments-count'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.textContent = '0';
        });
        if (lbCommentsSection) lbCommentsSection.classList.add('hidden');
        // Скрываем стрелки если одно фото
        if (lbPrev) lbPrev.classList.toggle('invisible', photos.length <= 1);
        if (lbNext) lbNext.classList.toggle('invisible', photos.length <= 1);
    }

    function prev() {
        current = (current - 1 + photos.length) % photos.length;
        render();
    }

    function next() {
        current = (current + 1) % photos.length;
        render();
    }

    // Клик по миниатюре
    document.addEventListener('click', e => {
        const thumb = e.target.closest('.photo-thumb');
        if (thumb) {
            e.preventDefault();
            open(parseInt(thumb.dataset.photoIndex, 10));
        }
    });

    if (lbClose) lbClose.addEventListener('click', close);
    if (lbPrev) lbPrev.addEventListener('click', prev);
    if (lbNext) lbNext.addEventListener('click', next);

    // Закрытие по клику на фон
    lb.addEventListener('click', e => { if (e.target === lb) close(); });

    // Комментарии — показать/скрыть секцию
    if (lbCommentsToggle && lbCommentsSection) {
        lbCommentsToggle.addEventListener('click', () => {
            lbCommentsSection.classList.toggle('hidden');
        });
    }

    // Клавиатура
    document.addEventListener('keydown', e => {
        if (lb.classList.contains('hidden')) return;
        if (e.key === 'ArrowLeft') prev();
        if (e.key === 'ArrowRight') next();
        if (e.key === 'Escape') close();
    });
}

// ─── УДАЛЕНИЕ ФОТО ───────────────────────────────────────────

function initDeletePhoto() {
    document.querySelectorAll('[data-js-delete-photo]').forEach(btn => {
        btn.addEventListener('click', function () {
            const url = this.dataset.deleteUrl;
            if (!url) return;
            if (!confirm('Delete this photo?')) return;

            const csrf = document.querySelector('[name=csrfmiddlewaretoken]');
            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrf ? csrf.value : '',
                    'HX-Request': 'true',
                },
            })
                .then(r => {
                    if (r.ok) window.location.reload();
                    else console.error('[gallery] Ошибка удаления фото');
                })
                .catch(err => console.error('[gallery] Ошибка удаления:', err));
        });
    });
}