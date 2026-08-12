

/*
 * Gallery page interactions.
 *
 * Handles album modal state, asynchronous album creation,
 * and field-level Django form errors.
 */

// ─── Elements ────────────────────────────────────────────────────
const albumModal = document.querySelector("[data-album-modal]");
const albumModalOpenButton = document.querySelector(
    "[data-album-modal-open]"
);
const albumModalCloseButtons = document.querySelectorAll(
    "[data-album-modal-close]"
);
const albumCreateForm = document.querySelector(
    "[data-album-create-form]"
);
const albumTitleInput = document.querySelector("#album-title");

// ─── Modal state ─────────────────────────────────────────────────
// """Show the album modal and move focus to its title field."""
function openAlbumModal() {

    if (!albumModal) {
        return;
    }

    albumModal.classList.remove("hidden");
    albumModal.setAttribute("aria-hidden", "false");
    document.body.classList.add("overflow-hidden");

    requestAnimationFrame(() => {
        albumTitleInput?.focus();
    });
}

// """Hide the album modal and restore focus to the open button."""
function closeAlbumModal() {

    if (!albumModal) {
        return;
    }

    albumModal.classList.add("hidden");
    albumModal.setAttribute("aria-hidden", "true");
    document.body.classList.remove("overflow-hidden");
    albumModalOpenButton?.focus();
}

albumModalOpenButton?.addEventListener("click", openAlbumModal);

albumModalCloseButtons.forEach((button) => {
    button.addEventListener("click", closeAlbumModal);
});

document.addEventListener("keydown", (event) => {
    if (
        event.key === "Escape" &&
        albumModal &&
        !albumModal.classList.contains("hidden")
    ) {
        closeAlbumModal();
    }
});

// ─── Form errors ─────────────────────────────────────────────────
function clearFormErrors(form) {
    // Remove previously rendered error messages.
    form.querySelectorAll("[data-field-error]").forEach((element) => {
        element.textContent = "";
        element.classList.add("hidden");
    });

    const generalErrors = form.querySelector(
        "[data-form-general-errors]"
    );

    if (generalErrors) {
        generalErrors.textContent = "";
        generalErrors.classList.add("hidden");
    }

    Array.from(form.elements).forEach((element) => {
        element.removeAttribute("aria-invalid");
    });
}

function renderFormErrors(form, errors) {
    // Map Django error keys to their matching form fields.
    Object.entries(errors).forEach(([fieldName, fieldErrors]) => {
        const message = fieldErrors
            .map((error) => error.message)
            .join(" ");

        if (fieldName === "__all__") {
            const generalErrors = form.querySelector(
                "[data-form-general-errors]"
            );

            if (generalErrors) {
                generalErrors.textContent = message;
                generalErrors.classList.remove("hidden");
            }

            return;
        }

        const field = form.elements.namedItem(fieldName);
        const errorElement = form.querySelector(
            `[data-field-error="${fieldName}"]`
        );

        field?.setAttribute("aria-invalid", "true");

        if (errorElement) {
            errorElement.textContent = message;
            errorElement.classList.remove("hidden");
        }
    });
}

// ─── Album creation ──────────────────────────────────────────────
albumCreateForm?.addEventListener("submit", async (event) => {
    event.preventDefault();

    const form = event.currentTarget;
    const submitButton = form.querySelector("[data-album-submit]");

    const csrfInput = form.elements.namedItem("csrfmiddlewaretoken");
    const titleInput = form.elements.namedItem("title");
    const visibilityInput = form.elements.namedItem("visibility");

    clearFormErrors(form);

    if (!csrfInput || !titleInput || !visibilityInput) {
        console.error("Album form is incomplete:", {
            csrfInput,
            titleInput,
            visibilityInput,
            form,
        });

        renderFormErrors(form, {
            __all__: [
                {
                    message: "The album form is incomplete. Reload the page.",
                },
            ],
        });

        return;
    }

    const body = new URLSearchParams({
        csrfmiddlewaretoken: csrfInput.value,
        title: titleInput.value,
        visibility: visibilityInput.value,
    });

    console.debug("[album-create] request:", {
        action: form.action,
        title: titleInput.value,
        visibility: visibilityInput.value,
        hasCsrfToken: Boolean(csrfInput.value),
    });

    submitButton?.setAttribute("disabled", "");

    try {
        const response = await fetch(form.action, {
            method: "POST",
            body,
            credentials: "same-origin",
            headers: {
                Accept: "application/json",
                "Content-Type":
                    "application/x-www-form-urlencoded;charset=UTF-8",
                "X-CSRFToken": csrfInput.value,
                "X-Requested-With": "XMLHttpRequest",
            },
        });

        const contentType = response.headers.get("content-type") ?? "";

        if (!contentType.includes("application/json")) {
            const responseText = await response.text();

            console.error(
                `[album-create] Unexpected response (${response.status}):`,
                responseText
            );

            renderFormErrors(form, {
                __all__: [
                    {
                        message: `Server rejected the request (${response.status}).`,
                    },
                ],
            });

            return;
        }

        const data = await response.json();

        if (!response.ok) {
            renderFormErrors(form, data.errors ?? {
                __all__: [
                    {
                        message:
                            data.message ??
                            `Request failed (${response.status}).`,
                    },
                ],
            });

            return;
        }

        if (data.redirect_url) {
            window.location.assign(data.redirect_url);
        }
    } catch (error) {
        console.error("[album-create] Request failed:", error);

        renderFormErrors(form, {
            __all__: [
                {
                    message: "Unable to create the album. Try again.",
                },
            ],
        });
    } finally {
        submitButton?.removeAttribute("disabled");
    }
});