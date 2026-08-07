/*
 * Messenger frontend.
 *
 * Part 3:
 * - UI initialization;
 * - HTMX events;
 * - message deletion;
 * - dialog deletion;
 * - Enter submit.
 */

import {
    getCookie,
    getLangPrefix,
    messengerDebug,
    reloadSidebar,
    scrollMessagesToBottom,
} from "./messenger_part_1.js";


// =====================================================
// UI initialization
// =====================================================

document.addEventListener(
    "DOMContentLoaded",
    async () => {

        focusMessageTextarea();

        scrollMessagesToBottom();

        const dialogPage = document.getElementById(
            "dialog-page",
        );

        if (dialogPage) {
            await reloadSidebar();
        }

    },
);


function focusMessageTextarea() {

    const textarea = document.querySelector(
        "textarea[name='text']",
    );

    if (textarea) {
        textarea.focus();
    }

}


// =====================================================
// HTMX
// =====================================================

document.body.addEventListener(
    "htmx:afterSwap",
    async (event) => {

        if (event.target.id !== "message-list") {
            return;
        }

        scrollMessagesToBottom();

        const textarea = document.querySelector(
            "textarea[name='text']",
        );

        if (textarea) {

            textarea.value = "";
            textarea.focus();

        }

        await reloadSidebar();

    },
);


// =====================================================
// Delete message
// =====================================================

document.addEventListener(
    "click",
    async (event) => {

        const button = event.target.closest(
            "[data-delete-message]",
        );

        if (!button) {
            return;
        }

        event.preventDefault();

        if (!confirm("Удалить сообщение?")) {
            return;
        }

        button.disabled = true;

        try {

            const response = await sendPostRequest(
                button.dataset.deleteMessage,
            );

            if (!response.ok) {

                messengerDebug(
                    "Message delete failed",
                    response.status,
                );

                button.disabled = false;
            }

        } catch (error) {

            messengerDebug(
                "Message delete error",
                error,
            );

            button.disabled = false;

        }

    },
);


// =====================================================
// Delete dialog
// =====================================================

document.addEventListener(
    "click",
    async (event) => {

        const button = event.target.closest(
            "[data-delete-dialog]",
        );

        if (!button) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();

        if (!confirm("Удалить диалог полностью?")) {
            return;
        }

        button.disabled = true;

        const dialogItem = button.closest(
            "[id^='dialog-']",
        );

        const publicId = dialogItem
            ? dialogItem.id.replace("dialog-", "")
            : null;

        try {

            const response = await sendPostRequest(
                button.dataset.deleteDialog,
            );

            if (!response.ok) {

                messengerDebug(
                    "Dialog delete failed",
                    response.status,
                );

                button.disabled = false;

                return;

            }

            const dialogPage = document.getElementById(
                "dialog-page",
            );

            const openedDialogPublicId = dialogPage?.dataset.dialogId;

            if (
                publicId
                && openedDialogPublicId === publicId
            ) {

                window.location.href =
                    `${getLangPrefix()}/messenger/`;

                return;

            }

            if (dialogItem) {
                dialogItem.remove();
            }

        } catch (error) {

            messengerDebug(
                "Dialog delete error",
                error,
            );

            button.disabled = false;

        }

    },
);


// =====================================================
// Shared POST request
// =====================================================

async function sendPostRequest(url) {

    return fetch(
        url,
        {
            method: "POST",
            headers: {
                "X-CSRFToken": getCookie(
                    "csrftoken",
                ),
            },
        },
    );

}


// =====================================================
// Enter submit
// =====================================================

document.addEventListener(
    "keydown",
    (event) => {

        const textarea = document.activeElement;

        if (textarea?.name !== "text") {
            return;
        }

        if (
            event.key !== "Enter"
            || event.shiftKey
        ) {
            return;
        }

        event.preventDefault();

        if (!textarea.value.trim()) {
            return;
        }

        textarea.form?.requestSubmit();

    },
);