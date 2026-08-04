document.addEventListener("DOMContentLoaded", () => {
    const tabs = document.querySelectorAll(".explore-tab");
    if (tabs.length === 0) return;

    // Функция переключения классов активной вкладки
    function activateTabUI(activeTab) {
        tabs.forEach(tab => {
            tab.classList.remove("border-blue-600", "text-blue-600");
            tab.classList.add("border-transparent", "text-slate-600");
        });
        activeTab.classList.remove("border-transparent", "text-slate-600");
        activeTab.classList.add("border-blue-600", "text-blue-600");
    }

    // Клик по вкладке меняет подсветку
    tabs.forEach(tab => {
        tab.addEventListener("click", () => {
            activateTabUI(tab);
        });
    });

    // Обработка открытия страницы по хэшу (например: /explore/#photos)
    const currentHash = window.location.hash;
    let targetTab = null;

    if (currentHash) {
        targetTab = document.querySelector(`.explore-tab[href="${currentHash}"]`);
    }

    // Если хэша нет или вкладка не найдена — берем первую (#albums)
    if (!targetTab) {
        targetTab = tabs[0];
    }

    // Программный клик запускает HTMX-запрос на подгрузку контента
    if (targetTab) {
        targetTab.click();
    }
});