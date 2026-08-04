document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-media-reveal]");

    if (!button) {
        return;
    }

    const container = button.closest(".media-container");

    if (!container) {
        return;
    }

    const image = container.querySelector(".media-image");
    const overlay = container.querySelector(".media-overlay");

    image?.classList.remove("is-blurred");
    overlay?.setAttribute("hidden", "");
});