# Инфраструктура сервера и регламент развёртывания второго сайта

**Назначение:** технический handoff для DevOps/разработчика, который будет готовить Docker-конфигурацию и разворачивать второй сайт на существующем Hetzner-сервере.  
**Актуально на:** 19.08.2026.

---

## 1. Что уже сделано

Сервер переразложен под multi-site архитектуру. Первый production-сайт **PeekDrop** уже перенесён в новую структуру и работает через общий edge reverse proxy **Caddy**.

Ключевой принцип: каждый сайт независим, но публичные `80/443` и TLS централизованы в одном Caddy.

```text
Internet
   │
   │ 80 / 443 TCP
   │ 443 UDP (HTTP/3)
   ▼
edge_caddy
   │
   │ shared external Docker network: proxy
   ├───────────────────────────────┐
   ▼                               ▼
peekdrop_nginx                 site2_nginx
   │                               │
   │ private site network          │ private site network
   ▼                               ▼
peekdrop_web                    site2_web
   │   │                           │   │
   DB Redis                        DB Redis
```

**Caddy — единственная публичная точка входа.**

---

## 2. Сервер

```text
Provider: Hetzner Cloud
OS: Ubuntu 24.04 LTS
Public IP: 188.245.169.52
CPU: 2 vCPU
RAM: ~3.7 GiB
Swap: 4 GiB (/swapfile)
Disk: 38 GiB
```

Финальный baseline после миграции и reboot:

```text
RAM used:       ~671 MiB
RAM available:  ~3.1 GiB
Swap used:      0 B
Disk used:      ~8.6 GiB
Disk free:      ~28 GiB
```

Docker включён в autostart. Все production-контейнеры используют `restart: unless-stopped`. Реальный reboot проверен: весь stack поднимается автоматически, HTTPS после reboot возвращает `200`.

---

## 3. Целевая файловая структура

```text
/srv/
├── sites/
│   └── peekdrop/                  # Git checkout сайта
├── infrastructure/
│   └── proxy/                     # отдельный Git checkout shared Caddy
├── data/
│   ├── peekdrop/
│   │   ├── postgres/
│   │   ├── media/
│   │   └── redis/
│   └── caddy/
│       ├── data/                  # TLS certificates/keys/runtime
│       └── config/
├── secrets/
│   └── peekdrop.env               # chmod 600, не Git
└── backups/
    └── peekdrop/
```

Для второго сайта продолжать **эту же схему**:

```text
/srv/sites/<site_slug>
/srv/data/<site_slug>/postgres
/srv/data/<site_slug>/media
/srv/data/<site_slug>/redis
/srv/secrets/<site_slug>.env
```

Не хранить production-data внутри Git checkout.

---

## 4. Текущий PeekDrop как эталон

Git checkout:

```text
/srv/sites/peekdrop
```

Remote:

```text
git@github.com:Paprics/peekdrop.xyz.git
```

Production branch:

```text
prod
```

Текущий production HEAD после инфраструктурных изменений:

```text
0be97b2 Remove duplicate security headers from nginx
```

Secrets:

```text
/srv/secrets/peekdrop.env
```

Persistent data:

```text
/srv/data/peekdrop/postgres
/srv/data/peekdrop/media
/srv/data/peekdrop/redis
```

Static named volume:

```text
peekdrop_static_volume
```

Контейнеры:

```text
peekdrop_nginx
peekdrop_web
peekdrop_db
peekdrop_redis
```

---

## 5. Shared Caddy

Caddy **не принадлежит PeekDrop**. Это отдельная инфраструктура сервера.

Server checkout:

```text
/srv/infrastructure/proxy
```

GitHub repository:

```text
git@github.com:Paprics/server-infrastructure.git
```

Branch:

```text
main
```

Container:

```text
edge_caddy
```

Image:

```text
caddy:2.11.4-alpine
```

Публичные порты:

```text
80/tcp
443/tcp
443/udp
```

Persistent Caddy state:

```text
/srv/data/caddy/data
/srv/data/caddy/config
```

Caddyfile:

