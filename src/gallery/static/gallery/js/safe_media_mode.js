// src/static/js/components/safe_media_mode.js

(() => {
    const TOGGLE_SELECTOR = "[data-safe-media-toggle]";
    const FORM_SELECTOR = "[data-safe-media-form]";

    let requestInProgress = false;

    function getToggles() {
        return Array.from(
            document.querySelectorAll(TOGGLE_SELECTOR),
        );
    }

    function setDisabled(disabled) {
        getToggles().forEach((toggle) => {
            toggle.disabled = disabled;
        });
    }

    function syncToggles(checked) {
        getToggles().forEach((toggle) => {
            toggle.checked = checked;
        });
    }

    document.addEventListener("change", async (event) => {
        const toggle = event.target.closest?.(TOGGLE_SELECTOR);

        if (!toggle) {
            return;
        }

        const form = toggle.closest(FORM_SELECTOR);

        if (!form || requestInProgress) {
            return;
        }

        const toggles = getToggles();

        const previousStates = new Map(
            toggles.map((item) => [
                item,
                item.checked,
            ]),
        );

        const checked = toggle.checked;

        /*
         * FormData нужно сформировать ДО disabled,
         * потому что disabled-поля в FormData не попадают.
         */
        const formData = new FormData(form);

        requestInProgress = true;

        /*
         * Визуально сразу синхронизируем все экземпляры
         * Safe Media Mode на странице.
         */
        syncToggles(checked);
        setDisabled(true);

        try {
            const response = await fetch(form.action, {
                method: "POST",
                body: formData,
                credentials: "same-origin",
                headers: {
                    "HX-Request": "true",
                    "X-Requested-With": "XMLHttpRequest",
                },
            });

            if (!response.ok) {
                throw new Error(
                    `Safe Media Mode request failed: ${response.status}`,
                );
            }

            /*
             * blur_media влияет на уже отрисованные изображения,
             * поэтому после успешного сохранения обновляем страницу.
             */
            window.location.reload();
        } catch (error) {
            console.error(error);

            /*
             * Сервер не сохранил значение —
             * возвращаем UI в исходное состояние.
             */
            previousStates.forEach((state, item) => {
                item.checked = state;
            });

            setDisabled(false);
            requestInProgress = false;
        }
    });
})();