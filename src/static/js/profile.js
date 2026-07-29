// static/js/profile.js
// Модуль: модальное окно смены аватара профиля

(function () {
    'use strict';

    // ── MutationObserver следит за контейнером модала ────────────
    // Срабатывает когда HTMX вставляет HTML — надёжнее чем htmx:afterSwap
    function watchModalContainer() {
        const container = document.getElementById('avatar-modal-container');
        if (!container) return;

        const observer = new MutationObserver(function (mutations) {
            for (const mutation of mutations) {
                if (mutation.addedNodes.length) {
                    const modal = document.getElementById('avatar-modal');
                    if (modal) {
                        document.body.classList.add('overflow-hidden');
                        initFileInput();
                        console.log('[profile] Модал аватара открыт');
                    }
                }
            }
        });

        observer.observe(container, { childList: true });
    }

    // ── Делегированные обработчики кликов ────────────────────────
    function initClickDelegation() {
        document.addEventListener('click', function (e) {

            // Закрытие по кнопке [js-close-avatar-modal]
            if (e.target.closest('[js-close-avatar-modal]')) {
                e.preventDefault();
                closeAvatarModal();
                return;
            }

            // Закрытие по клику на оверлей (сам #avatar-modal, не его дети)
            if (e.target.id === 'avatar-modal') {
                closeAvatarModal();
                return;
            }

            // Выбор фото из сетки
            const photoBtn = e.target.closest('.avatar-photo-btn');
            if (photoBtn) {
                selectPhoto(photoBtn);
                return;
            }

            // Кнопка «Set as profile photo»
            if (e.target.id === 'avatar-set-btn') {
                submitAvatar();
                return;
            }

            // Очистка превью нового файла
            if (e.target.closest('#avatar-upload-clear')) {
                clearUploadPreview();
                return;
            }
        });

        // Закрытие по Escape
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && document.getElementById('avatar-modal')) {
                closeAvatarModal();
            }
        });
    }

    // ── Инициализация file input (после вставки модала в DOM) ────
    function initFileInput() {
        const input = document.getElementById('avatar-file-input');
        if (!input) return;

        // Снимаем старый listener если модал переоткрывался
        const fresh = input.cloneNode(true);
        input.parentNode.replaceChild(fresh, input);

        fresh.addEventListener('change', function () {
            const file = this.files[0];
            if (!file) return;

            // Снимаем выделение с сетки
            document.querySelectorAll('.avatar-photo-btn').forEach(function (b) {
                b.classList.remove('border-blue-500');
                b.classList.add('border-transparent');
                const check = b.querySelector('.avatar-check');
                if (check) check.classList.add('hidden');
            });

            // Показываем превью
            const preview = document.getElementById('avatar-upload-preview');
            const previewImg = document.getElementById('avatar-upload-preview-img');
            const previewName = document.getElementById('avatar-upload-preview-name');

            if (preview && previewImg && previewName) {
                const reader = new FileReader();
                reader.onload = function (evt) {
                    previewImg.src = evt.target.result;
                    previewName.textContent = file.name;
                    preview.classList.remove('hidden');
                };
                reader.readAsDataURL(file);
            }

            // Активируем кнопку
            setButtonMode('upload');
            console.log('[profile] Выбран новый файл для загрузки:', file.name);
        });
    }

    // ── Выбор существующего фото ──────────────────────────────────
    function selectPhoto(btn) {
        // Снимаем выделение со всех
        document.querySelectorAll('.avatar-photo-btn').forEach(function (b) {
            b.classList.remove('border-blue-500');
            b.classList.add('border-transparent');
            const check = b.querySelector('.avatar-check');
            if (check) check.classList.add('hidden');
        });

        // Выделяем нажатый
        btn.classList.remove('border-transparent');
        btn.classList.add('border-blue-500');
        const check = btn.querySelector('.avatar-check');
        if (check) check.classList.remove('hidden');

        // Сбрасываем файл
        clearUploadPreview(false);

        setButtonMode('existing', btn.dataset.photoId);
        console.log('[profile] Выбрано фото id=' + btn.dataset.photoId);
    }

    // ── Режим кнопки ─────────────────────────────────────────────
    function setButtonMode(mode, photoId) {
        const btn = document.getElementById('avatar-set-btn');
        if (!btn) return;
        btn.disabled = false;
        btn.dataset.mode = mode;
        if (photoId) {
            btn.dataset.photoId = photoId;
        } else {
            delete btn.dataset.photoId;
        }
    }

    // ── Очистка превью файла ─────────────────────────────────────
    function clearUploadPreview(resetBtn) {
        if (resetBtn === undefined) resetBtn = true;

        const preview = document.getElementById('avatar-upload-preview');
        const input = document.getElementById('avatar-file-input');
        if (preview) preview.classList.add('hidden');
        if (input) input.value = '';

        if (resetBtn) {
            const anySelected = document.querySelector('.avatar-photo-btn.border-blue-500');
            if (!anySelected) {
                const btn = document.getElementById('avatar-set-btn');
                if (btn) {
                    btn.disabled = true;
                    delete btn.dataset.mode;
                    delete btn.dataset.photoId;
                }
            }
        }
    }

    // ── Submit ────────────────────────────────────────────────────
    function submitAvatar() {
        const setBtn = document.getElementById('avatar-set-btn');
        if (!setBtn || setBtn.disabled) return;

        const mode = setBtn.dataset.mode;
        const csrf = document.querySelector('[name=csrfmiddlewaretoken]');
        const csrfValue = csrf ? csrf.value : '';

        if (!mode) {
            console.warn('[profile] Режим не определён');
            return;
        }

        setBtn.disabled = true;
        const originalText = setBtn.textContent.trim();
        setBtn.textContent = '…';

        if (mode === 'existing') {
            const fd = new FormData();
            fd.append('photo_id', setBtn.dataset.photoId);
            fd.append('csrfmiddlewaretoken', csrfValue);

            fetch(setBtn.dataset.setUrl, {
                method: 'POST',
                body: fd,
                headers: { 'HX-Request': 'true' },
            })
                .then(function (r) {
                    if (!r.ok) throw new Error('HTTP ' + r.status);
                    return r.text();
                })
                .then(function (html) {
                    updateAvatarBlock(html);
                    closeAvatarModal();
                    console.log('[profile] Аватар установлен');
                })
                .catch(function (err) {
                    console.error('[profile] Ошибка установки аватара:', err);
                    setBtn.disabled = false;
                    setBtn.textContent = originalText;
                });

        } else if (mode === 'upload') {
            const input = document.getElementById('avatar-file-input');
            if (!input || !input.files[0]) {
                console.warn('[profile] Файл не найден');
                setBtn.disabled = false;
                setBtn.textContent = originalText;
                return;
            }

            const fd = new FormData();
            fd.append('photo', input.files[0]);
            fd.append('csrfmiddlewaretoken', csrfValue);

            fetch(setBtn.dataset.uploadUrl, {
                method: 'POST',
                body: fd,
                headers: { 'HX-Request': 'true' },
            })
                .then(function (r) {
                    if (!r.ok) throw new Error('HTTP ' + r.status);
                    return r.text();
                })
                .then(function (html) {
                    updateAvatarBlock(html);
                    closeAvatarModal();
                    console.log('[profile] Новое фото загружено и установлено аватаром');
                })
                .catch(function (err) {
                    console.error('[profile] Ошибка загрузки:', err);
                    setBtn.disabled = false;
                    setBtn.textContent = originalText;
                });
        }
    }

    // ── Обновление блока аватара ──────────────────────────────────
    function updateAvatarBlock(html) {
        const block = document.getElementById('avatar-block');
        if (block) {
            block.innerHTML = html;
            console.log('[profile] Блок аватара обновлён');
        }
    }

    // ── Закрытие модала ───────────────────────────────────────────
    function closeAvatarModal() {
        const container = document.getElementById('avatar-modal-container');
        if (container) container.innerHTML = '';
        document.body.classList.remove('overflow-hidden');
        console.log('[profile] Модал закрыт');
    }

    // ── Точка входа ───────────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', function () {
        watchModalContainer();
        initClickDelegation();
        console.log('[profile] profile.js загружен');
    });

})();