```text
/srv/infrastructure/proxy/conf/Caddyfile
```

Текущий PeekDrop route:

```caddyfile
peekdrop.xyz, www.peekdrop.xyz {
    reverse_proxy peekdrop-nginx:80 {
        header_up X-Real-IP {remote_host}
    }
}
```

Caddy отвечает за:

```text
public 80/443
TLS
Let's Encrypt
automatic certificate renewal
HTTP -> HTTPS
routing domain -> site nginx
HTTP/2 + HTTP/3
```

**Новый сайт не должен поднимать собственный Certbot или публичный TLS-Nginx.**

---

## 6. Shared Docker network

На host уже существует external Docker network:

```text
proxy
```

Проверка:

```bash
docker network inspect proxy
```

В Compose каждого сайта:

```yaml
networks:
  proxy:
    external: true
    name: proxy
```

К `proxy` подключается **только HTTP edge сервиса сайта**, обычно внутренний Nginx.

Не подключать к `proxy`:

```text
PostgreSQL
Redis
Django web
Celery workers
Celery Beat
прочие внутренние сервисы
```

Они остаются в приватной сети конкретного сайта.

---

## 7. Private network каждого сайта

У PeekDrop logical network в Compose:

```yaml
networks:
  internal:
    driver: bridge
```

Фактическое Docker-имя сейчас:

```text
peekdrop_internal
```

Для второго сайта сделать свою `internal` network.

Не добавлять `internal: true` автоматически: Django/Celery могут требовать outbound-доступ к API, email, Telegram, payment providers и т. п.

---

## 8. Порты: обязательный контракт

Сейчас:

```text
edge_caddy:
  0.0.0.0:80
  0.0.0.0:443
  UDP :443

peekdrop_db:
  127.0.0.1:5432 -> 5432

peekdrop_nginx:
  80/tcp only

peekdrop_web:
  8000/tcp only

peekdrop_redis:
  6379/tcp only
```

Для второго сайта:

- **не публиковать `80/443`;**
- web — только `expose: 8000`, если нужен внутреннему Nginx;
- Redis не публиковать на host;
- PostgreSQL либо не публиковать вовсе, либо только `127.0.0.1:<unique-port>`.

PeekDrop уже занимает:

```text
127.0.0.1:5432
```

Если второму сайту нужен SSH tunnel/DBeaver:

```yaml
ports:
  - "127.0.0.1:5433:5432"
```

Никогда не использовать для production DB:

```text
0.0.0.0:5432
```

---

## 9. Docker Compose шаблон второго сайта

Это архитектурный skeleton; project-specific Celery/Channels/worker-сервисы добавляются отдельно.

```yaml
services:
  db:
    image: postgres:16-alpine
    container_name: <site_slug>_db
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${DB_NAME:?DB_NAME is required}
      POSTGRES_USER: ${DB_USER:?DB_USER is required}
      POSTGRES_PASSWORD: ${DB_PASSWORD:?DB_PASSWORD is required}
    volumes:
      - /srv/data/<site_slug>/postgres:/var/lib/postgresql/data
    networks:
      - internal
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 5s
      timeout: 5s
      retries: 10

  redis:
    image: redis:7-alpine
    container_name: <site_slug>_redis
    restart: unless-stopped
    volumes:
      - /srv/data/<site_slug>/redis:/data
    networks:
      - internal
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 10

  web:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: <site_slug>_web
    restart: unless-stopped
    env_file:
      - /srv/secrets/<site_slug>.env
    volumes:
      - /srv/data/<site_slug>/media:/app/media
      - <site_slug>_static_volume:/app/staticfiles
    expose:
      - "8000"
    networks:
      - internal
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  nginx:
    image: nginx:1.27-alpine
    container_name: <site_slug>_nginx
    restart: unless-stopped
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - /srv/data/<site_slug>/media:/app/media:ro
      - <site_slug>_static_volume:/app/staticfiles:ro
    expose:
      - "80"
    networks:
      internal:
      proxy:
        aliases:
          - <site_slug>-nginx
    depends_on:
      - web

networks:
  internal:
    driver: bridge

  proxy:
    external: true
    name: proxy

volumes:
  <site_slug>_static_volume:
    name: <site_slug>_static_volume
```

