/*
 * Per-user inbox WebSocket.
 *
 * Keeps sidebar/unread counters realtime and reconnects
 * automatically after server reloads or temporary disconnects.
 */

import {
    messengerDebug,
    reloadSidebar,
} from "./messenger_part_1.js";


const RECONNECT_MAX_DELAY = 30000;

let inboxSocket = null;
let reconnectTimer = null;
let reconnectAttempts = 0;
let allowReconnect = true;


function hasMessengerSidebar() {
    return Boolean(
        document.getElementById(
            "messenger-sidebar",
        ),
    );
}


function getReconnectDelay() {
    return Math.min(
        1000 * (2 ** reconnectAttempts),
        RECONNECT_MAX_DELAY,
    );
}


function clearReconnectTimer() {
    if (reconnectTimer === null) {
        return;
    }

    window.clearTimeout(
        reconnectTimer,
    );

    reconnectTimer = null;
}


function scheduleInboxReconnect() {
    if (
        !allowReconnect
        || !hasMessengerSidebar()
        || reconnectTimer !== null
    ) {
        return;
    }

    const delay = getReconnectDelay();

    reconnectAttempts += 1;

    messengerDebug(
        "Inbox WS reconnect scheduled",
        delay,
    );

    reconnectTimer = window.setTimeout(
        () => {
            reconnectTimer = null;
            initInboxSocket();
        },
        delay,
    );
}


function reconnectInboxNow() {
    if (
        !allowReconnect
        || !hasMessengerSidebar()
    ) {
        return;
    }

    if (
        inboxSocket
        && (
            inboxSocket.readyState === WebSocket.OPEN
            || inboxSocket.readyState === WebSocket.CONNECTING
        )
    ) {
        return;
    }

    clearReconnectTimer();
    initInboxSocket();
}


function initInboxSocket() {
    if (
        !allowReconnect
        || !hasMessengerSidebar()
    ) {
        return;
    }

    if (
        inboxSocket
        && (
            inboxSocket.readyState === WebSocket.OPEN
            || inboxSocket.readyState === WebSocket.CONNECTING
        )
    ) {
        return;
    }

    const protocol =
        window.location.protocol === "https:"
            ? "wss"
            : "ws";

    inboxSocket = new WebSocket(
        `${protocol}://${window.location.host}/ws/messenger/inbox/`,
    );

    inboxSocket.onopen = async () => {
        reconnectAttempts = 0;
        clearReconnectTimer();

        messengerDebug(
            "Inbox WS connected",
        );

        /*
         * We may have missed events while disconnected.
         * Make server state authoritative after reconnect.
         */
        await reloadSidebar();
    };

    inboxSocket.onclose = (event) => {
        messengerDebug(
            "Inbox WS disconnected",
            event.code,
        );

        inboxSocket = null;

        scheduleInboxReconnect();
    };

    inboxSocket.onerror = (error) => {
        messengerDebug(
            "Inbox WS error",
            error,
        );
    };

    inboxSocket.onmessage = async (event) => {
        let data;

        try {
            data = JSON.parse(
                event.data,
            );
        } catch (error) {
            messengerDebug(
                "Invalid inbox WS payload",
                error,
            );
            return;
        }

        if (data.type !== "inbox.changed") {
            return;
        }

        await reloadSidebar();
    };
}


window.addEventListener(
    "online",
    reconnectInboxNow,
);


window.addEventListener(
    "focus",
    reconnectInboxNow,
);


document.addEventListener(
    "visibilitychange",
    () => {
        if (document.visibilityState === "visible") {
            reconnectInboxNow();
        }
    },
);


window.addEventListener(
    "beforeunload",
    () => {
        allowReconnect = false;
        clearReconnectTimer();

        if (inboxSocket) {
            inboxSocket.close();
        }
    },
);


initInboxSocket();
