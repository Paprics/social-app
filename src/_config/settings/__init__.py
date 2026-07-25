from .env import env

MODE = env("MODE", default="dev").strip().lower()

print("=" * 60)
print(f" Django settings: {MODE.upper()}")
print("=" * 60)

if MODE == "prod":
    from .prod import *
elif MODE == "dev_pg":
    from .dev_pg import *
elif MODE == "dev":
    from .dev import *
else:
    raise RuntimeError(f"Unknown MODE: {MODE}")
