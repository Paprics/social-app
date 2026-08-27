import { reloadSidebar } from "./sidebar.js";

async function handleInboxChanged() {
    if (!document.getElementById("messenger-sidebar")) {
        return;
    }

    await reloadSidebar();
}

async function initInboxRealtime() {
    if (!document.getElementById("messenger-sidebar")) {
        return;
    }

    document.addEventListener(
        "messenger:inbox-changed",
        handleInboxChanged,
    );

    await reloadSidebar();
}

initInboxRealtime();
