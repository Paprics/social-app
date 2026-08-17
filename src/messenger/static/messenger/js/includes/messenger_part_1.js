/*
 * Messenger frontend.
 *
 * Part 1:
 * - debug;
 * - URL helpers;
 * - CSRF helpers;
 * - common DOM functions;
 * - message history lazy loading;
 * - sidebar reload.
 */


// =====================================================
// DEBUG LOGGING
// =====================================================

export function messengerDebug(...args) {
    console.log(
        "[messenger]",
        ...args,
    );
}


// =====================================================
// URL helpers
// =====================================================

export function getLangPrefix() {

    const match = window.location.pathname.match(
        /^\/([a-z]{2})(?=\/|$)/i,
    );

    return match
        ? `/${match[1]}`
        : "";

}


// =====================================================
// CSRF helpers
// =====================================================

export function getCookie(name) {

    if (!document.cookie) {
        return null;
    }

    const cookies = document.cookie.split(";");

    for (const cookie of cookies) {

        const value = cookie.trim();

        if (value.startsWith(`${name}=`)) {

            return decodeURIComponent(
                value.substring(name.length + 1),
            );

        }

    }

    return null;

}


// =====================================================
// Message list
// =====================================================

const MESSAGE_HISTORY_THRESHOLD = 120;


export function scrollMessagesToBottom() {

    const list = document.getElementById(
        "message-list",
    );

    if (!list) {
        return;
    }

    list.scrollTop = list.scrollHeight;

}


export function initMessageHistoryLazyLoad() {

    const list = document.getElementById(
        "message-list",
    );

    if (
        !list
        || list.dataset.historyInitialized === "true"
    ) {
        return;
    }

    list.dataset.historyInitialized = "true";
    list.dataset.historyLoading = "false";

    list.addEventListener(
        "scroll",
        () => {

            if (list.scrollTop > MESSAGE_HISTORY_THRESHOLD) {
                return;
            }

            void loadOlderMessages(
                list,
            );

        },
        {
            passive: true,
        },
    );

}


async function loadOlderMessages(list) {

    if (
        list.dataset.hasOlderMessages !== "true"
        || list.dataset.historyLoading === "true"
    ) {
        return;
    }

    const oldestMessageId = Number(
        list.dataset.oldestMessageId,
    );

    const url = list.dataset.olderMessagesUrl;

    if (
        !Number.isInteger(oldestMessageId)
        || oldestMessageId <= 0
        || !url
    ) {
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

            messengerDebug(
                "Older messages load failed",
                response.status,
            );

            return;
        }

        const html = await response.text();

        if (html.trim()) {

            list.insertAdjacentHTML(
                "afterbegin",
                html,
            );

        }

        const newOldestMessageId = Number(
            response.headers.get(
                "X-Messenger-Oldest-Id",
            ),
        );

        if (
            Number.isInteger(newOldestMessageId)
            && newOldestMessageId > 0
        ) {
            list.dataset.oldestMessageId = String(
                newOldestMessageId,
            );
        }

        list.dataset.hasOlderMessages =
            response.headers.get(
                "X-Messenger-Has-More",
            ) === "1"
                ? "true"
                : "false";

        const newScrollHeight = list.scrollHeight;

        list.scrollTop =
            previousScrollTop
            + (
                newScrollHeight
                - previousScrollHeight
            );

    } catch (error) {

        messengerDebug(
            "Older messages load error",
            error,
        );

    } finally {

        list.dataset.historyLoading = "false";

    }

}


// =====================================================
// Sidebar
// =====================================================

export async function reloadSidebar() {

    const dialogScroll = document.getElementById(
        "messenger-dialog-scroll",
    );

    if (!dialogScroll) {
        return;
    }

    try {

        const response = await fetch(
            `${getLangPrefix()}/messenger/sidebar/`,
            {
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
            },
        );

        if (!response.ok) {

            messengerDebug(
                "Sidebar reload failed",
                response.status,
            );

            return;
        }

        const html = await response.text();

        dialogScroll.innerHTML = html;

        if (window.htmx) {
            window.htmx.process(
                dialogScroll,
            );
        }

    } catch (error) {

        messengerDebug(
            "Sidebar reload error",
            error,
        );

    }

}