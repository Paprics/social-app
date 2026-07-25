# Архитектура анонимного видеочата

## Что это такое

Сервис анонимного рандомного видеочата — аналог Omegle/Chatroulette.
Два случайных пользователя соединяются для видео и текстового общения.
Есть панель модератора для наблюдения и кика участников.

---

## Технологический стек и зачем каждый компонент

| Компонент | Зачем |
|---|---|
| **Django** | Основной веб-фреймворк, HTTP запросы, шаблоны |
| **Django Channels** | Расширение Django для WebSocket соединений |
| **Daphne** | ASGI сервер — умеет держать WebSocket соединения (обычный Gunicorn не умеет) |
| **Redis** | Хранит очередь ожидания, список комнат, передаёт сообщения между WebSocket workers |
| **WebRTC** | Браузерная технология для P2P видео/аудио напрямую между пользователями |
| **coturn** | TURN сервер — relay для пользователей которые не могут соединиться напрямую |

---

## Как работает соединение двух пользователей

### Шаг 1 — Пользователь открывает /chat/

```
Браузер → GET /chat/ → Django рендерит room.html
```

Страница загружается. JavaScript запрашивает доступ к камере и микрофону.

### Шаг 2 — Открывается WebSocket

```
Браузер → WebSocket ws://host/ws/chat/ → SignalingConsumer.connect()
```

WebSocket — это постоянное двустороннее соединение между браузером и сервером.
В отличие от обычного HTTP где браузер спрашивает → сервер отвечает → соединение закрывается,
WebSocket остаётся открытым и сервер может сам отправлять сообщения браузеру в любой момент.

### Шаг 3 — Матчмейкинг (поиск партнёра)

```
SignalingConsumer.connect()
    → _find_partner()
        → matchmaking.leave_queue()   # убираем дубли
        → отправляем клиенту {type: "status", message: "waiting"}
        → matchmaking.join_queue()    # пробуем взять партнёра из очереди
```

**Очередь в Redis** — это список channel_name (уникальных идентификаторов WebSocket соединений).

```
Redis: chat:queue = ["specific.xxx!aaa", "specific.xxx!bbb", ...]
                     ↑ первый ждущий пользователь
```

- Если очередь пуста — кладём себя в конец и ждём
- Если есть кто-то — берём его из очереди и создаём пару

### Шаг 4 — Создание комнаты

Когда нашёлся партнёр, один становится **caller**, другой — **callee**.

```
_create_room(partner_channel):
    → room_id = uuid4()              # уникальный ID комнаты
    → room_storage.create_room()     # сохраняем в Redis (для модератора)
    → send_json({type: "matched", role: "caller"})   # сообщаем себе
    → channel_layer.send(partner, {type: "room.matched", ...})  # сообщаем партнёру
```

**channel_layer** — это шина сообщений через Redis. Позволяет одному WebSocket worker-у
отправить сообщение другому WebSocket worker-у напрямую.

```
Caller Worker ──channel_layer.send()──→ Redis ──→ Callee Worker
```

Callee получает сообщение и его метод `room_matched()` вызывается автоматически Django Channels.

### Шаг 5 — WebRTC Handshake (согласование соединения)

Это самая сложная часть. WebRTC нужно согласовать параметры соединения перед тем
как пустить видео. Этот процесс называется **сигналинг**.

```
CALLEE:
1. setupPeerConnection()     # создаём RTCPeerConnection
2. wsSend({type: "ready"})   # говорим caller-у что готовы

СЕРВЕР (SignalingConsumer.receive):
3. Получает "ready" от callee
4. Пересылает caller-у как {type: "ready_to_connect"}

CALLER:
5. Получает "ready_to_connect"
6. sendOffer()               # создаём и отправляем offer

СЕРВЕР:
7. Получает offer от caller
8. Пересылает callee

CALLEE:
9. Получает offer
10. setRemoteDescription(offer)   # принимаем параметры caller-а
11. createAnswer()                # создаём ответ
12. wsSend({type: "answer", ...}) # отправляем обратно

СЕРВЕР:
13. Получает answer от callee
14. Пересылает caller-у

CALLER:
15. Получает answer
16. setRemoteDescription(answer)  # принимаем параметры callee

Оба:
17. Обмен ICE кандидатами        # согласование сетевых адресов
18. P2P соединение установлено   # видео/аудио идут напрямую!
```

**Почему handshake через "ready"?**
Без него caller мог отправить offer до того как callee создал RTCPeerConnection.
Тогда offer некуда было бы применить — гонка состояний. "ready" гарантирует
что callee готов принять offer.

