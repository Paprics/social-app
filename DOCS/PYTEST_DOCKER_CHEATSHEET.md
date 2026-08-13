# Pytest + Docker — шпаргалка

Короткая памятка по запуску тестов Django-проекта через Docker.

---

## 1. Конфигурация pytest

Файл:

```text
src/pytest.ini
```

Содержимое:

```ini
[pytest]
DJANGO_SETTINGS_MODULE = _config.settings.test
python_files = test_*.py
addopts = -ra
```

### Почему `pytest.ini` находится в `src/`

На хосте код проекта находится в:

```text
social-network/src/
```

В Docker эта директория монтируется как:

```text
/app
```

Поэтому:

```text
src/pytest.ini
```

внутри контейнера становится:

```text
/app/pytest.ini
```

Pytest запускается из `/app` и автоматически находит этот конфигурационный файл.

---

## 2. Django settings для тестов

Для pytest используется отдельный файл:

```text
src/_config/settings/test.py
```

То есть тесты работают с:

```text
_config.settings.test
```

а не с обычными:

```text
_config.settings.dev
```

Это позволяет отключить ненужные при тестировании dev-инструменты, например Django Debug Toolbar, и отдельно настроить тестовое окружение.

При запуске pytest в начале вывода должно быть:

```text
settings: _config.settings.test
```

---

# 3. Запуск через Docker

Все команды удобно выполнять из корня проекта:

```bash
cd /e/pythonProject/social-network
```

Базовая Docker-команда:

```bash
docker compose --env-file .env.dev -f docker/compose.dev.yml exec web
```

После неё указывается обычная команда `pytest`.

---

# 4. Запустить все тесты проекта

```bash
docker compose --env-file .env.dev -f docker/compose.dev.yml exec web \
    pytest -v
```

---

# 5. Запустить тесты одного Django app

Например все тесты `posts`:

```bash
docker compose --env-file .env.dev -f docker/compose.dev.yml exec web \
    pytest posts/tests -v
```

Другой app запускается аналогично:

```bash
pytest users/tests -v
```

```bash
pytest messenger/tests -v
```

---

# 6. Запустить один файл с тестами

Например:

```bash
docker compose --env-file .env.dev -f docker/compose.dev.yml exec web \
    pytest posts/tests/test_access.py -v
```

Views постов:

```bash
docker compose --env-file .env.dev -f docker/compose.dev.yml exec web \
    pytest posts/tests/test_post_views.py -v
```

Views комментариев:

```bash
docker compose --env-file .env.dev -f docker/compose.dev.yml exec web \
    pytest posts/tests/test_comment_views.py -v
```

---

# 7. Запустить один класс тестов

Формат:

```text
pytest путь_к_файлу.py::ИмяКласса
```

Пример:

```bash
docker compose --env-file .env.dev -f docker/compose.dev.yml exec web \
    pytest posts/tests/test_post_views.py::TestCreatePostView -v
```

---

# 8. Запустить один конкретный тест

Формат:

```text
pytest файл.py::Класс::метод_теста
```

Пример:

```bash
docker compose --env-file .env.dev -f docker/compose.dev.yml exec web \
    pytest posts/tests/test_post_views.py::TestCreatePostView::test_user_can_create_post_when_allowed -v
```

---

# 9. Остановиться на первой ошибке

Флаг:

```text
-x
```

Пример:

```bash
docker compose --env-file .env.dev -f docker/compose.dev.yml exec web \
    pytest posts/tests -v -x
```

Полезно при отладке, чтобы не получать сразу десятки одинаковых ошибок.

---

# 10. Запустить только тесты, упавшие в прошлый раз

Флаг:

```text
--lf
```

Пример:

```bash
docker compose --env-file .env.dev -f docker/compose.dev.yml exec web \
    pytest --lf -v
```

`lf` = `last failed`.

---

# 11. Сначала запустить прошлые упавшие тесты

Флаг:

```text
--ff
```

Пример:

```bash
docker compose --env-file .env.dev -f docker/compose.dev.yml exec web \
    pytest --ff -v
```

`ff` = `failed first`.

Сначала pytest проверит прошлые падения, затем продолжит остальные тесты.

---

# 12. Показывать print() и stdout

Флаг:

```text
-s
```

Пример:

```bash
docker compose --env-file .env.dev -f docker/compose.dev.yml exec web \
    pytest posts/tests -v -s
```

Полезно при временной отладке через `print()`.

---

# 13. Короткий traceback

```bash
docker compose --env-file .env.dev -f docker/compose.dev.yml exec web \
    pytest posts/tests -v --tb=short
```

Удобнее обычного огромного traceback.

---

# 14. Комбинация для поиска первой ошибки

Обычно при отладке удобно:

```bash
docker compose --env-file .env.dev -f docker/compose.dev.yml exec web \
    pytest posts/tests -v -x --tb=short
```

То есть:

```text
-v          подробный список тестов
-x          остановиться на первой ошибке
--tb=short  короткий traceback
```

---

# 15. Проверить установленную версию pytest

```bash
docker compose --env-file .env.dev -f docker/compose.dev.yml exec web \
    pytest --version
```

---

# 16. Если pytest использует неправильные settings

Нормальный вывод:

```text
settings: _config.settings.test
```

Если отображается:

```text
settings: _config.settings.dev
```

значит конфигурация pytest не была найдена или применена.

Проверить наличие `pytest.ini` внутри контейнера:

```bash
docker compose --env-file .env.dev -f docker/compose.dev.yml exec web \
    ls -l /app/pytest.ini
```

При необходимости settings можно временно передать явно:

```bash
docker compose --env-file .env.dev -f docker/compose.dev.yml exec web \
    pytest --ds=_config.settings.test posts/tests -v
```

Но при правильно настроенном `src/pytest.ini` постоянно писать `--ds` не требуется.

---

# Быстрая памятка

Если уже находишься внутри контейнера или пишешь только часть после `exec web`:

```bash
# Все тесты проекта
pytest -v

# Все тесты posts
pytest posts/tests -v

# Один файл
pytest posts/tests/test_access.py -v

# Один класс
pytest posts/tests/test_post_views.py::TestCreatePostView -v

# Один конкретный тест
pytest posts/tests/test_post_views.py::TestCreatePostView::test_user_can_create_post_when_allowed -v

# Остановиться на первой ошибке
pytest -x

# Только прошлые упавшие
pytest --lf -v

# Сначала прошлые упавшие
pytest --ff -v

# Показывать print()
pytest -s

# Короткий traceback
pytest --tb=short

# Удобный режим отладки
pytest posts/tests -v -x --tb=short
```

Полный Docker-префикс:

```bash
docker compose --env-file .env.dev -f docker/compose.dev.yml exec web
```

То есть обычная схема:

```text
docker compose ... exec web + pytest + путь к тестам + флаги
```

Например:

```bash
docker compose --env-file .env.dev -f docker/compose.dev.yml exec web \
    pytest posts/tests -v -x
```