from pathlib import Path
import shutil

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"


def reset_migrations() -> None:
    migration_dirs = list(SRC_DIR.rglob("migrations"))

    if not migration_dirs:
        print("Migration directories not found.")
        return

    deleted_files = 0
    deleted_cache_dirs = 0

    for migrations_dir in migration_dirs:
        print(f"\n[{migrations_dir.relative_to(PROJECT_ROOT)}]")

        for path in migrations_dir.iterdir():
            # __init__.py обязательно оставляем
            if path.name == "__init__.py":
                continue

            if path.is_file() and path.suffix == ".py":
                path.unlink()
                deleted_files += 1
                print(f"  deleted: {path.name}")

            elif path.is_dir() and path.name == "__pycache__":
                shutil.rmtree(path)
                deleted_cache_dirs += 1
                print("  deleted: __pycache__/")

    print("\nDone.")
    print(f"Migration files deleted: {deleted_files}")
    print(f"__pycache__ directories deleted: {deleted_cache_dirs}")


if __name__ == "__main__":
    reset_migrations()
