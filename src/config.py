"""Configuration, loaded from environment variables (.env)."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = str(ROOT / "data" / "ecommerce.db")
EXAMPLES_FILE = ROOT / "examples" / "examples.json"

CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")


def llm_available() -> bool:
    """True only if a real OpenAI key is configured (not the placeholder)."""
    key = os.getenv("OPENAI_API_KEY", "")
    return bool(key) and key != "sk-your-key-here"
