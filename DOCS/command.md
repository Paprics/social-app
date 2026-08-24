
Подключиться к Server SSH
''' python
ssh -i ~/.ssh/peekdrop_ed25519 root@188.245.169.52
'''

Тунель SSH


Поднять docker на dev локально
Пересобрать
docker compose --env-file .env.dev -f docker/compose.dev.yml up -d --build
Просто поднять без сборки
docker compose --env-file .env.dev -f docker/compose.dev.yml up -d

Просмотреть логи
docker logs -f sn-web-dev (online stream)
docker logs --tail 100 sn-web-dev

Миграции
docker exec -it sn-web-dev bash
python manage.py makemigrations
python manage.py migrate
- или
docker exec -it sn-web-dev python manage.py makemigrations
docker exec -it sn-web-dev python manage.py migrate