/**
 * Image Blur / Reveal
 *
 * Handles client-side revealing and hiding of blurred images.
 *
 * Images are blurred by the `.is-blurred` CSS class.
 * Clicking an element with `[data-media-reveal]` toggles the blur
 * on `.media-image` inside the nearest `.media-container`.
 *
 * Uses event delegation on `document`, so it also works with
 * dynamically inserted content (e.g. HTMX).
 *
 * Related:
 * - CSS: core/static/css/components/image_blur.css
 * - Django tag: core/templatetags/render_image.py
 */
document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-media-reveal]");

    if (!button) {
        return;
    }

    // The component may be rendered inside a clickable card or link.
    // Toggling the image must not activate that parent element.
    event.preventDefault();
    event.stopPropagation();

    const container = button.closest(".media-container");

    if (!container) {
        return;
    }

    const image = container.querySelector(".media-image");

    if (!image) {
        return;
    }

    const isRevealed = container.classList.toggle("is-revealed");

    image.classList.toggle("is-blurred", !isRevealed);

    button.setAttribute("aria-pressed", String(isRevealed));
    button.setAttribute(
        "aria-label",
        isRevealed ? "Hide image" : "Show image",
    );
    button.title = isRevealed ? "Hide" : "Show";

    if (!button.dataset.revealContent) {
        button.dataset.revealContent = button.innerHTML;
    }

    button.innerHTML = isRevealed
        ? `
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M3 3l18 18
                         M10.6 10.6a2 2 0 0 0 2.8 2.8
                         M9.9 4.2A10.7 10.7 0 0 1 12 4
                         c5.5 0 9 8 9 8
                         a16.8 16.8 0 0 1-2.1 3.2
                         M6.6 6.6C4.2 8.2 3 12 3 12
                         s3.5 8 9 8
                         a9.8 9.8 0 0 0 4.1-.9"/>
            </svg>
            <span>Hide</span>
        `
        : button.dataset.revealContent;
});