### Шаг 6 — P2P видео/аудио

После установки соединения видео и аудио идут **напрямую между браузерами**,
минуя сервер. Сервер больше не участвует в передаче медиа.

```
Браузер 1 ←────────── P2P WebRTC ──────────→ Браузер 2
              (видео/аудио напрямую)

Браузер 1 ←── WebSocket ──→ Сервер ←── WebSocket ──→ Браузер 2
              (только текстовый чат и управляющие сообщения)
```

### Шаг 7 — Текстовый чат

Текстовые сообщения идут через тот же WebSocket что и сигналинг:

```
Пользователь пишет сообщение
→ wsSend({type: "chat_message", text: "..."})
→ SignalingConsumer.receive()
→ channel_layer.send(partner_channel, ...)
→ партнёр получает {payload: {type: "chat_message", text: "..."}}
→ appendMessage() добавляет в UI
```

---

## Кнопка "Следующий"

```
Пользователь нажимает кнопку
→ closePeer()                    # закрываем RTCPeerConnection
→ wsSend({type: "next"})

Сервер (_handle_next):
→ сбрасываем partner_channel, room_id
→ удаляем комнату из Redis
→ уведомляем партнёра {type: "partner.disconnected"}
→ _find_partner()                # ищем нового партнёра

Партнёр:
→ получает "partner_disconnected"
→ показывает "Партнёр отключился. Нажмите Следующий."
→ НЕ ищет нового партнёра автоматически — ждёт кнопки
```

**Важно:** WebSocket при нажатии "Следующий" НЕ закрывается.
Пересоздаётся только RTCPeerConnection. Это быстрее и надёжнее.

---

## Панель модератора

### Список комнат

```
Модератор открывает /chat/moderate/
→ ModeratorListView.get()
→ RoomStorage.list_rooms()      # читаем из Redis: chat:rooms hash
→ рендерим страницу со списком

Каждые 5 секунд HTMX делает GET /chat/moderate/
→ сервер возвращает только HTML фрагмент (partial)
→ HTMX заменяет содержимое #room-list
```

**HTMX** — библиотека которая позволяет делать AJAX запросы через HTML атрибуты
без написания JavaScript. `hx-trigger="every 5s"` — автоматический polling.

### Подключение к комнате

```
Модератор открывает /chat/moderate/{room_id}/
→ ModeratorRoomView проверяет что комната существует в Redis
→ рендерит moderator_room.html

Фронт открывает WebSocket ws://host/ws/chat/moderate/{room_id}/
→ ModeratorConsumer.connect()
→ проверяет is_staff
→ вступает в channel group "moderate_{room_id}"
→ отправляет {type: "room_info", caller: "...", callee: "..."}
```

### WebRTC mesh на троих

Модератор устанавливает два отдельных P2P соединения:

```
Пользователь 1 ←──P2P──→ Пользователь 2   (существующее, не трогаем)
Пользователь 1 ←──P2P──→ Модератор         (новое)
Пользователь 2 ←──P2P──→ Модератор         (новое)
```

Модератор отправляет offer каждому участнику с `direction: recvonly` —
это означает "хочу получать видео, свою камеру не отправляю".

Участники получают offer через `signaling_message` и создают отдельный
`pcModerator` (не путать с основным `pc` для соединения между собой).

### Kick

```
Модератор нажимает Kick
→ wsSend({type: "kick", target: channel_name})
→ ModeratorConsumer.receive()
→ channel_layer.send(target, {type: "moderator.kick"})
→ SignalingConsumer.moderator_kick()
→ send_json({type: "kicked"})
→ self.close()                  # принудительно закрываем WebSocket
→ Браузер пользователя: WebSocket закрыт
```

---

## STUN и TURN — зачем нужны

**Проблема NAT:** Большинство пользователей не имеют публичного IP адреса.
Они сидят за роутером (NAT). Два пользователя за NAT не могут просто так
соединиться напрямую — они не знают реальные IP адреса друг друга.

**STUN** (Session Traversal Utilities for NAT):
- Бесплатный сервер (используем Google: stun.l.google.com)
- Говорит браузеру "твой публичный IP это X.X.X.X"
- Работает для большинства случаев (простой NAT, домашний роутер)

**TURN** (Traversal Using Relays around NAT):
- Наш сервер (coturn)
- Если P2P не получилось — медиа идёт через него как relay
- Нужен для: корпоративные файрволы, симметричный NAT, мобильные операторы
- На локалке не нужен — пользователи в одной сети

