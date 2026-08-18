// src/video_chat/static/video_chat/js/room.js

/**
 * Клиентская логика пользовательского видеочата.
 *
 * Django-шаблон передаёт RTC и переводы через window.videoChatConfig.
 */

const VIDEO_CHAT_CONFIG = window.videoChatConfig;

if (!VIDEO_CHAT_CONFIG) {
    throw new Error("window.videoChatConfig is not defined");
}

const RTC_CONFIG = VIDEO_CHAT_CONFIG.rtcConfig;
const I18N = VIDEO_CHAT_CONFIG.i18n;

let ws = null;
let pc = null;
let pcModerator = null;
let localStream = null;

let role = null;
let chatState = "idle";
let cooldownTimer = null;
let wasKicked = false;
let startAttempt = 0;
let startSent = false;

const localVideo = document.getElementById("localVideo");
const remoteVideo = document.getElementById("remoteVideo");
const localPlaceholder = document.getElementById("localPlaceholder");
const remotePlaceholder = document.getElementById("remotePlaceholder");

const statusEl = document.getElementById("status");
const chatGenderInputs = Array.from(
    document.querySelectorAll(
        'input[name="chatGender"]'
    )
);

const btnStart = document.getElementById("btnStart");
const btnNext = document.getElementById("btnNext");
const btnStop = document.getElementById("btnStop");

const chatMessages = document.getElementById("chatMessages");
const chatInput = document.getElementById("chatInput");
const btnSend = document.getElementById("btnSend");
const chatHint = document.getElementById("chatHint");

function setState(nextState) {
    chatState = nextState;

    const isIdle = (
        nextState === "idle"
    );

    const isActive = [
        "starting",
        "searching",
        "connecting",
        "connected",
        "cooldown",
    ].includes(
        nextState
    );

    chatGenderInputs.forEach(
        (input) => {
            input.disabled = !isIdle;
        }
    );

    // В IDLE показываем только Start.
    btnStart.classList.toggle(
        "hidden",
        !isIdle
    );
    btnStart.classList.toggle(
        "inline-flex",
        isIdle
    );

    btnStart.disabled = (
        !isIdle
        || !ws
        || ws.readyState !== WebSocket.OPEN
    );

    // Во время активной сессии показываем Stop вместо Start.
    btnStop.classList.toggle(
        "hidden",
        !isActive
    );
    btnStop.classList.toggle(
        "inline-flex",
        isActive
    );

    const canSkip = (
        nextState === "connected"
    );

    btnNext.classList.toggle(
        "hidden",
        !canSkip
    );
    btnNext.classList.toggle(
        "inline-flex",
        canSkip
    );

    setChatEnabled(
        nextState === "connected"
    );
}

function setChatEnabled(enabled) {
    chatInput.disabled = !enabled;
    btnSend.disabled = !enabled;

    chatInput.placeholder = (
        enabled
            ? I18N.chatEnabled
            : I18N.chatDisabled
    );

    chatHint.textContent = (
        enabled
            ? I18N.chatHintEnabled
            : I18N.chatHintDisabled
    );
}

function setStatus(text) {
    statusEl.textContent = text;
}

function wsSend(payload) {
    if (
        !ws
        || ws.readyState !== WebSocket.OPEN
    ) {
        return false;
    }

    ws.send(
        JSON.stringify(payload)
    );

    return true;
}

function resetToIdle(statusText = I18N.idle) {
    startAttempt += 1;
    startSent = false;

    cancelCooldown();
    closePeerConnections();
    stopLocalMedia();
    clearChat();

    role = null;

    setState("idle");
    setStatus(statusText);

    if (
        ws
        && ws.readyState === WebSocket.OPEN
    ) {
        btnStart.disabled = false;
    }
}

function connectWS() {
    const protocol = (
        location.protocol === "https:"
            ? "wss"
            : "ws"
    );

    ws = new WebSocket(
        `${protocol}://${location.host}/ws/chat/`
    );

    ws.onopen = () => {
        if (chatState === "idle") {
            setStatus(I18N.idle);
            btnStart.disabled = false;
        }
    };

    ws.onmessage = async (event) => {
        const message = JSON.parse(
            event.data
        );

        switch (message.type) {
            case "started":
                startSent = true;
                setState("searching");
                return;

            case "status":
                if (message.message === "waiting") {
                    cancelCooldown();
                    clearChat();
                    setState("searching");
                    setStatus(I18N.searching);
                }
                return;

            case "matched": {
                cancelCooldown();

                role = message.role;
                const myRole = message.role;

                clearChat();
                setState("connecting");
                setStatus(I18N.connecting);

                try {
                    await setupPeerConnection();

                    if (myRole === "callee") {
                        wsSend({
                            type: "ready",
                        });
                    }
                } catch (error) {
                    console.error(
                        "[RTC] setup error:",
                        error
                    );
                }

                return;
            }

            case "cooldown":
                startCooldown(
                    message.seconds
                );
                return;

            case "partner_disconnected":
                closePeerConnections();
                clearChat();

                startCooldown(
                    message.seconds || 3
                );
                return;

            case "stopped":
                resetToIdle(
                    I18N.stopped
                );
                return;

            case "kicked":
                wasKicked = true;
                resetToIdle(
                    I18N.kicked
                );
                return;

            case "error":
                handleServerError(
                    message.code
                );
                return;
        }

        if (message.payload) {
            await handlePayload(
                message.payload
            );
        }
    };

    ws.onclose = () => {
        startSent = false;
        cancelCooldown();
        closePeerConnections();
        stopLocalMedia();
        clearChat();

        setState("idle");
        btnStart.disabled = true;

        if (!wasKicked) {
            setStatus(
                I18N.wsClosed
            );
        }
    };

    ws.onerror = (error) => {
        console.error(
            "[WS] error:",
            error
        );
    };
}

