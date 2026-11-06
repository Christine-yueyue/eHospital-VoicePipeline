"""Load the application only after disabling access to developer dotenv files."""

import os
import secrets
import sys
from pathlib import Path

import dotenv


ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
TEST_TOKEN = "qa-" + secrets.token_urlsafe(32)

# app.py supplies an explicit path to load_dotenv. Replace that function before
# importing app so test startup never opens a developer .env file.
dotenv.load_dotenv = lambda *args, **kwargs: False
os.environ["APP_ACCESS_TOKEN"] = TEST_TOKEN
os.environ["OPENAI_API_KEY"] = "test-only-not-a-provider-key"
os.environ.pop("WHATSAPP_ACCESS_TOKEN", None)
os.environ.pop("WHATSAPP_APP_SECRET", None)
os.environ.pop("WHATSAPP_VERIFY_TOKEN", None)

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app as backend_app  # noqa: E402
import live as live_module  # noqa: E402
import voice_feedback  # noqa: E402
