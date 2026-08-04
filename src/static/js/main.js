import "./components/media.js";

// main.js — точка входа для глобальных скриптов
// Импортируем модуль авторизации (модалки, дропдауны, мобильное меню)
import "./accounts.js";

console.log("[main] scripts loaded");

// ==================== DROPDOWNS ====================
document.querySelectorAll("[data-dropdown-button]").forEach((button) => {
    button.addEventListener("click", (e) => {
        e.stopPropagation();

        const menu = document.getElementById(button.dataset.dropdownButton);

        if (!menu) return;

        document.querySelectorAll("[data-dropdown]").forEach((dropdown) => {
            if (dropdown !== menu) {
                dropdown.classList.add("hidden");
            }
        });

        menu.classList.toggle("hidden");
    });
});

document.addEventListener("click", (e) => {
    if (e.target.closest("[data-keep-dropdown]")) return;
    document.querySelectorAll("[data-dropdown]").forEach((dropdown) => {
        dropdown.classList.add("hidden");
    });
});

// ==================== MOBILE MENU ====================
const mobileMenuButton = document.getElementById("mobile-menu-button");
const mobileMenu = document.getElementById("mobile-menu");

if (mobileMenuButton && mobileMenu) {
    mobileMenuButton.addEventListener("click", () => {
        mobileMenu.classList.toggle("hidden");
    });
}

// Модальные окна: data-modal-open="id", data-modal-close="id", data-modal-backdrop
document.addEventListener("DOMContentLoaded", function () {
    // Открытие
    document.querySelectorAll("[data-modal-open]").forEach(function (btn) {
        btn.addEventListener("click", function () {
            const id = btn.getAttribute("data-modal-open");
            const modal = document.getElementById(id);
            if (!modal) return;
            modal.classList.remove("hidden");
            modal.classList.add("flex");
        });
    });

    // Закрытие кнопкой
    document.querySelectorAll("[data-modal-close]").forEach(function (btn) {
        btn.addEventListener("click", function () {
            const id = btn.getAttribute("data-modal-close");
            const modal = document.getElementById(id);
            if (!modal) return;
            modal.classList.add("hidden");
            modal.classList.remove("flex");
        });
    });

    // Закрытие по backdrop
    document.querySelectorAll("[data-modal-backdrop]").forEach(function (backdrop) {
        backdrop.addEventListener("click", function () {
            const modal = backdrop.closest("[data-modal]");
            if (!modal) return;
            modal.classList.add("hidden");
            modal.classList.remove("flex");
        });
    });
});