async function handlePayload(payload) {
    switch (payload.type) {
        case "ready_to_connect":
            if (role === "caller") {
                await sendOffer();
            }
            return;

        case "offer":
            if (payload.from_moderator) {
                await handleModeratorOffer(
                    payload
                );
                return;
            }

            await handlePartnerOffer(
                payload
            );
            return;

        case "answer":
            if (!pc) {
                return;
            }

            await pc.setRemoteDescription(
                new RTCSessionDescription(
                    payload.sdp
                )
            );
            return;

        case "ice_candidate":
            await handleIceCandidate(
                payload
            );
            return;

        case "chat_message":
            if (chatState === "connected") {
                appendMessage(
                    payload.text,
                    "partner"
                );
            }
            return;
    }
}

async function handlePartnerOffer(payload) {
    if (!pc) {
        return;
    }

    await pc.setRemoteDescription(
        new RTCSessionDescription(
            payload.sdp
        )
    );

    const answer = await pc.createAnswer();
    await pc.setLocalDescription(answer);

    wsSend({
        type: "answer",
        sdp: pc.localDescription,
    });
}

async function handleModeratorOffer(payload) {
    closeModeratorPeer();

    pcModerator = new RTCPeerConnection(
        RTC_CONFIG
    );

    if (localStream) {
        localStream.getTracks().forEach(
            (track) => {
                pcModerator.addTrack(
                    track,
                    localStream
                );
            }
        );
    }

    pcModerator.onicecandidate = (event) => {
        if (!event.candidate) {
            return;
        }

        wsSend({
            type: "ice_candidate",
            candidate: event.candidate,
            from_moderator_reply: true,
        });
    };

    await pcModerator.setRemoteDescription(
        new RTCSessionDescription(
            payload.sdp
        )
    );

    const answer = await pcModerator.createAnswer();
    await pcModerator.setLocalDescription(answer);

    wsSend({
        type: "answer",
        sdp: pcModerator.localDescription,
        from_moderator_reply: true,
    });
}

async function handleIceCandidate(payload) {
    try {
        if (payload.from_moderator) {
            if (!pcModerator) {
                return;
            }

            await pcModerator.addIceCandidate(
                new RTCIceCandidate(
                    payload.candidate
                )
            );
            return;
        }

        if (!pc) {
            return;
        }

        await pc.addIceCandidate(
            new RTCIceCandidate(
                payload.candidate
            )
        );
    } catch (error) {
        console.warn(
            "[RTC] ICE error:",
            error
        );
    }
}

async function setupPeerConnection() {
    // Закрываем только старые RTC peer connections.
    // Нельзя вызывать closePeerConnections() здесь:
    // она сбрасывает role текущего match.
    closeMainPeer();
    closeModeratorPeer();
    setChatEnabled(false);

    pc = new RTCPeerConnection(
        RTC_CONFIG
    );

    if (localStream) {
        localStream.getTracks().forEach(
            (track) => {
                pc.addTrack(
                    track,
                    localStream
                );
            }
        );
    }

    pc.ontrack = (event) => {
        remoteVideo.srcObject = (
            event.streams[0]
        );
        remotePlaceholder.classList.add(
            "hidden"
        );
    };

    pc.onicecandidate = (event) => {
        if (!event.candidate) {
            return;
        }

        wsSend({
            type: "ice_candidate",
            candidate: event.candidate,
        });
    };

    pc.onconnectionstatechange = () => {
        if (!pc) {
            return;
        }

        if (pc.connectionState === "connected") {
            setState("connected");
            setStatus(I18N.connected);

            wsSend({
                type: "connected",
            });
            return;
        }

        if (pc.connectionState === "failed") {
            closePeerConnections();
        }
    };
}

async function sendOffer() {
    if (!pc) {
        return;
    }

    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);

    wsSend({
        type: "offer",
        sdp: pc.localDescription,
    });
}

function closeMainPeer() {
    if (pc) {
        pc.close();
        pc = null;
    }

    remoteVideo.srcObject = null;
    remotePlaceholder.classList.remove(
        "hidden"
    );
}

