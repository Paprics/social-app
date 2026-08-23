
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