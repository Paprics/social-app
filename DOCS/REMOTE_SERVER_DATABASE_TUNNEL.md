# Remote Server Database Tunnel

Документация по локальному запуску Django с подключением к PostgreSQL на удалённом production-сервере через SSH-туннель.

Используется для случаев, когда код, шаблоны, management commands и вспомогательные файлы находятся локально, но работать нужно с удалённой базой данных.

---

## Быстрый запуск

### 1. Поднять SSH-туннель

Запускать **локально на Windows**, в отдельном терминале Git Bash:

```bash
ssh -N -i ~/.ssh/peekdrop_ed25519 \
-L 5433:127.0.0.1:5433 \
root@188.245.169.52
```

После успешного подключения терминал ничего не выводит и остаётся занят. Это нормальное поведение: процесс SSH держит туннель открытым.

Схема проброса:

```text
Windows 127.0.0.1:5433
        │
        │ SSH
        ▼
Server 127.0.0.1:5433
        │
        │ Docker port mapping
        ▼
flingon-postgres:5432
```

Остановить туннель:

```text
Ctrl+C
```

---

### 2. Проверить локальный порт туннеля

Git Bash:

```bash
netstat -ano | grep 5433
```

PowerShell:

```powershell
Test-NetConnection 127.0.0.1 -Port 5433
```

При рабочем туннеле:

```text
TcpTestSucceeded : True
```

Дополнительная проверка через Python:

```bash
python -c "import socket; s=socket.create_connection(('127.0.0.1',5433),5); print('TUNNEL OK'); s.close()"
```

Ожидаемый результат:

```text
TUNNEL OK
```

Эта проверка подтверждает доступность порта, но ещё не проверяет логин и пароль PostgreSQL.

---

### 3. Активировать виртуальное окружение

Из корня проекта:

```bash
source .venv/Scripts/activate
```

Проверка используемого Python:

```bash
which python
```

Ожидаемый путь:

```text
/e/pythonProject/social-network/.venv/Scripts/python
```

---

### 4. Проверить настройки remote_server

```bash
DJANGO_SETTINGS_MODULE=_config.settings.remote_server \
python src/manage.py shell -c \
"from django.conf import settings; d=settings.DATABASES['default']; print(d['NAME'], d['USER'], d['HOST'], d['PORT'])"
```

Для production-базы Flingon ожидается примерно:

```text
flingon flingon 127.0.0.1 5433
```

Пароль намеренно не выводится.

---

### 5. Проверить реальное подключение к PostgreSQL

```bash
DJANGO_SETTINGS_MODULE=_config.settings.remote_server \
python src/manage.py shell -c "
from django.db import connection
with connection.cursor() as c:
    c.execute('SELECT current_database(), current_user')
    print(c.fetchone())
"
```

Ожидаемый результат:

```text
('flingon', 'flingon')
```

Если этот запрос выполняется, Django действительно подключён к удалённой PostgreSQL через SSH-туннель.

---

### 6. Запустить локальный Django с удалённой БД

```bash
DJANGO_SETTINGS_MODULE=_config.settings.remote_server \
python src/manage.py runserver
```

Django работает локально:

```text
http://127.0.0.1:8000/
```

При этом ORM использует удалённую production-базу данных.

---

## Варианты запуска

### Один запуск с remote_server

Переменная применяется только к конкретному процессу:

```bash
DJANGO_SETTINGS_MODULE=_config.settings.remote_server \
python src/manage.py runserver
```

Это предпочтительный вариант для эпизодической работы с удалённой БД.

### Установить settings для текущего Git Bash

```bash
export DJANGO_SETTINGS_MODULE=_config.settings.remote_server
```

После этого:

```bash
python src/manage.py runserver
```

или:

```bash
python src/manage.py shell
```

Вернуться к development settings:

```bash
export DJANGO_SETTINGS_MODULE=_config.settings.dev
```

Либо просто закрыть терминал.

### Запуск без активации virtualenv

```bash
DJANGO_SETTINGS_MODULE=_config.settings.remote_server \
./.venv/Scripts/python.exe src/manage.py runserver
```

Это полезно, если не хочется активировать `.venv` вручную.

---

## Конфигурация `remote_server.py`

Файл:

```text
src/_config/settings/remote_server.py
```

Назначение настройки:

- сохранить локальное development-поведение Django;
- использовать production-реквизиты PostgreSQL;
- заменить только адрес подключения к БД на локальную точку SSH-туннеля.

Пример:

