#!/usr/bin/env python3
"""
pytree.py — расширенный аналог `tree` для Python/Django проектов.

Использование:
    python pytree.py [путь] [--depth N] [--no-color] [--no-ast] [--ignore PATTERN]

Примеры:
    python pytree.py .
    python pytree.py /path/to/project --depth 4
    python pytree.py . --no-ast
    python pytree.py . --ignore migrations --ignore tests
"""

import ast
import argparse
import os
import sys
import time
from pathlib import Path

# ─── ANSI-цвета ───────────────────────────────────────────────────────────────

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

C_DIR = "\033[1;34m"  # синий жирный  — папки
C_PY = "\033[1;32m"  # зелёный жирный — .py файлы
C_FILE = "\033[0;37m"  # серый          — прочие файлы
C_CLASS = "\033[1;33m"  # жёлтый жирный  — классы
C_METHOD = "\033[0;36m"  # голубой        — методы / функции
C_DECO = "\033[0;35m"  # фиолетовый     — декораторы
C_ARGS = "\033[2;37m"  # серый dim      — аргументы
C_COMMENT = "\033[2;32m"  # зелёный dim    — docstring-превью
C_IGNORE = "\033[2;31m"  # красный dim    — пропущенные узлы
C_LINES = "\033[2;36m"  # голубой dim    — счётчик строк файла
C_STAT_KEY = "\033[0;37m"  # серый          — метка в итогах
C_STAT_VAL = "\033[1;37m"  # белый жирный   — значение в итогах
C_TIME = "\033[0;33m"  # жёлтый         — elapsed

# ─── Константы игнорирования ──────────────────────────────────────────────────

DEFAULT_IGNORE_DIRS = {
    "__pycache__",
    ".git",
    ".hg",
    ".svn",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    ".venv",
    "venv",
    "env",
    ".env",
    "dist",
    "build",
    "*.egg-info",
    ".eggs",
    "htmlcov",
    ".coverage",
    "site-packages",
    "migrations",
    ".idea",
    ".vscode",
    "staticfiles",
    "static",
    "media",
    "photos",
    "dev_data",
}

DEFAULT_IGNORE_FILES = {
    ".DS_Store",
    "Thumbs.db",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.so",
    "*.dll",
    "*.egg",
    "*.whl",
    ".env",
    ".env.*",
    "db.sqlite3",
    "*.sqlite3",
    "poetry.lock",
    "Pipfile.lock",
    "package-lock.json",
}

# ─── Символы дерева ───────────────────────────────────────────────────────────

TEE = "├──"
LAST = "└──"
BLANK = "   "
PIPE_PREF = "│  "

# ─── AST-анализ ───────────────────────────────────────────────────────────────


def _deco_name(node) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_deco_name(node.value)}.{node.attr}"
    if isinstance(node, ast.Call):
        return f"{_deco_name(node.func)}(...)"
    return "?"


def _args_repr(args: ast.arguments) -> str:
    parts = []
    for a in args.posonlyargs:
        parts.append(a.arg)
    if args.posonlyargs:
        parts.append("/")
    for a in args.args:
        parts.append(a.arg)
    if args.vararg:
        parts.append(f"*{args.vararg.arg}")
    elif args.kwonlyargs:
        parts.append("*")
    for a in args.kwonlyargs:
        parts.append(a.arg)
    if args.kwarg:
        parts.append(f"**{args.kwarg.arg}")
    return ", ".join(parts)


def _docstring_preview(node) -> str | None:
    if (
        node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    ):
        doc = node.body[0].value.value.strip().splitlines()[0]
        return doc[:60] + ("…" if len(doc) > 60 else "")
    return None


def extract_symbols(filepath: Path, stats: dict) -> list[dict]:
    """Разбирает .py файл, возвращает символы и обновляет глобальную статистику."""
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return [{"kind": "error", "name": "<SyntaxError>"}]

    symbols = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            methods = []
            for item in ast.iter_child_nodes(node):
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    is_async = isinstance(item, ast.AsyncFunctionDef)
                    decos = [_deco_name(d) for d in item.decorator_list]
                    methods.append(
                        {
                            "kind": "method",
                            "name": item.name,
                            "args": _args_repr(item.args),
                            "decorators": decos,
                            "doc": _docstring_preview(item),
                            "async": is_async,
                        }
                    )
                    stats["functions"] += 1
                    if is_async:
                        stats["async_funcs"] += 1
            decos = [_deco_name(d) for d in node.decorator_list]
            symbols.append(
                {
                    "kind": "class",
                    "name": node.name,
                    "decorators": decos,
                    "doc": _docstring_preview(node),
                    "methods": methods,
                }
            )
            stats["classes"] += 1
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            is_async = isinstance(node, ast.AsyncFunctionDef)
            decos = [_deco_name(d) for d in node.decorator_list]
            symbols.append(
                {
                    "kind": "function",
                    "name": node.name,
                    "args": _args_repr(node.args),
                    "decorators": decos,
                    "doc": _docstring_preview(node),
                    "async": is_async,
                }
            )
            stats["functions"] += 1
            if is_async:
                stats["async_funcs"] += 1

    return symbols


