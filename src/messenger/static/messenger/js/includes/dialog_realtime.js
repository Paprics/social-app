import {
    getLangPrefix,
    messengerDebug,
} from "./utils.js";
import { scrollMessagesToBottom } from "./history.js";
import {
    getWebSocketUrl,
    ReconnectingSocket,
} from "./reconnecting_socket.js";

const dialogPage = document.getElementById("dialog-page");
let pendingReadMessageId = null;
let dialogSocket = null;

function canMarkMessagesRead() {
    return document.visibilityState === "visible" && document.hasFocus();
}

function queueMessageRead(messageId) {
    if (!Number.isInteger(messageId) || messageId <= 0) {
        return;
    }

    pendingReadMessageId = Math.max(pendingReadMessageId ?? 0, messageId);
    flushPendingRead();
}

function flushPendingRead() {
    if (pendingReadMessageId === null || !canMarkMessagesRead()) {
        return;
    }

    const sent = dialogSocket?.sendJson({
        type: "message.read",
        message_id: pendingReadMessageId,
    });

    if (sent) {
        pendingReadMessageId = null;
    }
}

async function handleSocketMessage(event) {
    let data;

    try {
        data = JSON.parse(event.data);
    } catch (error) {
        messengerDebug("Invalid dialog WS payload", event.data, error);
        return;
    }

    switch (data.type) {
        case "message.created":
            await handleMessageCreated(data);
            break;
        case "message.deleted":
            handleMessageDeleted(data);
            break;
        case "dialog.deleted":
            handleDialogDeleted();
            break;
        case "messages.read":
            handleMessagesRead(data);
            break;
        default:
            messengerDebug("Unknown dialog WS event", data.type);
    }
}

async function handleMessageCreated(data) {
    const messageId = Number(data.message_id);

    if (!Number.isInteger(messageId) || messageId <= 0) {
        messengerDebug("message.created without valid message_id", data);
        return;
    }

    if (document.getElementById(`message-${messageId}`)) {
        if (data.is_own !== true) {
            queueMessageRead(messageId);
        }
        return;
    }

    try {
        const response = await fetch(
            `${getLangPrefix()}/messenger/messages/${messageId}/`,
            {
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
            },
        );

        if (!response.ok) {
            messengerDebug("Message load error", response.status);
            return;
        }

        const messageList = document.getElementById("message-list");

        if (!messageList) {
            return;
        }

        messageList.insertAdjacentHTML("beforeend", await response.text());

        if (data.is_own !== true) {
            queueMessageRead(messageId);
        }

        scrollMessagesToBottom();
    } catch (error) {
        messengerDebug("Message fetch failed", error);
    }
}

function handleMessageDeleted(data) {
    const messageId = Number(data.message_id);

    if (Number.isInteger(messageId) && messageId > 0) {
        document.getElementById(`message-${messageId}`)?.remove();
    }
}

function handleDialogDeleted() {
    window.location.replace(
        `${getLangPrefix()}/messenger/`,
    );
}

function handleMessagesRead(data) {
    const lastReadMessageId = Number(data.last_read_message_id);

    if (!Number.isInteger(lastReadMessageId)) {
        messengerDebug("messages.read has invalid last_read_message_id", data);
        return;
    }

    document
        .querySelectorAll(".message-status[data-message-id]")
        .forEach((status) => {
            const messageId = Number(status.dataset.messageId);

            if (Number.isInteger(messageId) && messageId <= lastReadMessageId) {
                status.textContent = "✓✓";
                status.dataset.read = "true";
            }
        });
}

function initDialogRealtime() {
    const publicId = dialogPage?.dataset.dialogId;

    if (!publicId) {
        return;
    }

    dialogSocket = new ReconnectingSocket({
        url: getWebSocketUrl(`/ws/messenger/${publicId}/`),
        label: "Dialog",
        shouldConnect: () => Boolean(document.getElementById("dialog-page")),
        onMessage: handleSocketMessage,
        onOpen: flushPendingRead,
    });

    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible") {
            flushPendingRead();
        }
    });
    window.addEventListener("focus", flushPendingRead);

    dialogSocket.start();
}

initDialogRealtime();