```
Без TURN (P2P):          Браузер 1 ←──────────→ Браузер 2

С TURN (relay):          Браузер 1 ←── coturn ──→ Браузер 2
```

---

## Структура файлов

```
chat/
├── consumers/
│   ├── signaling.py      # WebSocket для пользователей чата
│   └── moderator.py      # WebSocket для модератора
├── services/
│   ├── matchmaking.py    # Очередь в Redis, поиск партнёра
│   ├── room_storage.py   # Список активных комнат в Redis
│   ├── chat_storage.py   # Хранение текстового чата в Redis (TTL)
│   └── rtc_config.py     # STUN/TURN конфиг из переменных окружения
├── templates/chat/
│   ├── room.html          # Страница пользователя (WebRTC + чат)
│   ├── moderator_list.html    # Список комнат
│   ├── moderator_room.html    # Просмотр комнаты модератором
│   └── partials/
│       └── room_list.html     # HTMX фрагмент списка комнат
├── routing.py            # WebSocket URL маршруты
├── urls.py               # HTTP URL маршруты
└── views.py              # Django views
```

---

## Данные в Redis

```
chat:queue                     # List — очередь ожидания
    ["specific.xxx!aaa", "specific.xxx!bbb"]

chat:rooms                     # Hash — активные комнаты
    {
        "uuid-комнаты": '{"caller": "...", "callee": "...", "created_at": 123}'
    }

chat:messages:{room_id}        # List — история чата (TTL 1 час)
    ['{"sender":"me","text":"привет","timestamp":123}', ...]
```

---

## Поток данных — полная схема

```
                    ┌─────────────────────────────────────────┐
                    │              DJANGO SERVER               │
                    │                                          │
Браузер 1           │  SignalingConsumer 1                     │  Браузер 2
(caller)            │                                          │  (callee)
    │               │                                          │      │
    │──WS connect──→│──join_queue()──→[Redis: chat:queue]      │      │
    │               │                                          │      │
    │               │           [Redis: chat:queue]←──join_queue()──│
    │               │                    │                     │      │
    │               │            match found!                  │      │
    │               │                    │                     │      │
    │←─{matched,    │──create_room()──→[Redis: chat:rooms]     │      │
    │   caller}     │                    │                     │      │
    │               │         channel_layer.send()─────────────→SignalingConsumer 2
    │               │                                          │      │
    │               │                                          │←─{matched,
    │               │                                          │   callee}
    │               │                                          │      │
    │               │                    ←──{ready}────────────│      │
    │←─{ready_to_connect}─────────────────                     │      │
    │               │                                          │      │
    │──{offer}─────→│─────────────────────────────────────────→│      │
    │               │                                          │──{offer}→
    │               │                    ←──{answer}───────────│      │
    │←─{answer}─────│─────────────────────                     │      │
    │               │                                          │      │
    │◄═══════════════════ P2P видео/аудио ════════════════════►│      │
    │               │                    (сервер не участвует) │      │
    │──{chat_msg}──→│─────────────────────────────────────────→│      │
    │               │                                          │──{chat_msg}→
```

---

## Ключевые баги которые были найдены и исправлены

### 1. Гонка состояний WebRTC
**Симптом:** видео не появляется, статус "соединяемся" висит вечно  
**Причина:** caller отправлял offer до того как callee создал RTCPeerConnection  
**Решение:** handshake через ready → ready_to_connect перед отправкой offer

### 2. role = null в closePeer()
**Симптом:** callee никогда не отправлял ready  
**Причина:** `closePeer()` обнулял переменную `role`, которая проверялась после `await setupPeerConnection()`  
**Решение:** сохранять role в локальную переменную `myRole` до вызова async функции

### 3. Неверный парсинг сообщений
**Симптом:** сигналинг не работал несмотря на правильный бэкенд  
**Причина:** бэкенд отправляет `{payload: {type: "offer"}}`, но фронт проверял `msg.type` (верхний уровень)  
**Решение:** разделить обработку — `msg.type` для системных событий, `msg.payload` для сигналинга

### 4. Дублирование метода signaling_message
**Симптом:** сигналинг не работал  
**Причина:** метод был объявлен дважды, Python брал последний  
**Решение:** один метод на класс

### 5. WebRTC mesh для модератора
**Симптом:** offer от модератора применялся к основному pc участника  
**Причина:** участник использовал один pc для всех входящих offer  
**Решение:** отдельный pcModerator для соединения с модератором