```python
"""
Local development settings using the remote server database via SSH tunnel.
"""

from pathlib import Path

import environ

from .dev import *


PROJECT_DIR = Path(__file__).resolve().parents[3]

remote_env = environ.Env()
remote_env.read_env(PROJECT_DIR / ".env", overwrite=True)


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": remote_env("POSTGRES_DB"),
        "USER": remote_env("POSTGRES_USER"),
        "PASSWORD": remote_env("POSTGRES_PASSWORD"),
        "HOST": "127.0.0.1",
        "PORT": "5433",
    }
}
```

`from .dev import *` сохраняет development-настройки.

Production `.env` используется для получения настоящих реквизитов базы:

```text
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
```

При этом Django не подключается к PostgreSQL напрямую по публичному адресу сервера. Для него база находится здесь:

```text
127.0.0.1:5433
```

Этот адрес существует локально благодаря SSH-туннелю.

---

## Для чего используется такой режим

Основной сценарий — выполнять локальный код непосредственно против удалённой базы.

Например:

```bash
DJANGO_SETTINGS_MODULE=_config.settings.remote_server \
python src/manage.py some_management_command
```

Это позволяет:

- запускать локальные Django management commands;
- использовать локальные исходные данные;
- выполнять тяжёлые импорты с рабочего компьютера;
- работать через обычный Django ORM;
- не загружать большие исходные GEO-файлы на сервер;
- проверять текущий локальный код на реальных данных.

Примерный сценарий GEO-импорта:

```text
локальные GEO-файлы
        ↓
локальная management command
        ↓
Django ORM
        ↓
127.0.0.1:5433
        ↓
SSH tunnel
        ↓
production PostgreSQL
```

---

## Важные ограничения

`remote_server` подключается к **реальной production-базе**.

Поэтому любые ORM-операции являются реальными:

```python
Model.objects.create(...)
Model.objects.update(...)
object.delete()
```

Они изменяют production-данные.

В этом режиме не следует без явной необходимости запускать:

```bash
python src/manage.py migrate
python src/manage.py flush
```

Также нельзя запускать тестовый suite, если тестовая конфигурация по какой-либо причине может использовать эту базу.

Для тестов используется отдельный `test.py`.

---

## Диагностика

### `password authentication failed`

Пример:

```text
FATAL: password authentication failed for user "postgres"
```

Это означает, что сетевой маршрут до PostgreSQL уже работает, но Django использует неправильные credentials.

Проверить:

```bash
DJANGO_SETTINGS_MODULE=_config.settings.remote_server \
python src/manage.py shell -c \
"from django.conf import settings; d=settings.DATABASES['default']; print(d['NAME'], d['USER'], d['HOST'], d['PORT'])"
```

### `connection refused`

Если получено:

```text
connection refused
```

проверить:

1. запущен ли SSH-туннель;
2. слушается ли локальный `127.0.0.1:5433`;
3. существует ли на сервере Docker mapping `127.0.0.1:5433 -> postgres:5432`;
4. запущен ли контейнер PostgreSQL.

### Терминал с SSH выглядит зависшим

Для команды:

```bash
ssh -N ...
```

это нормальное поведение.

Ключ `-N` говорит SSH не запускать удалённую shell-сессию. Процесс используется только для port forwarding.

---

## Как работает весь flow

Django ничего не знает о физическом расположении production PostgreSQL.

Для `remote_server.py` база выглядит как обычный PostgreSQL на:

```text
127.0.0.1:5433
```

SSH-клиент открывает этот порт на локальной машине и передаёт все TCP-соединения через зашифрованное SSH-соединение на сервер.

На сервере запрос приходит на:

```text
127.0.0.1:5433
```

Этот порт опубликован Docker-контейнером PostgreSQL и перенаправляется внутрь контейнера на стандартный PostgreSQL-порт:

```text
5432
```

Итоговый flow:

```text
Local Django
     │
     │ psycopg / Django ORM
     ▼
127.0.0.1:5433
     │
     │ SSH encrypted tunnel
     ▼
Remote server
127.0.0.1:5433
     │
     │ Docker port forwarding
     ▼
flingon-postgres:5432
     │
     ▼
Production database
```

Таким образом, код выполняется локально, а SQL-запросы выполняются в production PostgreSQL.

SSH здесь выполняет роль защищённого транспортного канала. PostgreSQL не требуется открывать в интернет, а Django не требуется устанавливать или запускать внутри production-контейнера для выполнения локальных management commands.
