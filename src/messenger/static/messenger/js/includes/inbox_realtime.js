import { messengerDebug } from "./utils.js";
import { reloadSidebar } from "./sidebar.js";
import {
    getWebSocketUrl,
    ReconnectingSocket,
} from "./reconnecting_socket.js";

async function handleInboxMessage(event) {
    let data;

    try {
        data = JSON.parse(event.data);
    } catch (error) {
        messengerDebug("Invalid inbox WS payload", error);
        return;
    }

    if (data.type !== "inbox.changed") {
        return;
    }

    await reloadSidebar();
}

function initInboxRealtime() {
    if (!document.getElementById("messenger-sidebar")) {
        return;
    }

    const socket = new ReconnectingSocket({
        url: getWebSocketUrl("/ws/messenger/inbox/"),
        label: "Inbox",
        shouldConnect: () => Boolean(document.getElementById("messenger-sidebar")),
        onMessage: handleInboxMessage,
        onOpen: reloadSidebar,
    });

    socket.start();
}

initInboxRealtime();
