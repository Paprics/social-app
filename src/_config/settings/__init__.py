from .env import env
from _config.celery import app as celery_app

MODE = env("MODE", default="dev").strip().lower()

print("=" * 60)
print(f" Django settings: {MODE.upper()}")
print("=" * 60)

if MODE == "dev":
    from .dev import *
elif MODE == "prod":
    from .prod import *
else:
    raise RuntimeError(f"Unknown MODE: {MODE}")

__all__ = ("celery_app",)
