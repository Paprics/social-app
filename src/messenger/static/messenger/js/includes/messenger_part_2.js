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

const DIALOG_RECONNECT_MAX_DELAY = 30000;

let socket = null;
let pendingReadMessageId = null;
let dialogReconnectTimer = null;
let dialogReconnectAttempts = 0;
let allowDialogReconnect = true;


function clearDialogReconnectTimer() {

    if (dialogReconnectTimer === null) {
        return;
    }

    window.clearTimeout(
        dialogReconnectTimer,
    );

    dialogReconnectTimer = null;

}


function scheduleDialogReconnect() {

    if (
        !allowDialogReconnect
        || !dialogPage
        || dialogReconnectTimer !== null
    ) {
        return;
    }

    const delay = Math.min(
        1000 * (2 ** dialogReconnectAttempts),
        DIALOG_RECONNECT_MAX_DELAY,
    );

    dialogReconnectAttempts += 1;

    messengerDebug(
        "Dialog WS reconnect scheduled",
        delay,
    );

    dialogReconnectTimer = window.setTimeout(
        () => {
            dialogReconnectTimer = null;
            initDialogSocket();
        },
        delay,
    );

}


function reconnectDialogNow() {

    if (
        !allowDialogReconnect
        || !dialogPage
    ) {
        return;
    }

    if (
        socket
        && (
            socket.readyState === WebSocket.OPEN
            || socket.readyState === WebSocket.CONNECTING
        )
    ) {
        return;
    }

    clearDialogReconnectTimer();
    initDialogSocket();

}


function initDialogSocket() {

    if (!dialogPage) {

        messengerDebug(
            "Dialog page not found",
        );

        return;
    }

    if (
        socket
        && (
            socket.readyState === WebSocket.OPEN
            || socket.readyState === WebSocket.CONNECTING
        )
    ) {
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

        dialogReconnectAttempts = 0;
        clearDialogReconnectTimer();

        messengerDebug(
            "WS connected",
            dialogPublicId,
        );

        flushPendingRead();

    };

    socket.onclose = (event) => {

        messengerDebug(
            "WS disconnected",
            event.code,
        );

        socket = null;

        scheduleDialogReconnect();

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
     * HTTP POST создания сообщения возвращает 204 и ничего
     * не вставляет в DOM. Поэтому message.created является
     * единым realtime-путём рендера как чужого, так и своего
     * сообщения. Проверка existingMessage защищает от дублей.
     */
    const existingMessage =
        document.getElementById(
            `message-${messageId}`,
        );

    if (existingMessage) {

        if (data.is_own !== true) {
            queueMessageRead(
                messageId,
            );
        }

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

        if (data.is_own !== true) {
            queueMessageRead(
                messageId,
            );
        }

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
// Explicit read receipt
// =====================================================

function canMarkMessagesRead() {
    return (
        document.visibilityState === "visible"
        && document.hasFocus()
    );
}

function queueMessageRead(messageId) {
    if (!Number.isInteger(messageId) || messageId <= 0) {
        return;
    }

    pendingReadMessageId = Math.max(
        pendingReadMessageId ?? 0,
        messageId,
    );

    flushPendingRead();
}

function flushPendingRead() {
    if (
        pendingReadMessageId === null
        || !canMarkMessagesRead()
        || !socket
        || socket.readyState !== WebSocket.OPEN
    ) {
        return;
    }

    const messageId = pendingReadMessageId;

    socket.send(
        JSON.stringify(
            {
                type: "message.read",
                message_id: messageId,
            },
        ),
    );

    pendingReadMessageId = null;
}

document.addEventListener(
    "visibilitychange",
    () => {
        if (document.visibilityState === "visible") {
            flushPendingRead();
        }
    },
);

window.addEventListener(
    "focus",
    flushPendingRead,
);


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
// Reconnect lifecycle
// =====================================================

window.addEventListener(
    "online",
    reconnectDialogNow,
);


window.addEventListener(
    "focus",
    reconnectDialogNow,
);


document.addEventListener(
    "visibilitychange",
    () => {
        if (document.visibilityState === "visible") {
            reconnectDialogNow();
        }
    },
);


window.addEventListener(
    "beforeunload",
    () => {
        allowDialogReconnect = false;
        clearDialogReconnectTimer();

        if (socket) {
            socket.close();
        }
    },
);


// =====================================================
// Initialization
// =====================================================

initDialogSocket();