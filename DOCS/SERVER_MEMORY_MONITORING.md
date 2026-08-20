# Контроль памяти production-сервера и Gunicorn

Служебная шпаргалка для периодического ручного контроля памяти сервера и контейнера Django/Gunicorn.

Production:

```text
Server: 188.245.169.52
Web container: peekdrop_web
Gunicorn workers: 3
RAM server: ~3.7 GiB
Swap: 4 GiB
```

## Подключение к серверу

С локального компьютера:

```bash
ssh -i ~/.ssh/peekdrop_ed25519 root@188.245.169.52
```

---

# Основной замер

Этот блок можно целиком вставлять в Bash на сервере.

```bash
echo
echo "============================================================"
echo "              PEEKDROP MEMORY CHECK"
echo "============================================================"

echo
echo "===== DATE / UPTIME ====="
date
uptime

echo
echo "===== SYSTEM RAM ====="
free -h

echo
echo "===== SWAP ====="
swapon --show

echo
echo "===== CONTAINER MEMORY ====="
docker stats --no-stream \
  --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.CPUPerc}}\t{{.PIDs}}"

echo
echo "===== PEEKDROP WEB / GUNICORN ====="
docker top peekdrop_web -eo pid,ppid,rss,%mem,etime,args

echo
echo "===== PEEKDROP WEB TOTAL ====="
docker stats --no-stream peekdrop_web \
  --format "Memory: {{.MemUsage}} | {{.MemPerc}} | CPU: {{.CPUPerc}} | PIDs: {{.PIDs}}"

echo
echo "===== CONTAINERS ====="
docker ps \
  --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo
echo "===== HTTPS ====="
curl -sS \
  -o /dev/null \
  -w 'HTTP %{http_code} | time=%{time_total}s\n' \
  https://peekdrop.xyz/en/

echo
echo "============================================================"
echo "                    CHECK FINISHED"
echo "============================================================"
echo
```

---

# Как читать Gunicorn

Команда:

```bash
docker top peekdrop_web -eo pid,ppid,rss,%mem,etime,args
```

выводит примерно:

```text
PID    PPID   RSS     %MEM   ELAPSED   COMMAND
1329   1208   28276   0.7    ...       gunicorn ...
1658   1329   60448   1.5    ...       gunicorn ...
1659   1329   59788   1.5    ...       gunicorn ...
1660   1329   58740   1.5    ...       gunicorn ...
```

`RSS` указан в KiB.

Пример:

```text
28276 KiB ≈ 28 MB
60448 KiB ≈ 60 MB
59788 KiB ≈ 60 MB
58740 KiB ≈ 59 MB
```

Первый процесс — Gunicorn master.

Остальные три — workers.

---

# Нормальный baseline PeekDrop

После последнего reboot нормальные значения были примерно:

```text
peekdrop_web total: ~174 MiB

Gunicorn master:
~28 MB

worker #1:
~60 MB

worker #2:
~60 MB

worker #3:
~59 MB
```

Остальные контейнеры примерно:

```text
peekdrop_db:      ~59 MiB
edge_caddy:       ~51 MiB
peekdrop_redis:   ~13 MiB
peekdrop_nginx:   ~10 MiB
```

Системная память:

```text
RAM total:      ~3.7 GiB
RAM used:       ~670 MiB
RAM available:  ~3.1 GiB
Swap used:      0
```

Это использовать как ориентир, а не как жёсткий лимит.

---

# На что смотреть

Главное — не единичное значение, а рост одного и того же worker во времени.

Например:

```text
12:00  worker PID 1658   60 MB
15:00  worker PID 1658   95 MB
20:00  worker PID 1658  180 MB
следующий день           350 MB
```

Такой устойчивый рост требует внимания.

Особенно подозрительно:

```text
worker > 200–300 MB
```

и тем более:

```text
worker > 500 MB
```

Ранее проблемные production workers доходили примерно до:

```text
650–730 MB на один worker
```

---

# Gunicorn recycle

Production сейчас запускается с:

```text
--workers 3
--max-requests 1000
--max-requests-jitter 100
```

Поэтому worker должен периодически завершаться и заменяться новым.

Это можно заметить по изменению `PID`.

Например:

```text
старый worker:
PID 1658 — 160 MB

через некоторое время:

PID 4832 — 60 MB
```

Это нормальный recycle.

Если PID изменился и память снова вернулась примерно к baseline — механизм работает.

---

# Быстрый замер только Gunicorn

Когда весь сервер смотреть не нужно:

```bash
echo "===== WEB TOTAL ====="

docker stats --no-stream peekdrop_web \
  --format "Memory: {{.MemUsage}} | CPU: {{.CPUPerc}} | PIDs: {{.PIDs}}"

echo
echo "===== GUNICORN ====="

docker top peekdrop_web -eo pid,ppid,rss,%mem,etime,args
```

---

# Наблюдение в реальном времени

Чтобы смотреть память контейнеров непрерывно:

```bash
docker stats
```

Выход:

```text
Ctrl+C
```

---

# Автоматический снимок каждую минуту

Для временного наблюдения:

```bash
while true; do
    clear

    echo "===== $(date) ====="
    echo

    free -h

    echo
    docker stats --no-stream peekdrop_web \
      --format "WEB: {{.MemUsage}} | CPU: {{.CPUPerc}} | PIDs: {{.PIDs}}"

    echo
    docker top peekdrop_web -eo pid,ppid,rss,%mem,etime,args

    sleep 60
done
```

Остановить:

```text
Ctrl+C
```

---

# Записать замер в лог

Если нужно сохранить состояние для последующего сравнения:

```bash
LOG="/root/peekdrop-memory-$(date +%Y%m%d-%H%M%S).log"

{
    echo "===== DATE ====="
    date

    echo
    echo "===== UPTIME ====="
    uptime

    echo
    echo "===== RAM ====="
    free -h

    echo
    echo "===== SWAP ====="
    swapon --show

    echo
    echo "===== CONTAINERS ====="
    docker stats --no-stream \
      --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.CPUPerc}}\t{{.PIDs}}"

    echo
    echo "===== GUNICORN ====="
    docker top peekdrop_web -eo pid,ppid,rss,%mem,etime,args

} | tee "$LOG"

echo
echo "Saved: $LOG"
```

---

# Короткая диагностика

Нормальная картина:

```text
web container около baseline
workers десятки MB
swap = 0
available RAM большой
workers периодически меняют PID
HTTPS = 200
```

Требует расследования:

```text
один и тот же worker постоянно увеличивает RSS
workers снова достигают сотен MB
весь peekdrop_web постоянно растёт
после recycle память не уменьшается
начинает постоянно использоваться swap
available RAM постоянно уменьшается
```

Важно:

```text
рост RSS сам по себе ещё не доказывает memory leak
```

Для поиска непосредственной причины используются отдельные инструменты профилирования (`tracemalloc`, `memray` и т. п.).

Этот документ предназначен именно для визуального эксплуатационного контроля.