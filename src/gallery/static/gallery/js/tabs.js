// src/gallery/static/gallery/js/tabs.js

document.addEventListener('DOMContentLoaded', () => {
    initGalleryTabs();
})


// ─── GALLERY TABS ───────────────────────────────────────────────

function initGalleryTabs() {
    const tabs = document.querySelectorAll('[data-gallery-tab]');

    if (!tabs.length) {
        return;
    }

    function activateTab(activeTab) {
        tabs.forEach((tab) => {
            const isActive = tab === activeTab;

            tab.classList.toggle('border-blue-600', isActive);
            tab.classList.toggle('text-blue-600', isActive);

            tab.classList.toggle('border-transparent', !isActive);
            tab.classList.toggle('text-slate-500', !isActive);
        });
    }

    tabs.forEach((tab) => {
        tab.addEventListener('click', () => {
            activateTab(tab);
        });
    });
}