Все `container_name`, volume names, network aliases и host ports должны быть уникальными на сервере.

---

## 10. Внутренний Nginx сайта

Site Nginx отвечает только за:

```text
/static/
/media/
reverse proxy -> web:8000
proxy timeouts/limits
```

В нём **не должно быть**:

```text
listen 443 ssl
ssl_certificate
ssl_certificate_key
Certbot challenge
Let's Encrypt logic
HTTP -> HTTPS redirect server
```

Пример важной proxy-части:

```nginx
map $http_x_forwarded_proto $upstream_forwarded_proto {
    default $http_x_forwarded_proto;
    ""      $scheme;
}

upstream django {
    server web:8000;
}

server {
    listen 80;

    location / {
        proxy_pass http://django;

        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $http_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $upstream_forwarded_proto;
        proxy_set_header X-Real-IP $http_x_real_ip;

        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

### Почему `X-Forwarded-Proto` важен

Пользователь приходит:

```text
HTTPS -> Caddy
```

Но Caddy обращается к внутреннему Nginx по HTTP.

Если внутренний Nginx бездумно выставит:

```nginx
X-Forwarded-Proto $scheme
```

он передаст Django `http`, хотя исходный request был HTTPS.

Для Django behind proxy обычно требуется согласованная настройка:

```python
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```

если проект использует secure redirects/cookies logic.

---

## 11. Security headers

В PeekDrop application security headers оставлены на уровне Django, чтобы не дублировать их в Nginx.

Не выставлять одновременно одинаковые:

```text
X-Frame-Options
X-Content-Type-Options
Referrer-Policy
```

в Django и Nginx.

Рекомендуемая модель ответственности:

```text
Django -> application security headers
Nginx  -> static/media/reverse proxy
Caddy  -> public TLS/domain routing
```

---

## 12. Добавление домена второго сайта в Caddy

DNS нового домена сначала должен указывать на:

```text
188.245.169.52
```

После того как site nginx поднят и подключён к `proxy`, добавить в infrastructure repo:

```text
conf/Caddyfile
```

пример:

```caddyfile
example.com, www.example.com {
    reverse_proxy <site_slug>-nginx:80 {
        header_up X-Real-IP {remote_host}
    }
}
```

Изменение Caddyfile относится к repository:

```text
server-infrastructure
```

а не к repository конкретного сайта.

На сервере:

```bash
cd /srv/infrastructure/proxy
git pull --ff-only origin main
```

Проверка:

```bash
docker exec edge_caddy \
  caddy validate \
  --config /etc/caddy/Caddyfile \
  --adapter caddyfile
```

Применение без остановки Caddy:

```bash
docker exec edge_caddy \
  caddy reload \
  --config /etc/caddy/Caddyfile \
  --adapter caddyfile
```

После этого Caddy сам получит/обновит сертификат для нового домена.

---

## 13. Production flow нового сайта

### A. Git

Production server — не место разработки.

```text
local development
  -> commit
  -> GitHub production branch
  -> server git pull
```

Не редактировать tracked production-файлы вручную на сервере.

### B. Директории

```bash
mkdir -p /srv/data/<site_slug>/postgres
mkdir -p /srv/data/<site_slug>/media
mkdir -p /srv/data/<site_slug>/redis
```

Secrets:

```text
/srv/secrets/<site_slug>.env
```

```bash
chmod 700 /srv/secrets
chmod 600 /srv/secrets/<site_slug>.env
```

### C. Clone

```bash
git clone \
  --branch prod \
  --single-branch \
  git@github.com:OWNER/REPOSITORY.git \
  /srv/sites/<site_slug>
```

### D. Validate

```bash
cd /srv/sites/<site_slug>

docker compose \
  --env-file /srv/secrets/<site_slug>.env \
  config -q
```

### E. Start site stack

```bash
docker compose \
  --env-file /srv/secrets/<site_slug>.env \
  up -d --build
