# SERVER MULTISITE INFRA DATA

Служебная записка для DevOps, разворачивающего второй сайт на существующем Hetzner production-сервере.

## Сервер

```text
OS: Ubuntu 24.04 LTS
IP: 188.245.169.52
RAM: ~3.7 GiB
Swap: /swapfile, 4 GiB
Disk: 38 GiB
Docker: enabled, autostart
```

## Общая схема

```text
Internet
  ↓
edge_caddy :80/:443
  ↓
Docker external network: proxy
  ├─ peekdrop-nginx:80
  └─ <site_slug>-nginx:80
```

Caddy — единая публичная точка входа и TLS для всех сайтов.

## Структура `/srv`

```text
/srv/
├── sites/
│   └── peekdrop/
├── infrastructure/
│   └── proxy/
├── data/
│   ├── peekdrop/
│   │   ├── postgres/
│   │   ├── media/
│   │   └── redis/
│   └── caddy/
│       ├── data/
│       └── config/
├── secrets/
│   └── peekdrop.env
└── backups/
    └── peekdrop/
```

Для второго сайта:

```text
/srv/sites/<site_slug>
/srv/data/<site_slug>/postgres
/srv/data/<site_slug>/media
/srv/data/<site_slug>/redis
/srv/secrets/<site_slug>.env
```

## Shared Caddy

```text
Repo: git@github.com:Paprics/server-infrastructure.git
Server path: /srv/infrastructure/proxy
Branch: main
Container: edge_caddy
Image: caddy:2.11.4-alpine
Caddyfile: /srv/infrastructure/proxy/conf/Caddyfile
Caddy data: /srv/data/caddy/data
Caddy config: /srv/data/caddy/config
```

Публичные порты:

```text
80/tcp
443/tcp
443/udp
```

Текущий PeekDrop route:

```caddyfile
peekdrop.xyz, www.peekdrop.xyz {
    reverse_proxy peekdrop-nginx:80 {
        header_up X-Real-IP {remote_host}
    }
}
```

Для второго сайта нужен аналогичный block:

```caddyfile
<domain>, www.<domain> {
    reverse_proxy <site_slug>-nginx:80 {
        header_up X-Real-IP {remote_host}
    }
}
```

## Shared Docker network

Уже существует:

```text
proxy
```

В Compose второго сайта:

```yaml
networks:
  proxy:
    external: true
    name: proxy
```

К `proxy` подключается только внутренний Nginx второго сайта.

## Сеть второго сайта

Отдельная private bridge network:

```yaml
networks:
  internal:
    driver: bridge
```

Подключение:

```text
db      -> internal
redis   -> internal
web     -> internal
nginx   -> internal + proxy
```

## Naming второго сайта

Все имена уникальные:

```text
<site_slug>_db
<site_slug>_redis
<site_slug>_web
<site_slug>_nginx
<site_slug>_static_volume
```

Alias Nginx в `proxy`:

```text
<site_slug>-nginx
```

Пример:

```yaml
nginx:
  networks:
    internal:
    proxy:
      aliases:
        - <site_slug>-nginx
```

## Persistent mounts

```yaml
db:
  - /srv/data/<site_slug>/postgres:/var/lib/postgresql/data

redis:
  - /srv/data/<site_slug>/redis:/data

web:
  - /srv/data/<site_slug>/media:/app/media

nginx:
  - /srv/data/<site_slug>/media:/app/media:ro
```

Production env:

```yaml
env_file:
  - /srv/secrets/<site_slug>.env
```

Static volume:

```text
<site_slug>_static_volume
```

Restart policy:

```yaml
restart: unless-stopped
```

## Порты

Уже занято:

```text
80/tcp              edge_caddy
443/tcp             edge_caddy
443/udp             edge_caddy
127.0.0.1:5432      PeekDrop PostgreSQL
```

Второй сайт:

```text
nginx: expose 80
web: expose 8000
redis: internal 6379
```

Если нужен host-доступ к PostgreSQL:

```text
127.0.0.1:5433 -> <site_slug>_db:5432
```

Следующие сайты — 5434, 5435 и т.д.

## Внутренний Nginx второго сайта

```text
listen 80
/static/ -> static volume
/media/  -> /srv/data/<site_slug>/media
/        -> web:8000
```

TLS внутри site Nginx не используется.

При proxy к Django нужно сохранить `X-Forwarded-Proto` от Caddy.

## PeekDrop reference

```text
Repo: git@github.com:Paprics/peekdrop.xyz.git
Server path: /srv/sites/peekdrop
Branch: prod

Data:
  /srv/data/peekdrop/postgres
  /srv/data/peekdrop/media
  /srv/data/peekdrop/redis

Secret:
  /srv/secrets/peekdrop.env

Containers:
  peekdrop_db
  peekdrop_redis
  peekdrop_web
  peekdrop_nginx

Proxy alias:
  peekdrop-nginx

Static volume:
  peekdrop_static_volume
```

## Текущее Docker-состояние

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

Host services:

```text
nginx.service: inactive
certbot.timer: inactive
```

## Что требуется от второго сайта

Перед развёртыванием должны быть известны:

```text
site_slug
domain
Git repository
production branch
Dockerfile
docker-compose.yml
nginx.conf
production env
нужен ли host port PostgreSQL
дополнительные services: celery / beat / websocket / worker / scheduler
```

Точки интеграции с существующим сервером:

```text
/srv/sites/<site_slug>
/srv/data/<site_slug>/*
/srv/secrets/<site_slug>.env
external network: proxy
proxy alias: <site_slug>-nginx
Caddyfile route
```

## Контроль после запуска

```text
site containers: Up
DB/Redis: healthy
<site_slug>-nginx присутствует в network proxy
новый домен работает по HTTPS
PeekDrop продолжает возвращать HTTP 200
после reboot оба сайта поднимаются автоматически
```
