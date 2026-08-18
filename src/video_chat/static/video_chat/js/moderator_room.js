// src/video_chat/static/video_chat/js/moderator_room.js

/**
 * Клиентская WebRTC-логика staff-панели активной видеочат-комнаты.
 *
 * Django-шаблон передаёт room-specific данные через window.videoChatModeratorConfig.
 */

const MODERATOR_CONFIG = window.videoChatModeratorConfig;

if (!MODERATOR_CONFIG) {
    throw new Error("window.videoChatModeratorConfig is not defined");
}

const ROOM_ID = MODERATOR_CONFIG.roomId;
const CALLER = MODERATOR_CONFIG.caller;
const CALLEE = MODERATOR_CONFIG.callee;
const RTC_CONFIG = MODERATOR_CONFIG.rtcConfig;

let ws = null;
let pcCaller = null;
let pcCallee = null;

const videoUser1 = document.getElementById("videoUser1");
const videoUser2 = document.getElementById("videoUser2");
const modStatus = document.getElementById("modStatus");
const modLog = document.getElementById("modLog");

function log(message) {
    const element = document.createElement("div");

    element.textContent = (
        `[${new Date().toLocaleTimeString()}] ${message}`
    );

    modLog.appendChild(element);
    modLog.scrollTop = modLog.scrollHeight;
}

function setStatus(text) {
    modStatus.textContent = text;
    log(text);
}

function wsSend(data) {
    if (
        ws
        && ws.readyState === WebSocket.OPEN
    ) {
        ws.send(
            JSON.stringify(data)
        );
        return;
    }

    log("WS не открыт — сообщение не отправлено");
}

function connectWS() {
    const protocol = location.protocol === "https:" ? "wss" : "ws";

    ws = new WebSocket(
        `${protocol}://${location.host}/ws/chat/moderate/${ROOM_ID}/`
    );

    ws.onopen = () => {
        setStatus("Подключён к комнате");
    };

    ws.onmessage = async (event) => {
        const message = JSON.parse(event.data);

        if (message.type === "room_info") {
            log(
                `Комната: caller=...${message.caller.slice(-8)}, `
                + `callee=...${message.callee.slice(-8)}`
            );

            await setupPeerWith(
                CALLER,
                "caller"
            );

            await setupPeerWith(
                CALLEE,
                "callee"
            );

            return;
        }

        if (message.type === "kick_sent") {
            log(
                `Kick отправлен пользователю ...${message.target.slice(-8)}`
            );
            return;
        }

        if (message.payload) {
            await handleSignaling(
                message.payload
            );
        }
    };

    ws.onclose = () => {
        setStatus(
            "WebSocket закрыт — комната завершена"
        );

        closePeers();
    };

    ws.onerror = (error) => {
        log(
            `WS ошибка: ${error}`
        );
    };
}

async function setupPeerWith(
    targetChannel,
    role
) {
    const peer = new RTCPeerConnection(
        RTC_CONFIG
    );

    peer.ontrack = (event) => {
        log(
            `Получен видеопоток от ${role}`
        );

        if (role === "caller") {
            videoUser1.srcObject = event.streams[0];
            return;
        }

        videoUser2.srcObject = event.streams[0];
    };

    peer.onicecandidate = (event) => {
        if (!event.candidate) {
            return;
        }

        wsSend({
            type: "ice_candidate",
            candidate: event.candidate,
            target: targetChannel,
            from_role: role,
        });
    };

    peer.onconnectionstatechange = () => {
        log(
            `${role}: ${peer.connectionState}`
        );
    };

    if (role === "caller") {
        pcCaller = peer;
    } else {
        pcCallee = peer;
    }

    // Модератор только принимает медиа.
    peer.addTransceiver(
        "video",
        {
            direction: "recvonly",
        }
    );

    peer.addTransceiver(
        "audio",
        {
            direction: "recvonly",
        }
    );

    const offer = await peer.createOffer();

    await peer.setLocalDescription(
        offer
    );

    wsSend({
        type: "offer",
        sdp: peer.localDescription,
        target: targetChannel,
        from_role: role,
    });

    log(
        `Offer отправлен → ${role}`
    );
}

async function handleSignaling(payload) {
    // После backend-изоляции сюда должны попадать только ответы
    // participant → moderator.
    if (!payload.from_moderator_reply) {
        return;
    }

    const channel = payload.answering_channel;

    let peer = null;
    let role = null;

    if (channel === CALLER) {
        peer = pcCaller;
        role = "caller";
    } else if (channel === CALLEE) {
        peer = pcCallee;
        role = "callee";
    } else {
        log(
            "Игнорирован signaling от неизвестного канала"
        );
        return;
    }

    if (!peer) {
        return;
    }

    try {
        if (payload.type === "answer") {
            log(
                `Answer от ${role}`
            );

            await peer.setRemoteDescription(
                new RTCSessionDescription(
                    payload.sdp
                )
            );

            return;
        }

        if (payload.type === "ice_candidate") {
            await peer.addIceCandidate(
                new RTCIceCandidate(
                    payload.candidate
                )
            );
        }
    } catch (error) {
        log(
            `Ошибка ${role}: ${error.message}`
        );
    }
}

function kickUser(role) {
    const target = (
        role === "caller"
            ? CALLER
            : CALLEE
    );

    if (
        !confirm(
            `Кикнуть пользователя (${role})?`
        )
    ) {
        return;
    }

    wsSend({
        type: "kick",
        target,
    });
}

function closePeers() {
    if (pcCaller) {
        pcCaller.close();
        pcCaller = null;
    }

    if (pcCallee) {
        pcCallee.close();
        pcCallee = null;
    }

    videoUser1.srcObject = null;
    videoUser2.srcObject = null;
}

document.querySelectorAll("[data-kick-role]").forEach(
    (button) => {
        button.addEventListener(
            "click",
            () => {
                kickUser(
                    button.dataset.kickRole
                );
            }
        );
    }
);

connectWS();