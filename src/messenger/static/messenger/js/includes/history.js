import { messengerDebug } from "./utils.js";

const MESSAGE_HISTORY_THRESHOLD = 120;

export function scrollMessagesToBottom() {
    const list = document.getElementById("message-list");

    if (list) {
        list.scrollTop = list.scrollHeight;
    }
}

export function initMessageHistoryLazyLoad() {
    const list = document.getElementById("message-list");

    if (!list || list.dataset.historyInitialized === "true") {
        return;
    }

    list.dataset.historyInitialized = "true";
    list.dataset.historyLoading = "false";

    list.addEventListener(
        "scroll",
        () => {
            if (list.scrollTop <= MESSAGE_HISTORY_THRESHOLD) {
                void loadOlderMessages(list);
            }
        },
        { passive: true },
    );
}

async function loadOlderMessages(list) {
    if (
        list.dataset.hasOlderMessages !== "true"
        || list.dataset.historyLoading === "true"
    ) {
        return;
    }

    const oldestMessageId = Number(list.dataset.oldestMessageId);
    const url = list.dataset.olderMessagesUrl;

    if (!Number.isInteger(oldestMessageId) || oldestMessageId <= 0 || !url) {
        list.dataset.hasOlderMessages = "false";
        return;
    }

    list.dataset.historyLoading = "true";

    const previousScrollHeight = list.scrollHeight;
    const previousScrollTop = list.scrollTop;

    try {
        const response = await fetch(
            `${url}?before=${oldestMessageId}`,
            {
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
            },
        );

        if (!response.ok) {
            messengerDebug("Older messages load failed", response.status);
            return;
        }

        const html = await response.text();

        if (html.trim()) {
            list.insertAdjacentHTML("afterbegin", html);
        }

        const newOldestMessageId = Number(
            response.headers.get("X-Messenger-Oldest-Id"),
        );

        if (Number.isInteger(newOldestMessageId) && newOldestMessageId > 0) {
            list.dataset.oldestMessageId = String(newOldestMessageId);
        }

        list.dataset.hasOlderMessages =
            response.headers.get("X-Messenger-Has-More") === "1"
                ? "true"
                : "false";

        list.scrollTop =
            previousScrollTop
            + (list.scrollHeight - previousScrollHeight);
    } catch (error) {
        messengerDebug("Older messages load error", error);
    } finally {
        list.dataset.historyLoading = "false";
    }
}
