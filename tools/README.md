# pytree — расширенный `tree` для Python / Django проектов

> Утилита командной строки, которая обходит директорию проекта как стандартная
> утилита `tree`, но дополнительно вскрывает каждый `.py`-файл и показывает
> его внутреннюю структуру: классы, методы, функции, декораторы и аргументы.
> Результат можно скинуть нейросети или коллеге — и они сразу поймут, что
> вообще происходит в проекте.

---

## Содержание

1. [Требования](#1-требования)
2. [Установка](#2-установка)
3. [Быстрый старт](#3-быстрый-старт)
4. [Аргументы командной строки](#4-аргументы-командной-строки)
5. [Что выводится из .py-файлов](#5-что-выводится-из-py-файлов)
6. [Цветовая схема](#6-цветовая-схема)
7. [Что игнорируется по умолчанию](#7-что-игнорируется-по-умолчанию)
8. [Практические сценарии](#8-практические-сценарии)
9. [Расширение и кастомизация](#9-расширение-и-кастомизация)
10. [Ограничения](#10-ограничения)

---

## 1. Требования

| Что нужно | Версия |
|-----------|--------|
| Python    | 3.10+  |
| Сторонние библиотеки | **не нужны** — только стандартная библиотека |
| ОС | Linux, macOS, Windows (WSL рекомендуется) |

Модуль использует только встроенные модули: `ast`, `argparse`, `os`, `sys`,
`pathlib`, `fnmatch`. Никаких `pip install`.

---

## 2. Установка

### Вариант A — просто скопировать файл в проект

Положите `pytree.py` в корень своего Django-проекта рядом с `manage.py`:

```
myproject/
├── manage.py
├── pytree.py   ← сюда
├── config/
└── myapp/
```

### Вариант B — сделать глобальной командой (Linux / macOS)

```bash
# Скопировать в директорию для пользовательских скриптов
cp pytree.py ~/.local/bin/pytree

# Сделать исполняемым
chmod +x ~/.local/bin/pytree

# Теперь можно запускать из любой директории
pytree /path/to/project
```

### Вариант C — alias в .bashrc / .zshrc

```bash
echo "alias pytree='python3 /полный/путь/до/pytree.py'" >> ~/.bashrc
source ~/.bashrc
```

---

## 3. Быстрый старт

```bash
# Перейти в корень проекта
cd /path/to/myproject

# Запустить — покажет всё дерево с AST-скелетом
python pytree.py

# Или указать путь явно
python pytree.py /path/to/myproject
```

Пример вывода:

```
/home/user/myproject
├── config/
│  ├── __init__.py
│  └── settings.py
├── myapp/
│  ├── __init__.py
│  ├── models.py
│  │  ├── class Airdrop  # Модель аирдропа.
│  │  │  ├── def __str__(self)
│  │  │  └── def activate(self)
│  │  └── class Category
│  └── views.py
│     ├── class AirdropListView  # Список аирдропов.
│     │  ├── def get(self, request)
│     │  └── def post(self, request)
│     ├── def airdrop_detail(request, pk)  @login_required
│     └── async def fetch_data(url, timeout)
├── manage.py
│  └── def main()
└── requirements.txt

────────────────────────────────────────────────
  3 директорий  6 файлов  (5 .py)
```

---

## 4. Аргументы командной строки

```
python pytree.py [path] [--depth N] [--no-color] [--no-ast] [--ignore PATTERN]
```

### `path` — путь к проекту (необязательный)

```bash
python pytree.py .                        # текущая директория
python pytree.py /home/user/myproject     # абсолютный путь
python pytree.py ../other_project         # относительный путь
```

По умолчанию — текущая директория (`.`).

---

### `--depth N` / `-d N` — глубина обхода

Ограничивает рекурсию. Полезно для больших проектов, когда нужно увидеть
только верхнеуровневую структуру.

```bash
python pytree.py . --depth 1    # только корень
python pytree.py . --depth 2    # корень + один уровень вложенности
python pytree.py . -d 3         # короткая форма
```

Пример при `--depth 1`:

```
/home/user/myproject
├── config/
│  └── ...
├── myapp/
│  └── ...
├── manage.py
└── requirements.txt
```

Директории, в которые не зашли из-за ограничения глубины, показывают `...`.

---

### `--no-color` — отключить цвет

По умолчанию цвета включаются автоматически, если вывод идёт в терминал
(TTY). При перенаправлении в файл или pipe цвета отключаются автоматически —
в этом случае флаг явно указывать не нужно.

```bash
# Сохранить в файл без ANSI-кодов
python pytree.py . --no-color > skeleton.txt

# Передать в less с цветом
python pytree.py . | less -R

# Принудительно убрать цвет в терминале
python pytree.py . --no-color
```

---

### `--no-ast` — только структура папок и файлов

Отключает анализ содержимого `.py`-файлов. Поведение становится идентичным
стандартному `tree`.

```bash
python pytree.py . --no-ast
```

Когда пригождается:
- нужна просто структура без деталей
- проект очень большой и AST-анализ замедляет вывод
- `.py`-файлы содержат специфичный синтаксис (Cython, нестандартные расширения)

---

### `--ignore PATTERN` / `-i PATTERN` — дополнительные игноры

Добавляет паттерн к списку игнорируемых файлов и директорий. Паттерны
поддерживают glob-синтаксис (`*`, `?`, `[abc]`). Можно указывать несколько
раз.

```bash
# Игнорировать одну директорию
python pytree.py . --ignore tests

# Игнорировать несколько директорий
python pytree.py . --ignore tests --ignore fixtures --ignore docs

# Glob-паттерн
python pytree.py . --ignore "test_*"

# Игнорировать определённые файлы
python pytree.py . --ignore "*.json" --ignore "*.yaml"

# Короткая форма
python pytree.py . -i tests -i fixtures
```

---

## 5. Что выводится из `.py`-файлов

Утилита разбирает каждый `.py`-файл через модуль `ast` (Abstract Syntax Tree)
стандартной библиотеки Python — без выполнения кода. Это быстро и безопасно.

### Классы

Выводится имя класса с ключевым словом `class`. Если у класса есть
декораторы — они показываются рядом через `@`. Если первая строка тела
класса — docstring, выводится его превью (до 60 символов) после `#`.

```
└── class AirdropListView  @some_decorator  # Список аирдропов.
```

### Методы

Выводятся все методы класса с полной сигнатурой аргументов. `async`-методы
помечаются явно.

```
├── def get(self, request)
├── def post(self, request)
└── async def fetch(self, url, *args, **kwargs)  @login_required
```

### Функции верхнего уровня

Функции, объявленные вне классов, показываются на уровне файла.

```
├── def parse_token(raw, strict)  @cache_result(...)
└── async def send_webhook(url, payload, timeout)
```

### Декораторы

Показываются для классов, методов и функций. Поддерживаются:

| Тип декоратора | Пример в коде | Вывод |
|---|---|---|
| Простой | `@login_required` | `@login_required` |
| Атрибутный | `@permission_classes.IsAuth` | `@permission_classes.IsAuth` |
| С аргументами | `@cache_page(60 * 15)` | `@cache_page(...)` |

### Аргументы функций

Выводятся все виды аргументов Python:

| Вид | Пример в коде | Вывод |
|---|---|---|
| Обычные | `def f(self, x, y)` | `(self, x, y)` |
| Позиционные-only | `def f(x, y, /)` | `(x, y, /)` |
| `*args` | `def f(*args)` | `(*args)` |
| `**kwargs` | `def f(**kwargs)` | `(**kwargs)` |
| keyword-only | `def f(*, key)` | `(*, key)` |
| Комбо | `def f(a, b, /, c, *, d, **kw)` | `(a, b, /, c, *, d, **kw)` |

Типы аннотаций (`x: int`, `-> str`) в вывод не включаются — чтобы не
засорять скелет.

### Синтаксическая ошибка в файле

Если в `.py`-файле синтаксическая ошибка — утилита не падает, а показывает
метку:

```
└── models_broken.py
   └── <SyntaxError>
```

---

## 6. Цветовая схема

| Элемент | Цвет | Значение |
|---------|------|----------|
| Директории | **Синий жирный** | Папки |
| `.py` файлы | **Зелёный жирный** | Python-модули |
| Прочие файлы | Серый | `requirements.txt`, `docker-compose.yml` и т.д. |
| `class Foo` | **Жёлтый жирный** | Определения классов |
| `def foo` / `async def foo` | Голубой | Методы и функции |
| `@decorator` | Фиолетовый | Декораторы |
| `(arg1, arg2)` | Серый dim | Аргументы функции |
| `# docstring preview` | Зелёный dim | Превью docstring |

Цвета включаются только в интерактивном терминале. При записи в файл или
передаче через pipe — автоматически отключаются.

---

## 7. Что игнорируется по умолчанию

Всё это жёстко зашито в код и не требует настройки.

### Директории

```
__pycache__       .git              .hg               .svn
.tox              .mypy_cache       .pytest_cache      .ruff_cache
node_modules      .venv             venv               env
.env              dist              build              *.egg-info
.eggs             htmlcov           .coverage          site-packages
migrations        .idea             .vscode            staticfiles
static            media
```

> `migrations` игнорируется намеренно — для скелета проекта они не нужны,
> но файлы `__init__.py` рядом с ними подхватываются через родительскую папку.
> Если нужно увидеть миграции — добавьте `--ignore something_else` и уберите
> `migrations` из `DEFAULT_IGNORE_DIRS` в исходнике.

### Файлы

```
.DS_Store         Thumbs.db         *.pyc             *.pyo
*.pyd             *.so              *.dll             *.egg
*.whl             .env              .env.*            db.sqlite3
*.sqlite3         poetry.lock       Pipfile.lock      package-lock.json
```

---

## 8. Практические сценарии

### Передать скелет проекта нейросети

```bash
# Генерируем чистый текст без ANSI-кодов
python pytree.py . > project_skeleton.txt

# Открываем файл и копируем содержимое в промпт
cat project_skeleton.txt
```

Или сразу в буфер обмена (macOS):

```bash
python pytree.py . | pbcopy
```

Linux (xclip):

```bash
python pytree.py . | xclip -selection clipboard
```

---

### Показать только структуру папок без кода

```bash
python pytree.py . --no-ast
```

Полезно, когда нужно объяснить архитектуру проекта без деталей реализации.

---

### Посмотреть только верхний уровень

```bash
python pytree.py . --depth 2
```

Даёт общее представление о структуре, не уходя в детали модулей.

---

### Анализировать конкретное приложение

```bash
python pytree.py ./myapp
python pytree.py ./myapp --depth 2
```

---

### Исключить тестовые файлы при анализе

```bash
python pytree.py . --ignore tests --ignore "test_*" --ignore conftest.py
```

---

### Сравнить два приложения

```bash
python pytree.py ./app1 --no-color > app1.txt
python pytree.py ./app2 --no-color > app2.txt
diff app1.txt app2.txt
```

---

### Использование в Makefile

```makefile
.PHONY: skeleton
skeleton:
	python pytree.py . --no-color > docs/skeleton.txt
	@echo "Скелет сохранён в docs/skeleton.txt"
```

```bash
make skeleton
```

---

### Добавить в pre-commit как документацию

```bash
# .git/hooks/pre-commit
python pytree.py . --no-color > docs/project_structure.md
git add docs/project_structure.md
```

---

## 9. Расширение и кастомизация

### Добавить свои директории в игнор по умолчанию

Открыть `pytree.py`, найти `DEFAULT_IGNORE_DIRS` и добавить нужное:

```python
DEFAULT_IGNORE_DIRS = {
    "__pycache__", ".git",
    # ...существующие...
    "tests",        # ← добавить
    "fixtures",     # ← добавить
    "docs",         # ← добавить
}
```

### Убрать миграции из игнора (если нужно видеть их)

```python
DEFAULT_IGNORE_DIRS = {
    "__pycache__", ".git",
    # "migrations",  ← закомментировать эту строку
    ...
}
```

### Показывать только классы, без функций

В функции `extract_symbols` убрать блок `elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))`.

### Добавить вывод атрибутов класса

В функции `extract_symbols` внутри блока `isinstance(node, ast.ClassDef)` добавить обход `ast.Assign` и `ast.AnnAssign`:

```python
for item in ast.iter_child_nodes(node):
    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
        attrs.append(item.target.id)  # name: Type = value
```

---

## 10. Ограничения

**AST-анализ — только верхний уровень.** Классы и функции, вложенные внутрь
других функций, не показываются. Это сделано намеренно — иначе вывод
становится слишком шумным.

**Нет анализа импортов.** Утилита не показывает, что откуда импортируется.
Это тоже намеренно — скелет, не граф зависимостей.

**Типы аннотаций не выводятся.** Аргументы показываются без `int`, `str`,
`Optional[...]` и т.д. — только имена, чтобы не раздувать вывод.

**Значения по умолчанию не выводятся.** `def f(x=10)` покажется как `def f(x)`.

**Файлы с нестандартным синтаксисом.** Если в проекте есть `.py`-файлы с
синтаксисом, который не поддерживается текущей версией Python (например,
старый Python 2 код) — они покажут `<SyntaxError>` вместо содержимого.

**Символические ссылки.** Симлинки на директории не разворачиваются, чтобы
избежать бесконечных циклов.

---

## Краткая шпаргалка

```bash
# Полный скелет проекта
python pytree.py .

# Только структура папок
python pytree.py . --no-ast

# Ограничить глубину
python pytree.py . -d 3

# Сохранить в файл
python pytree.py . --no-color > skeleton.txt

# Игнорировать директории
python pytree.py . -i tests -i docs

# Конкретное приложение
python pytree.py ./myapp

# Помощь
python pytree.py --help
```