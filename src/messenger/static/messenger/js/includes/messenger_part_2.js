// src/messenger/static/messenger/js/includes/messenger_part_2.js

/*
 * Messenger frontend.
 *
 * Part 2:
 * - WebSocket connection;
 * - message.created;
 * - message.deleted;
 * - messages.read;
 * - realtime UI updates.
 */

import {
    getLangPrefix,
    messengerDebug,
    reloadSidebar,
    scrollMessagesToBottom,
} from "./messenger_part_1.js";


// =====================================================
// WebSocket
// =====================================================

const dialogPage = document.getElementById(
    "dialog-page",
);

let socket = null;


function initDialogSocket() {

    if (!dialogPage) {

        messengerDebug(
            "Dialog page not found",
        );

        return;
    }

    const dialogPublicId =
        dialogPage.dataset.dialogId;

    if (!dialogPublicId) {

        messengerDebug(
            "Dialog public ID not found",
        );

        return;
    }

    const protocol =
        window.location.protocol === "https:"
            ? "wss"
            : "ws";

    socket = new WebSocket(
        `${protocol}://${window.location.host}/ws/messenger/${dialogPublicId}/`,
    );

    socket.onopen = () => {

        messengerDebug(
            "WS connected",
            dialogPublicId,
        );

    };

    socket.onclose = (event) => {

        messengerDebug(
            "WS disconnected",
            event.code,
        );

    };

    socket.onerror = (error) => {

        messengerDebug(
            "WS error",
            error,
        );

    };

    socket.onmessage =
        handleSocketMessage;

}


// =====================================================
// WebSocket router
// =====================================================

async function handleSocketMessage(event) {

    let data;

    try {

        data = JSON.parse(
            event.data,
        );

        messengerDebug(
            "WS EVENT",
            data,
        );

    } catch (error) {

        messengerDebug(
            "Invalid WebSocket payload",
            event.data,
            error,
        );

        return;
    }

    switch (data.type) {

        case "message.created":

            await handleMessageCreated(
                data,
            );

            break;

        case "message.deleted":

            await handleMessageDeleted(
                data,
            );

            break;

        case "messages.read":

            handleMessagesRead(
                data,
            );

            break;

        default:

            messengerDebug(
                "Unknown WebSocket event",
                data.type,
            );

    }

}


// =====================================================
// Message created
// =====================================================

async function handleMessageCreated(data) {

    const messageId = Number(
        data.message_id,
    );

    if (
        !Number.isInteger(messageId)
        || messageId <= 0
    ) {

        messengerDebug(
            "message.created without valid message_id",
            data,
        );

        return;
    }

    /*
     * Свое сообщение уже рендерится ответом формы.
     * WebSocket нужен здесь только для синхронизации
     * sidebar.
     */
    if (data.is_own === true) {

        await reloadSidebar();

        return;
    }

    const existingMessage =
        document.getElementById(
            `message-${messageId}`,
        );

    if (existingMessage) {

        await reloadSidebar();

        return;
    }

    try {

        const response = await fetch(
            `${getLangPrefix()}/messenger/messages/${messageId}/`,
            {
                headers: {
                    "X-Requested-With":
                        "XMLHttpRequest",
                },
            },
        );

        if (!response.ok) {

            messengerDebug(
                "Message load error",
                response.status,
            );

            return;
        }

        const messageList =
            document.getElementById(
                "message-list",
            );

        if (!messageList) {

            messengerDebug(
                "message-list not found",
            );

            return;
        }

        const html =
            await response.text();

        messageList.insertAdjacentHTML(
            "beforeend",
            html,
        );

        scrollMessagesToBottom();

        await reloadSidebar();

    } catch (error) {

        messengerDebug(
            "Message fetch failed",
            error,
        );

    }

}


// =====================================================
// Message deleted
// =====================================================

async function handleMessageDeleted(data) {

    const messageId = Number(
        data.message_id,
    );

    if (
        !Number.isInteger(messageId)
        || messageId <= 0
    ) {
        return;
    }

    const message =
        document.getElementById(
            `message-${messageId}`,
        );

    if (message) {
        message.remove();
    }

    await reloadSidebar();

}


// =====================================================
// Messages read
// =====================================================

function handleMessagesRead(data) {

    const lastReadMessageId = Number(
        data.last_read_message_id,
    );

    if (
        !Number.isInteger(
            lastReadMessageId,
        )
    ) {

        messengerDebug(
            "messages.read has invalid last_read_message_id",
            data,
        );

        return;
    }

    const statuses =
        document.querySelectorAll(
            ".message-status[data-message-id]",
        );

    statuses.forEach(
        (status) => {

            const messageId = Number(
                status.dataset.messageId,
            );

            if (
                Number.isInteger(messageId)
                && messageId <= lastReadMessageId
            ) {

                status.textContent = "✓✓";
                status.dataset.read = "true";

            }

        },
    );

}


// =====================================================
// Initialization
// =====================================================

initDialogSocket();