# src/_config/settings/env.py

from pathlib import Path

import environ

PROJECT_DIR = Path(__file__).resolve().parents[3]

env = environ.Env()
env.read_env(PROJECT_DIR / ".env.dev")
