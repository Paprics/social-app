document.addEventListener("DOMContentLoaded", () => {
    const profileButton = document.getElementById("profile-button");
    const profileMenu = document.getElementById("profile-menu");

    const mobileButton = document.getElementById("mobile-menu-button");
    const mobileMenu = document.getElementById("mobile-menu");

    /**
     * Profile menu
     */

    if (profileButton && profileMenu) {

        profileButton.addEventListener("click", (event) => {
            event.stopPropagation();
            profileMenu.classList.toggle("hidden");
        });

        profileMenu.addEventListener("click", (event) => {
            event.stopPropagation();
        });

    }

    /**
     * Mobile menu
     */

    if (mobileButton && mobileMenu) {

        mobileButton.addEventListener("click", (event) => {
            event.stopPropagation();
            mobileMenu.classList.toggle("hidden");
        });

        mobileMenu.addEventListener("click", (event) => {
            event.stopPropagation();
        });

    }

    /**
     * Close menus by clicking outside
     */

    document.addEventListener("click", () => {

        if (profileMenu) {
            profileMenu.classList.add("hidden");
        }

        if (mobileMenu) {
            mobileMenu.classList.add("hidden");
        }

    });

    /**
     * Close menus with Escape
     */

    document.addEventListener("keydown", (event) => {

        if (event.key === "Escape") {

            if (profileMenu) {
                profileMenu.classList.add("hidden");
            }

            if (mobileMenu) {
                mobileMenu.classList.add("hidden");
            }

        }

    });

});