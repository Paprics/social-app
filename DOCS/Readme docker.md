# Docker — запуск проекта

## Структура

```
server/
├── infrastructure/
│   ├── nginx/          ← один nginx на весь сервер (запускается первым)
│   └── coturn/         ← один TURN сервер на весь сервер
└── social-network/
    ├── docker/
    │   ├── Dockerfile.dev
    │   ├── Dockerfile.prod
    │   ├── compose.dev.yml
    │   └── compose.prod.yml
    ├── src/
    ├── .env.dev
    ├── .env.prod
    └── requirements.txt
```

---

## Dev

```bash
# Из корня проекта
docker compose -f docker/compose.dev.yml --env-file .env.dev up --build

# Следить за логами одного сервиса
docker compose -f docker/compose.dev.yml logs -f web

# Выполнить команду внутри web контейнера
docker compose -f docker/compose.dev.yml exec web python manage.py createsuperuser
```

Django доступен на http://localhost:8000

---

## Prod

### 1. Первый раз на сервере — запустить инфраструктуру

```bash
cd infrastructure/nginx
docker compose up -d
# Это создаёт сеть frontend_network

cd ../coturn
docker compose up -d
```

### 2. Запустить проект

```bash
cd social-network
# Заполнить .env.prod реальными значениями
docker compose -f docker/compose.prod.yml --env-file .env.prod up -d --build
```

### 3. SSL сертификат (первый раз)

```bash
cd infrastructure/nginx
# Временно открыть HTTP в nginx conf для challenge, затем:
docker compose run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d example.com -d www.example.com \
  --email your@email.com --agree-tos
```

---

## Добавить второй сайт на сервер

1. Задеплоить второй проект аналогично (у него свой compose.prod.yml с `frontend_network: external: true`)
2. Добавить файл `infrastructure/nginx/conf.d/site-b.conf`
3. `docker compose -f infrastructure/nginx/compose.yml exec nginx nginx -s reload`

Nginx перезагрузится без даунтайма и начнёт проксировать второй сайт.

---

## Переменные которые ОБЯЗАТЕЛЬНО менять в .env.prod

- `SECRET_KEY` — длинный случайный ключ
- `POSTGRES_PASSWORD` — сложный пароль
- `ALLOWED_HOSTS` — реальный домен
- `TURN_URL` — IP сервера
- `TURN_USER` / `TURN_PASSWORD` — должны совпадать с `infrastructure/coturn/turnserver.conf`