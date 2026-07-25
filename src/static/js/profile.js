/**
 * profile.js
 * JavaScript-модуль для страницы профиля пользователя.
 * Подключается только на странице профиля через {% block extra_js %}.
 */

// ─── Wall filter buttons ─────────────────────────────────────────────────────

const filterButtons = document.querySelectorAll('.wall-filter-btn');

filterButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        // Сброс активного состояния у всех кнопок
        filterButtons.forEach(b => {
            b.classList.remove('bg-blue-600', 'text-white');
            b.classList.add('border', 'border-slate-200', 'bg-white', 'text-slate-600');
        });

        // Активная кнопка
        btn.classList.add('bg-blue-600', 'text-white');
        btn.classList.remove('border', 'border-slate-200', 'bg-white', 'text-slate-600');

        // TODO: Здесь будет логика фильтрации записей стены
        // (HTMX-запрос или JS-фильтрация по data-аттрибутам)
        const filter = btn.id.replace('wall-filter-', '');
        console.debug('[Profile] Wall filter:', filter);
    });
});

// ─── Load more button ────────────────────────────────────────────────────────

const loadMoreBtn = document.getElementById('wall-load-more');

if (loadMoreBtn) {
    loadMoreBtn.addEventListener('click', () => {
        // TODO: Подгрузка следующей страницы записей (HTMX или fetch)
        console.debug('[Profile] Load more wall posts');
    });
}

// ─── Auto-resize wall post textarea ─────────────────────────────────────────

const wallTextarea = document.getElementById('wall-post-input');

if (wallTextarea) {
    wallTextarea.addEventListener('input', () => {
        wallTextarea.style.height = 'auto';
        wallTextarea.style.height = wallTextarea.scrollHeight + 'px';
    });
}