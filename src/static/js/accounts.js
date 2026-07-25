// accounts.js — логика модалок и дропдаунов авторизации
// Импортируется в main.js: import './accounts.js'

(function () {
    "use strict";

    // ─── Модалки ───────────────────────────────────────────────────────────────

    function openModal(id) {
        const modal = document.getElementById(id);
        if (!modal) return;
        modal.classList.remove("hidden");
        modal.classList.add("flex");
        document.body.style.overflow = "hidden";
        console.log("[accounts] modal open:", id);
    }

    function closeModal(id) {
        const modal = document.getElementById(id);
        if (!modal) return;
        modal.classList.add("hidden");
        modal.classList.remove("flex");
        document.body.style.overflow = "";
        console.log("[accounts] modal close:", id);
    }

    function initModals() {
        // Открытие по data-modal-open="<id>"
        document.addEventListener("click", function (e) {
            const opener = e.target.closest("[data-modal-open]");
            if (opener) {
                e.preventDefault();
                openModal(opener.dataset.modalOpen);
            }
        });

        // Закрытие по data-modal-close="<id>"
        document.addEventListener("click", function (e) {
            const closer = e.target.closest("[data-modal-close]");
            if (closer) {
                e.preventDefault();
                closeModal(closer.dataset.modalClose);
                // Поддержка одновременного закрытия + открытия другой
                if (closer.dataset.modalOpen) {
                    openModal(closer.dataset.modalOpen);
                }
            }
        });

        // Закрытие по клику на backdrop
        document.addEventListener("click", function (e) {
            if (e.target.hasAttribute("data-modal-backdrop")) {
                const modal = e.target.closest("[data-modal]");
                if (modal) closeModal(modal.id);
            }
        });

        // Закрытие по Escape
        document.addEventListener("keydown", function (e) {
            if (e.key !== "Escape") return;
            document.querySelectorAll("[data-modal].flex").forEach(function (modal) {
                closeModal(modal.id);
            });
        });
    }

    // ─── Дропдауны ─────────────────────────────────────────────────────────────

    function initDropdowns() {
        // Открытие/закрытие по data-dropdown-button="<id>"
        document.addEventListener("click", function (e) {
            const btn = e.target.closest("[data-dropdown-button]");
            if (btn) {
                e.stopPropagation();
                const targetId = btn.dataset.dropdownButton;
                const menu = document.getElementById(targetId);
                if (!menu) return;

                // Закрываем все остальные
                document.querySelectorAll("[data-dropdown]:not(.hidden)").forEach(function (m) {
                    if (m.id !== targetId) m.classList.add("hidden");
                });

                menu.classList.toggle("hidden");
                console.log("[accounts] dropdown toggle:", targetId);
                return;
            }

            // Клик вне дропдауна — закрываем все
            document.querySelectorAll("[data-dropdown]:not(.hidden)").forEach(function (m) {
                m.classList.add("hidden");
            });
        });
    }

    // ─── Мобильное меню ────────────────────────────────────────────────────────

    function initMobileMenu() {
        const btn = document.getElementById("mobile-menu-button");
        const menu = document.getElementById("mobile-menu");
        if (!btn || !menu) return;

        btn.addEventListener("click", function () {
            menu.classList.toggle("hidden");
            console.log("[accounts] mobile menu toggle");
        });
    }

    // ─── Init ──────────────────────────────────────────────────────────────────

    document.addEventListener("DOMContentLoaded", function () {
        initModals();
        initDropdowns();
        initMobileMenu();
        console.log("[accounts] auth UI initialized");
    });
})();