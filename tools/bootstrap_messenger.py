from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "src" / "messenger"


# ----------------------------
# Что удалить
# ----------------------------

REMOVE_DIRS = [
    APP / "logic",
    APP / "managers",
    APP / "_DOCS  dev",
]

REMOVE_FILES = []


# ----------------------------
# Что создать
# ----------------------------

DIRS = [
    "consumers",
    "consumers/handlers",
    "docs",
    "docs/decisions",
    "forms",
    "models",
    "selectors",
    "services",
    "templates/messenger",
    "tests",
    "views",
]

FILES = [
    "__init__.py",
    "admin.py",
    "apps.py",
    "routing.py",
    "signals.py",
    "urls.py",
    # consumers
    "consumers/__init__.py",
    "consumers/chat_consumer.py",
    "consumers/presence_consumer.py",
    "consumers/handlers/__init__.py",
    "consumers/handlers/message.py",
    "consumers/handlers/presence_consumer.py",
    "consumers/handlers/read.py",
    "consumers/handlers/typing.py",
    # docs
    "docs/001_architecture.md",
    "docs/002_database.md",
    "docs/003_http_api.md",
    "docs/004_websocket_protocol.md",
    "docs/005_services.md",
    # ADR
    "docs/decisions/.gitkeep",
    # forms
    "forms/__init__.py",
    "forms/message.py",
    # models
    "models/__init__.py",
    "models/dialog.py",
    "models/message.py",
    "models/participant.py",
    "models/attachment.py",
    # selectors
    "selectors/__init__.py",
    "selectors/dialog.py",
    "selectors/message.py",
    "selectors/participant.py",
    # services
    "services/__init__.py",
    "services/dialog.py",
    "services/message.py",
    "services/presence_consumer.py",
    "services/read.py",
    "services/typing.py",
    "services/attachment.py",
    # tests
    "tests/__init__.py",
    "tests/test_dialog.py",
    "tests/test_message.py",
    "tests/test_services.py",
    # views
    "views/__init__.py",
    "views/dialog.py",
    "views/message.py",
]


def remove_path(path: Path):
    if not path.exists():
        return

    if path.is_dir():
        shutil.rmtree(path)
        print(f"[-] removed dir  {path.relative_to(ROOT)}")
    else:
        path.unlink()
        print(f"[-] removed file {path.relative_to(ROOT)}")


def ensure_dir(path: Path):
    if not path.exists():
        path.mkdir(parents=True)
        print(f"[+] created dir {path.relative_to(ROOT)}")


def ensure_file(path: Path):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        print(f"[+] created file {path.relative_to(ROOT)}")


def rename_chat_consumer():
    old = APP / "consumers" / "chat.py"
    new = APP / "consumers" / "chat_consumer.py"

    if old.exists() and not new.exists():
        old.rename(new)
        print("[*] chat.py -> chat_consumer.py")


def main():

    print("\n=== Messenger bootstrap ===\n")

    rename_chat_consumer()

    for path in REMOVE_DIRS:
        remove_path(path)

    for path in REMOVE_FILES:
        remove_path(path)

    for directory in DIRS:
        ensure_dir(APP / directory)

    for file in FILES:
        ensure_file(APP / file)

    print("\nDone.\n")


if __name__ == "__main__":
    main()