```

Ожидание:

```text
db      healthy
redis   healthy
web     Up
nginx   Up
```

### F. Проверить внутренний Nginx

```bash
docker exec <site_slug>_nginx nginx -t
```

До подключения Caddy убедиться, что chain работает:

```text
site nginx -> web -> Django
```

### G. Добавить Caddy route

Добавить domain block в `server-infrastructure`, pull на сервере, validate/reload Caddy.

### H. External check

```bash
curl -I http://example.com
curl -I https://example.com
```

Ожидание:

```text
HTTP -> HTTPS redirect
HTTPS -> 200/301/302 application response
```

Проверить logs:

```bash
docker logs --tail 100 edge_caddy
```

И отдельно убедиться, что PeekDrop после добавления второго сайта продолжает возвращать `200`.

---

## 14. Если второй сайт мигрируется с существующей БД

Не копировать live PostgreSQL directory во время записи.

Безопасный flow:

```text
1. Подготовить новую инфраструктуру заранее.
2. Остановить web traffic старого deployment.
3. Сделать final pg_dump.
4. Проверить dump.
5. Остановить PostgreSQL.
6. Перенести/восстановить DB.
7. Перенести media.
8. Поднять новый site stack.
9. Проверить DB/Web/internal nginx.
10. Только затем подключить domain через Caddy.
```

Physical PostgreSQL directory переносить только при остановленном PostgreSQL и совместимой версии.

---

## 15. Static vs Media

**Media** — пользовательские данные:

```text
/srv/data/<site_slug>/media
```

Они persistent.

**Static** — результат `collectstatic`.

Для PeekDrop используется named volume:

```text
peekdrop_static_volume
```

Static можно восстановить из кода; PostgreSQL и user media — нельзя считать пересоздаваемыми.

---

## 16. Entrypoint/Gunicorn PeekDrop: полезный reference

PeekDrop entrypoint поддерживает явно переданную Docker command:

```bash
if [ "$#" -gt 0 ]; then
    exec "$@"
fi
```

Это позволяет:

```bash
docker compose run --rm web python manage.py ...
```

без безусловного запуска Gunicorn.

Gunicorn PeekDrop:

```text
workers: env GUNICORN_WORKERS, default 3
timeout: env GUNICORN_TIMEOUT, default 60
max_requests: default 1000
max_requests_jitter: default 100
```

`max-requests` и jitter сейчас являются production guard и не должны удаляться без отдельного решения.

---

## 17. Особенность file bind mount

PeekDrop Nginx config монтируется как отдельный файл:

```yaml
- ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
```

После `git pull` Git может заменить host-файл новым inode, а уже запущенный container продолжит видеть старый file mount.

Поэтому при изменении `nginx.conf` надёжный вариант:

```bash
docker compose \
  --env-file /srv/secrets/peekdrop.env \
  up -d --no-deps --force-recreate nginx
```

Для Caddy монтируется directory `./conf -> /etc/caddy`, после чего используется `caddy reload`.

---

## 18. Обычный production deploy

```bash
cd /srv/sites/<site_slug>

git pull --ff-only origin prod

docker compose \
  --env-file /srv/secrets/<site_slug>.env \
  up -d --build
```

`--ff-only` нужен, чтобы production server не создавал неожиданные merge commits. Если история разошлась, deploy должен остановиться и потребовать разбирательства.

---

## 19. Что категорически не делать

1. Не публиковать `80/443` второго сайта — они принадлежат Caddy.
2. Не поднимать второй Certbot.
3. Не хранить PostgreSQL/media/Redis data внутри Git checkout.
4. Не хранить production `.env` в Git.
5. Не повторять `container_name` уже существующих контейнеров.
6. Не повторять host DB port `127.0.0.1:5432`.
7. Не подключать DB/Redis к shared `proxy`.
8. Не включать host `nginx.service` — публичный proxy теперь Caddy.
9. Не включать старый `certbot.timer` — TLS теперь управляет Caddy.
10. Не делать слепой `docker system prune -a` на production host.

---

## 20. Текущее Docker-состояние после cleanup

Networks:

```text
bridge
host
none
peekdrop_internal
proxy
```

Volumes:

```text
peekdrop_static_volume
```

Images:

```text
caddy:2.11.4-alpine
nginx:1.27-alpine
peekdrop-web:latest
postgres:16-alpine
redis:7-alpine
```

Build cache после cleanup:

```text
0 B
```

Host services:

```text
docker: active
host nginx: inactive
certbot.timer: inactive
```

---

## 21. Текущий memory baseline

После reboot:

```text
System RAM:
  total       ~3.7 GiB
  used        ~671 MiB
  available   ~3.1 GiB

