import {
    getLangPrefix,
    messengerDebug,
} from "./utils.js";

export async function reloadSidebar() {
    const container = document.getElementById("messenger-dialog-scroll");

    if (!container) {
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
            messengerDebug("Sidebar reload failed", response.status);
            return;
        }

        container.innerHTML = await response.text();

        if (window.htmx) {
            window.htmx.process(container);
        }
    } catch (error) {
        messengerDebug("Sidebar reload error", error);
    }
}