function closeModeratorPeer() {
    if (pcModerator) {
        pcModerator.close();
        pcModerator = null;
    }
}

function closePeerConnections() {
    closeMainPeer();
    closeModeratorPeer();

    role = null;

    setChatEnabled(false);
}

function appendMessage(text, sender) {
    const message = document.createElement(
        "div"
    );

    message.className = (
        sender === "me"
            ? "self-end max-w-[85%] break-words rounded-2xl rounded-br-sm bg-indigo-600 px-3 py-2 text-white"
            : "self-start max-w-[85%] break-words rounded-2xl rounded-bl-sm bg-gray-700 px-3 py-2 text-gray-100"
    );

    message.textContent = text;

    chatMessages.appendChild(
        message
    );
    chatMessages.scrollTop = (
        chatMessages.scrollHeight
    );
}

function clearChat() {
    chatMessages.innerHTML = "";
}

function sendChatMessage() {
    if (chatState !== "connected") {
        return;
    }

    const text = chatInput.value.trim();

    if (
        !text
        || !ws
        || ws.readyState !== WebSocket.OPEN
    ) {
        return;
    }

    wsSend({
        type: "chat_message",
        text,
    });

    appendMessage(
        text,
        "me"
    );

    chatInput.value = "";
    chatInput.focus();
}

function startCooldown(seconds) {
    cancelCooldown();
    closePeerConnections();
    setState("cooldown");

    let remaining = Number(seconds) || 3;

    const render = () => {
        setStatus(
            `${I18N.cooldown}: ${remaining}`
        );
    };

    render();

    cooldownTimer = setInterval(
        () => {
            remaining -= 1;

            if (remaining <= 0) {
                cancelCooldown();
                setState("searching");
                setStatus(I18N.searching);

                wsSend({
                    type: "search",
                });
                return;
            }

            render();
        },
        1000
    );
}

function cancelCooldown() {
    if (cooldownTimer) {
        clearInterval(cooldownTimer);
        cooldownTimer = null;
    }
}

function handleServerError(code) {
    if (code === "invalid_gender") {
        resetToIdle(
            I18N.genderRequired
        );
        return;
    }

    console.warn(
        "[WS] server error:",
        code
    );
}

function getSelectedChatGender() {
    const selected = chatGenderInputs.find(
        (input) => input.checked
    );

    return selected ? selected.value : "";
}

function stopLocalMedia() {
    if (!localStream) {
        return;
    }

    localStream.getTracks().forEach(
        (track) => track.stop()
    );

    localStream = null;
    localVideo.srcObject = null;

    localPlaceholder.classList.remove(
        "hidden"
    );
}

async function ensureLocalMedia() {
    if (localStream) {
        return true;
    }

    setStatus(I18N.media);

    try {
        localStream = await navigator.mediaDevices.getUserMedia(
            {
                video: true,
                audio: true,
            }
        );

        localVideo.srcObject = localStream;
        localPlaceholder.classList.add(
            "hidden"
        );

        return true;
    } catch (error) {
        console.error(
            "[MEDIA] error:",
            error
        );

        setStatus(I18N.mediaError);
        return false;
    }
}

btnStart.addEventListener(
    "click",
    async () => {
        const gender = getSelectedChatGender();

        if (!gender) {
            setStatus(
                I18N.genderRequired
            );
            return;
        }

        if (
            !ws
            || ws.readyState !== WebSocket.OPEN
        ) {
            return;
        }

        const attempt = ++startAttempt;
        startSent = false;

        setState("starting");

        const mediaReady = await ensureLocalMedia();

        if (attempt !== startAttempt) {
            if (mediaReady) {
                stopLocalMedia();
            }
            return;
        }

        if (!mediaReady) {
            resetToIdle(
                I18N.mediaError
            );
            return;
        }

        startSent = wsSend({
            type: "start",
            gender,
        });

        if (!startSent) {
            resetToIdle(
                I18N.wsClosed
            );
        }
    }
);

btnNext.addEventListener(
    "click",
    () => {
        if (chatState !== "connected") {
            return;
        }

        closePeerConnections();
        clearChat();

        wsSend({
            type: "next",
        });
    }
);

btnStop.addEventListener(
    "click",
    () => {
        const shouldNotifyServer = (
            startSent
            && ws
            && ws.readyState === WebSocket.OPEN
        );

        // UI сбрасываем немедленно и полностью.
        resetToIdle(
            I18N.stopped
        );

        // Backend дочищает queue/room/participant отдельно.
        if (shouldNotifyServer) {
            wsSend({
                type: "stop",
            });
        }
    }
);

btnSend.addEventListener(
    "click",
    sendChatMessage
);

chatInput.addEventListener(
    "keydown",
    (event) => {
        if (
            event.key === "Enter"
            && !event.shiftKey
        ) {
            event.preventDefault();
            sendChatMessage();
        }
    }
);

window.addEventListener(
    "beforeunload",
    () => {
        stopLocalMedia();
    }
);

setState("idle");
connectWS();