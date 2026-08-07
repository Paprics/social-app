/*
 * Messenger frontend.
 *
 * Part 1:
 * - debug;
 * - URL helpers;
 * - CSRF helpers;
 * - common DOM functions;
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

export function scrollMessagesToBottom() {

    const list = document.getElementById(
        "message-list",
    );

    if (!list) {
        return;
    }

    list.scrollTop = list.scrollHeight;

}


// =====================================================
// Sidebar
// =====================================================

export async function reloadSidebar() {

    const sidebar = document.getElementById(
        "messenger-sidebar",
    );

    if (!sidebar) {
        return;
    }

    try {

        const response = await fetch(
            `${getLangPrefix()}/messenger/sidebar/`,
        );

        if (!response.ok) {

            messengerDebug(
                "Sidebar reload failed",
                response.status,
            );

            return;

        }

        const html = await response.text();

        const parser = new DOMParser();

        const documentFragment = parser.parseFromString(
            html,
            "text/html",
        );

        const newSidebar = documentFragment.getElementById(
            "messenger-sidebar",
        );

        if (!newSidebar) {

            messengerDebug(
                "New sidebar not found",
            );

            return;

        }

        sidebar.replaceWith(
            newSidebar,
        );

    } catch (error) {

        messengerDebug(
            "Sidebar reload error",
            error,
        );

    }

}