# ─── Счётчик строк ────────────────────────────────────────────────────────────


def _count_lines(filepath: Path) -> int:
    """Быстрый подсчёт строк без загрузки всего файла в память."""
    try:
        count = 0
        with filepath.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 16), b""):
                count += chunk.count(b"\n")
        return count
    except OSError:
        return 0


# ─── Игнорирование ────────────────────────────────────────────────────────────


def _match_glob(name: str, patterns: set[str]) -> bool:
    from fnmatch import fnmatch

    return any(fnmatch(name, p) for p in patterns)


def should_ignore(path: Path, extra_ignore: set[str]) -> bool:
    name = path.name
    all_dir_ignore = DEFAULT_IGNORE_DIRS | extra_ignore
    all_file_ignore = DEFAULT_IGNORE_FILES | extra_ignore
    if path.is_dir():
        return _match_glob(name, all_dir_ignore)
    return _match_glob(name, all_file_ignore)


# ─── Рендер символов ──────────────────────────────────────────────────────────


def _colorize(text: str, color: str, use_color: bool) -> str:
    return f"{color}{text}{RESET}" if use_color else text


def render_symbols(symbols: list[dict], prefix: str, use_color: bool) -> list[str]:
    lines = []
    for i, sym in enumerate(symbols):
        is_last = i == len(symbols) - 1
        connector = LAST if is_last else TEE
        child_pref = prefix + (BLANK if is_last else PIPE_PREF)

        if sym["kind"] == "error":
            lines.append(f"{prefix}{connector} {_colorize(sym['name'], C_IGNORE, use_color)}")
            continue

        if sym["kind"] == "class":
            decos = ""
            if sym["decorators"]:
                decos = " " + _colorize(" ".join(f"@{d}" for d in sym["decorators"]), C_DECO, use_color)
            label = _colorize(f"class {sym['name']}", C_CLASS, use_color)
            doc_hint = ""
            if sym.get("doc"):
                doc_hint = "  " + _colorize(f'# {sym["doc"]}', C_COMMENT, use_color)
            lines.append(f"{prefix}{connector} {label}{decos}{doc_hint}")
            lines.extend(render_symbols(sym["methods"], child_pref, use_color))

        elif sym["kind"] in ("method", "function"):
            prefix_kw = "async def" if sym.get("async") else "def"
            label = _colorize(f"{prefix_kw} {sym['name']}", C_METHOD, use_color)
            args = _colorize(f"({sym['args']})", C_ARGS, use_color)
            decos = ""
            if sym["decorators"]:
                decos = "  " + _colorize(" ".join(f"@{d}" for d in sym["decorators"]), C_DECO, use_color)
            doc_hint = ""
            if sym.get("doc"):
                doc_hint = "  " + _colorize(f'# {sym["doc"]}', C_COMMENT, use_color)
            lines.append(f"{prefix}{connector} {label}{args}{decos}{doc_hint}")

    return lines


# ─── Рекурсивный обход дерева ─────────────────────────────────────────────────


