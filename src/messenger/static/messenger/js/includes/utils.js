export function messengerDebug(...args) {
    console.log("[messenger]", ...args);
}

export function getLangPrefix() {
    const match = window.location.pathname.match(/^\/([a-z]{2})(?=\/|$)/i);
    return match ? `/${match[1]}` : "";
}

export function getCookie(name) {
    if (!document.cookie) {
        return null;
    }

    for (const cookie of document.cookie.split(";")) {
        const value = cookie.trim();

        if (value.startsWith(`${name}=`)) {
            return decodeURIComponent(value.substring(name.length + 1));
        }
    }

    return null;
}
