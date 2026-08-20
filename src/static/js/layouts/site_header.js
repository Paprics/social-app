(() => {
    "use strict";

    const dropdownButtonSelector = "[data-dropdown-button]";
    const dropdownSelector = "[data-dropdown]";
    const languageSelector = "[data-language-switch]";

    function closeDropdown(dropdown) {
        if (!dropdown) {
            return;
        }

        dropdown.classList.add("hidden");

        const button = document.querySelector(
            `${dropdownButtonSelector}[data-dropdown-button="${dropdown.id}"]`
        );

        button?.setAttribute("aria-expanded", "false");
    }

    function closeAllDropdowns(except = null) {
        document.querySelectorAll(dropdownSelector).forEach((dropdown) => {
            if (dropdown !== except) {
                closeDropdown(dropdown);
            }
        });
    }

    function toggleDropdown(button) {
        const dropdownId = button.dataset.dropdownButton;
        const dropdown = document.getElementById(dropdownId);

        if (!dropdown) {
            return;
        }

        const isOpen = !dropdown.classList.contains("hidden");

        closeAllDropdowns(dropdown);

        dropdown.classList.toggle("hidden", isOpen);
        button.setAttribute("aria-expanded", String(!isOpen));
    }

    function setMobileMenu(open) {
        const button = document.getElementById("mobile-menu-button");
        const menu = document.getElementById("mobile-menu");

        if (!button || !menu) {
            return;
        }

        menu.classList.toggle("hidden", !open);
        button.setAttribute("aria-expanded", String(open));
    }

    function switchLanguage(language) {
        const supportedLanguages = new Set(["en", "ru", "uk"]);

        if (!supportedLanguages.has(language)) {
            return;
        }

        const url = new URL(window.location.href);
        const parts = url.pathname.split("/").filter(Boolean);
        const hadTrailingSlash = url.pathname.endsWith("/");

        if (parts.length && supportedLanguages.has(parts[0])) {
            parts[0] = language;
        } else {
            parts.unshift(language);
        }

        url.pathname =
            "/" +
            parts.join("/") +
            (hadTrailingSlash ? "/" : "");

        document.cookie =
            `django_language=${encodeURIComponent(language)}; Path=/; SameSite=Lax`;

        window.location.assign(url.toString());
    }

    document.addEventListener("DOMContentLoaded", () => {
        document.querySelectorAll(dropdownButtonSelector).forEach((button) => {
            button.setAttribute("aria-expanded", "false");
            button.setAttribute("aria-haspopup", "true");
        });

        const mobileMenuButton = document.getElementById("mobile-menu-button");

        if (mobileMenuButton) {
            mobileMenuButton.setAttribute("aria-controls", "mobile-menu");
            mobileMenuButton.setAttribute("aria-expanded", "false");
        }
    });

    document.addEventListener("click", (event) => {
        const languageButton = event.target.closest(languageSelector);

        if (languageButton) {
            event.preventDefault();

            switchLanguage(
                languageButton.dataset.languageSwitch
            );

            return;
        }

        const mobileMenuButton = event.target.closest(
            "#mobile-menu-button"
        );

        if (mobileMenuButton) {
            event.preventDefault();
            event.stopPropagation();

            const mobileMenu = document.getElementById(
                "mobile-menu"
            );

            if (mobileMenu) {
                closeAllDropdowns();

                setMobileMenu(
                    mobileMenu.classList.contains("hidden")
                );
            }

            return;
        }

        const dropdownButton = event.target.closest(
            dropdownButtonSelector
        );

        if (dropdownButton) {
            event.preventDefault();
            event.stopPropagation();

            setMobileMenu(false);
            toggleDropdown(dropdownButton);

            return;
        }

        if (event.target.closest(dropdownSelector)) {
            return;
        }

        closeAllDropdowns();

        if (!event.target.closest("#mobile-menu")) {
            setMobileMenu(false);
        }
    });

    document.addEventListener("change", (event) => {
        const toggle = event.target.closest(
            "[data-safe-media-toggle]"
        );

        if (!toggle) {
            return;
        }

        const form = toggle.closest(
            "[data-safe-media-form]"
        );

        if (form) {
            form.requestSubmit();
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") {
            return;
        }

        closeAllDropdowns();
        setMobileMenu(false);
    });

    window.addEventListener("resize", () => {
        if (window.innerWidth >= 1024) {
            setMobileMenu(false);
        }
    });
})();