Swap:
  total       4 GiB
  used        0 B
```

Containers:

```text
peekdrop_web      ~174 MiB
peekdrop_db        ~59 MiB
edge_caddy         ~51 MiB
peekdrop_redis     ~13 MiB
peekdrop_nginx     ~10 MiB
```

Это reference baseline для оценки влияния второго сайта.

---

## 22. Checklist второго сайта

Перед завершением deployment проверить:

```text
[ ] выбран уникальный site_slug
[ ] /srv/sites/<site_slug> используется только для кода
[ ] PostgreSQL -> /srv/data/<site_slug>/postgres
[ ] Media -> /srv/data/<site_slug>/media
[ ] Redis -> /srv/data/<site_slug>/redis
[ ] Secrets -> /srv/secrets/<site_slug>.env
[ ] Compose config validation проходит
[ ] container names уникальны
[ ] static volume уникален
[ ] internal network сайта создана
[ ] external proxy network используется существующая
[ ] только site nginx подключён к proxy
[ ] site nginx имеет уникальный alias `<site_slug>-nginx`
[ ] site nginx не публикует 80/443
[ ] web не публикует 8000 наружу
[ ] Redis не публикует 6379 наружу
[ ] DB либо без host port, либо только 127.0.0.1:<unique-port>
[ ] внутренний nginx -> web работает
[ ] X-Forwarded-Proto сохраняется корректно
[ ] DNS нового домена указывает на 188.245.169.52
[ ] Caddyfile обновлён через infrastructure repo
[ ] Caddy config validation проходит
[ ] Caddy reload проходит
[ ] HTTP редиректит на HTTPS
[ ] HTTPS работает
[ ] certificate получен Caddy
[ ] restart: unless-stopped включён
[ ] PeekDrop после deployment всё ещё отвечает 200
```

---

## 23. Известные отдельные задачи

За рамками этой multi-site миграции сознательно оставлены:

1. Off-server backup strategy.
2. Root-cause старого роста памяти Gunicorn workers.

Они не блокируют развёртывание второго сайта, но являются отдельными operational/application задачами.

---

# Краткий handoff для DevOps

Если читать только этот блок:

```text
1. Новый сайт -> /srv/sites/<site_slug>.
2. Data -> /srv/data/<site_slug>/{postgres,media,redis}.
3. Secrets -> /srv/secrets/<site_slug>.env.
4. У сайта собственная private internal Docker network.
5. Shared external network уже существует и называется `proxy`.
6. Только внутренний nginx сайта подключить к `proxy`.
7. Дать ему уникальный alias `<site_slug>-nginx`.
8. Никаких host 80/443 внутри сайта.
9. Никакого Certbot/TLS внутри сайта.
10. Caddy в /srv/infrastructure/proxy маршрутизирует domain -> `<site_slug>-nginx:80`.
11. DB не открывать в интернет; если нужен tunnel — уникальный 127.0.0.1 port.
12. Сначала поднять и проверить внутренний stack, затем подключать Caddy.
13. Все container names/volumes/ports должны быть уникальными.
14. Production код идёт local -> GitHub -> server git pull, без ручных tracked-правок на host.
15. После deployment обязательно проверить и новый домен, и PeekDrop.
```

Если новый Compose следует этому контракту, второй Django-сайт встраивается в существующую инфраструктуру без изменения принципов уже работающего PeekDrop.
