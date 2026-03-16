from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None


_ENV_PATH = Path(__file__).resolve().parent / ".env"
if load_dotenv is not None and _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash").strip()

_BASE_DIR = Path(__file__).resolve().parent

# Defaults live next to this code (works regardless of current working directory).
# Use the anonymized version of the main project's keystrokes.
INPUT_FILE = str(_BASE_DIR.parent / "clean_text.txt")

# Optional: set your default prompt in this file.
PROMPT_FILE = str(_BASE_DIR / "prompt.txt")

