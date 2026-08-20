# src/_config/settings/env.py

import os
from pathlib import Path

import environ

PROJECT_DIR = Path(__file__).resolve().parents[3]

env = environ.Env()

settings_module = os.getenv(
    "DJANGO_SETTINGS_MODULE",
    "_config.settings.dev",
)

env_file = ".env" if settings_module.endswith(".prod") else ".env.dev"

env.read_env(PROJECT_DIR / env_file)