def walk_tree(
    path: Path,
    prefix: str = "",
    depth: int = 0,
    max_depth: int | None = None,
    use_color: bool = True,
    show_ast: bool = True,
    show_lines: bool = True,
    extra_ignore: set[str] = frozenset(),
    stats: dict = None,
) -> list[str]:
    if stats is None:
        stats = {}

    lines = []

    try:
        entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except PermissionError:
        lines.append(f"{prefix}  {_colorize('[нет доступа]', C_IGNORE, use_color)}")
        return lines

    visible = [e for e in entries if not should_ignore(e, extra_ignore)]

    for i, entry in enumerate(visible):
        is_last = i == len(visible) - 1
        connector = LAST if is_last else TEE
        child_pref = prefix + (BLANK if is_last else PIPE_PREF)

        if entry.is_dir():
            stats["dirs"] += 1
            dir_label = _colorize(entry.name + "/", C_DIR, use_color)
            lines.append(f"{prefix}{connector} {dir_label}")
            if max_depth is None or depth + 1 < max_depth:
                lines.extend(
                    walk_tree(
                        entry,
                        child_pref,
                        depth + 1,
                        max_depth,
                        use_color,
                        show_ast,
                        show_lines,
                        extra_ignore,
                        stats,
                    )
                )
            else:
                lines.append(f"{child_pref}{LAST} {_colorize('...', C_IGNORE, use_color)}")

        elif entry.is_file():
            stats["files"] += 1
            if entry.suffix == ".py":
                stats["py_files"] += 1
                # подсчёт строк
                lc = _count_lines(entry) if show_lines else 0
                stats["total_lines"] += lc
                line_hint = ""
                if show_lines:
                    line_hint = "  " + _colorize(f"[{lc}]", C_LINES, use_color)
                file_label = _colorize(entry.name, C_PY, use_color)
                lines.append(f"{prefix}{connector} {file_label}{line_hint}")
                if show_ast and (max_depth is None or depth + 1 < max_depth):
                    symbols = extract_symbols(entry, stats)
                    if symbols:
                        lines.extend(render_symbols(symbols, child_pref, use_color))
            else:
                file_label = _colorize(entry.name, C_FILE, use_color)
                lines.append(f"{prefix}{connector} {file_label}")

    return lines


# ─── Итоговая статистика ──────────────────────────────────────────────────────


def _stat_row(label: str, value, use_color: bool, color=None) -> str:
    """Форматирует одну строку итогов: «  Files:        214»"""
    color = color or C_STAT_VAL
    lbl = _colorize(f"{label:<14}", C_STAT_KEY, use_color)
    val = _colorize(str(value).rjust(7), color, use_color)
    return f"  {lbl}{val}"


def render_summary(stats: dict, elapsed: float, use_color: bool) -> str:
    sep = _colorize("─" * 44, DIM, use_color)
    lines_str = f"{stats['total_lines']:,}".replace(",", " ")
    elapsed_str = f"{elapsed:.2f} sec"

    rows = [
        "",
        sep,
        _stat_row("Files:", stats["files"], use_color, C_PY),
        _stat_row("Directories:", stats["dirs"], use_color, C_DIR),
        "",
        _stat_row("Classes:", stats["classes"], use_color, C_CLASS),
        _stat_row("Functions:", stats["functions"], use_color, C_METHOD),
        _stat_row("Async:", stats["async_funcs"], use_color, C_DECO),
        "",
        _stat_row("Lines:", lines_str, use_color, C_LINES),
        "",
        _stat_row("Elapsed:", elapsed_str, use_color, C_TIME),
        sep,
    ]
    return "\n".join(rows)


# ─── Точка входа ──────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="pytree — расширенный tree с AST-скелетом Python-модулей",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Путь к директории проекта (по умолчанию: текущая)",
    )
    parser.add_argument(
        "--depth",
        "-d",
        type=int,
        default=None,
        metavar="N",
        help="Максимальная глубина обхода (по умолчанию: без ограничений)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Отключить цветной вывод",
    )
    parser.add_argument(
        "--no-ast",
        action="store_true",
        help="Не показывать классы/функции внутри .py файлов",
    )
    parser.add_argument(
        "--no-lines",
        action="store_true",
        help="Не показывать счётчик строк рядом с файлами",
    )
    parser.add_argument(
        "--ignore",
        "-i",
        action="append",
        metavar="PATTERN",
        default=[],
        help="Дополнительные паттерны для игнорирования (можно указать несколько раз)",
    )
    args = parser.parse_args()

    root = Path(args.path).resolve()
    if not root.exists():
        print(f"Ошибка: путь не существует: {root}", file=sys.stderr)
        sys.exit(1)
    if not root.is_dir():
        print(f"Ошибка: не директория: {root}", file=sys.stderr)
        sys.exit(1)

    use_color = not args.no_color and sys.stdout.isatty()
    extra_ignore = set(args.ignore)
    stats: dict = {
        "dirs": 0,
        "files": 0,
        "py_files": 0,
        "classes": 0,
        "functions": 0,
        "async_funcs": 0,
        "total_lines": 0,
    }

    root_label = _colorize(str(root), C_DIR, use_color)
    print(f"\n{root_label}")

    t0 = time.perf_counter()
    lines = walk_tree(
        root,
        prefix="",
        depth=0,
        max_depth=args.depth,
        use_color=use_color,
        show_ast=not args.no_ast,
        show_lines=not args.no_lines,
        extra_ignore=extra_ignore,
        stats=stats,
    )
    elapsed = time.perf_counter() - t0

    print("\n".join(lines))
    print(render_summary(stats, elapsed, use_color))


if __name__ == "__main__":
    main()
