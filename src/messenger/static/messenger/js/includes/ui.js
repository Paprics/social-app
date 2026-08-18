import {
    getCookie,
    getLangPrefix,
    messengerDebug,
} from "./utils.js";
import {
    initMessageHistoryLazyLoad,
    scrollMessagesToBottom,
} from "./history.js";

function focusMessageTextarea() {
    document.querySelector("textarea[name='text']")?.focus();
}

async function sendPostRequest(url) {
    return fetch(url, {
        method: "POST",
        headers: {
            "X-CSRFToken": getCookie("csrftoken"),
        },
    });
}

document.addEventListener("DOMContentLoaded", () => {
    focusMessageTextarea();
    initMessageHistoryLazyLoad();
    scrollMessagesToBottom();
});

document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-delete-message]");

    if (!button) {
        return;
    }

    event.preventDefault();

    if (!confirm("Удалить сообщение?")) {
        return;
    }

    button.disabled = true;

    try {
        const response = await sendPostRequest(button.dataset.deleteMessage);

        if (!response.ok) {
            messengerDebug("Message delete failed", response.status);
            button.disabled = false;
        }
    } catch (error) {
        messengerDebug("Message delete error", error);
        button.disabled = false;
    }
});

document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-delete-dialog]");

    if (!button) {
        return;
    }

    event.preventDefault();
    event.stopPropagation();

    if (!confirm("Удалить диалог полностью?")) {
        return;
    }

    button.disabled = true;

    const dialogItem = button.closest("[id^='dialog-']");
    const publicId = dialogItem?.id.replace("dialog-", "") ?? null;

    try {
        const response = await sendPostRequest(button.dataset.deleteDialog);

        if (!response.ok) {
            messengerDebug("Dialog delete failed", response.status);
            button.disabled = false;
            return;
        }

        const openedDialogPublicId =
            document.getElementById("dialog-page")?.dataset.dialogId;

        if (publicId && openedDialogPublicId === publicId) {
            window.location.href = `${getLangPrefix()}/messenger/`;
            return;
        }

        dialogItem?.remove();
    } catch (error) {
        messengerDebug("Dialog delete error", error);
        button.disabled = false;
    }
});

document.addEventListener("keydown", (event) => {
    const textarea = document.activeElement;

    if (
        textarea?.name !== "text"
        || event.key !== "Enter"
        || event.shiftKey
    ) {
        return;
    }

    event.preventDefault();

    if (textarea.value.trim()) {
        textarea.form?.requestSubmit();
    }
});
