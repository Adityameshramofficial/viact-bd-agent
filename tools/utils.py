import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
TMP = ROOT / ".tmp"

load_dotenv(ROOT / ".env")


def get_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(f"Missing required env var: {key}")
    return value


def tmp_path(filename: str) -> Path:
    TMP.mkdir(exist_ok=True)
    return TMP / filename
