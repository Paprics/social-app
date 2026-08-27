import {
    getWebSocketUrl,
    ReconnectingSocket,
} from "../../messenger/js/includes/reconnecting_socket.js";

const BADGE_SELECTOR = "[data-messenger-unread-badge]";
const INBOX_CHANGED_EVENT = "messenger:inbox-changed";
const MAX_VISIBLE_COUNT = 99;

function formatUnreadCount(count) {
    if (count > MAX_VISIBLE_COUNT) {
        return `${MAX_VISIBLE_COUNT}+`;
    }

    return String(count);
}

function updateUnreadBadges(count) {
    document.querySelectorAll(BADGE_SELECTOR).forEach((badge) => {
        if (count <= 0) {
            badge.textContent = "";
            badge.classList.add("hidden");
            return;
        }

        badge.textContent = formatUnreadCount(count);
        badge.classList.remove("hidden");
    });
}

function dispatchInboxChanged(data) {
    document.dispatchEvent(
        new CustomEvent(INBOX_CHANGED_EVENT, {
            detail: data,
        }),
    );
}

function handleInboxMessage(event) {
    let data;

    try {
        data = JSON.parse(event.data);
    } catch {
        return;
    }

    if (data.type !== "inbox.changed") {
        return;
    }

    const unreadCount = Number(data.unread_count);

    if (!Number.isInteger(unreadCount) || unreadCount < 0) {
        return;
    }

    updateUnreadBadges(unreadCount);
    dispatchInboxChanged(data);
}

function initMessengerUnreadBadge() {
    if (!document.querySelector(BADGE_SELECTOR)) {
        return;
    }

    let socket;

    socket = new ReconnectingSocket({
        url: getWebSocketUrl("/ws/messenger/inbox/"),
        label: "Global inbox",
        shouldConnect: () => Boolean(document.querySelector(BADGE_SELECTOR)),
        onMessage: handleInboxMessage,
        onOpen: () => {
            socket.sendJson({
                type: "inbox.sync",
            });
        },
    });

    socket.start();
}

initMessengerUnreadBadge();
