import { messengerDebug } from "./utils.js";

const DEFAULT_MAX_RECONNECT_DELAY = 30000;

export class ReconnectingSocket {
    constructor({
        url,
        label,
        onMessage,
        onOpen = null,
        shouldConnect = () => true,
        maxReconnectDelay = DEFAULT_MAX_RECONNECT_DELAY,
    }) {
        this.url = url;
        this.label = label;
        this.onMessage = onMessage;
        this.onOpen = onOpen;
        this.shouldConnect = shouldConnect;
        this.maxReconnectDelay = maxReconnectDelay;

        this.socket = null;
        this.reconnectTimer = null;
        this.reconnectAttempts = 0;
        this.stopped = false;
        this.lifecycleBound = false;

        this.reconnectNow = this.reconnectNow.bind(this);
        this.handleVisibilityChange = this.handleVisibilityChange.bind(this);
        this.stop = this.stop.bind(this);
    }

    start() {
        if (this.stopped) {
            return;
        }

        this.bindLifecycleEvents();
        this.connect();
    }

    sendJson(payload) {
        if (!this.isOpen()) {
            return false;
        }

        this.socket.send(JSON.stringify(payload));
        return true;
    }

    isOpen() {
        return this.socket?.readyState === WebSocket.OPEN;
    }

    connect() {
        if (
            this.stopped
            || !this.shouldConnect()
            || this.isConnectingOrOpen()
        ) {
            return;
        }

        this.socket = new WebSocket(this.url);

        this.socket.onopen = async () => {
            this.reconnectAttempts = 0;
            this.clearReconnectTimer();
            messengerDebug(`${this.label} WS connected`);

            if (this.onOpen) {
                await this.onOpen();
            }
        };

        this.socket.onmessage = this.onMessage;

        this.socket.onerror = (error) => {
            messengerDebug(`${this.label} WS error`, error);
        };

        this.socket.onclose = (event) => {
            messengerDebug(`${this.label} WS disconnected`, event.code);
            this.socket = null;
            this.scheduleReconnect();
        };
    }

    reconnectNow() {
        if (
            this.stopped
            || !this.shouldConnect()
            || this.isConnectingOrOpen()
        ) {
            return;
        }

        this.clearReconnectTimer();
        this.connect();
    }

    scheduleReconnect() {
        if (
            this.stopped
            || !this.shouldConnect()
            || this.reconnectTimer !== null
        ) {
            return;
        }

        const delay = Math.min(
            1000 * (2 ** this.reconnectAttempts),
            this.maxReconnectDelay,
        );

        this.reconnectAttempts += 1;
        messengerDebug(`${this.label} WS reconnect scheduled`, delay);

        this.reconnectTimer = window.setTimeout(() => {
            this.reconnectTimer = null;
            this.connect();
        }, delay);
    }

    clearReconnectTimer() {
        if (this.reconnectTimer === null) {
            return;
        }

        window.clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
    }

    isConnectingOrOpen() {
        return Boolean(
            this.socket
            && (
                this.socket.readyState === WebSocket.OPEN
                || this.socket.readyState === WebSocket.CONNECTING
            )
        );
    }

    bindLifecycleEvents() {
        if (this.lifecycleBound) {
            return;
        }

        this.lifecycleBound = true;
        window.addEventListener("online", this.reconnectNow);
        window.addEventListener("focus", this.reconnectNow);
        document.addEventListener(
            "visibilitychange",
            this.handleVisibilityChange,
        );
        window.addEventListener("beforeunload", this.stop);
    }

    unbindLifecycleEvents() {
        if (!this.lifecycleBound) {
            return;
        }

        this.lifecycleBound = false;
        window.removeEventListener("online", this.reconnectNow);
        window.removeEventListener("focus", this.reconnectNow);
        document.removeEventListener(
            "visibilitychange",
            this.handleVisibilityChange,
        );
        window.removeEventListener("beforeunload", this.stop);
    }

    handleVisibilityChange() {
        if (document.visibilityState === "visible") {
            this.reconnectNow();
        }
    }

    stop() {
        if (this.stopped) {
            return;
        }

        this.stopped = true;
        this.clearReconnectTimer();
        this.unbindLifecycleEvents();

        if (this.socket) {
            this.socket.onclose = null;
            this.socket.close();
            this.socket = null;
        }
    }
}

export function getWebSocketUrl(path) {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    return `${protocol}://${window.location.host}${path}`;
}
