import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# --- AI Provider Configuration (NVIDIA NIM / Gemini) ---
NIM_API_KEY = os.getenv("NIM_API_KEY", os.getenv("NVIDIA_API_KEY", ""))
GEMINI_API_KEY_ENV = os.getenv("GEMINI_API_KEY", "")

if NIM_API_KEY:
    AI_API_KEY = NIM_API_KEY
    AI_BASE_URL = "https://integrate.api.nvidia.com/v1"
    AI_MODEL = os.getenv("NIM_MODEL", "meta/llama-3.2-11b-vision-instruct")
    AI_PROVIDER = "NVIDIA NIM"
elif GEMINI_API_KEY_ENV:
    AI_API_KEY = GEMINI_API_KEY_ENV
    AI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
    AI_MODEL = "gemini-2.5-flash"
    AI_PROVIDER = "Gemini"
else:
    AI_API_KEY = ""
    AI_BASE_URL = "https://integrate.api.nvidia.com/v1"
    AI_MODEL = os.getenv("NIM_MODEL", "meta/llama-3.2-11b-vision-instruct")
    AI_PROVIDER = "NVIDIA NIM"

# Aliases for backwards compatibility
GEMINI_API_KEY = AI_API_KEY
GEMINI_BASE_URL = AI_BASE_URL
GEMINI_MODEL = AI_MODEL

TARGET_APP_URL = os.getenv("TARGET_APP_URL", "http://localhost:3001")
CONFIDENCE_THRESHOLD = 0.80

SPECS_DIR = BASE_DIR / "specs"
TESTS_DIR = BASE_DIR / "tests"
ARTIFACTS_DIR = BASE_DIR / "artifacts"
RUNS_DIR = ARTIFACTS_DIR / "runs"
REPAIRS_DIR = ARTIFACTS_DIR / "repairs"

SPECS_DIR.mkdir(parents=True, exist_ok=True)
TESTS_DIR.mkdir(parents=True, exist_ok=True)
RUNS_DIR.mkdir(parents=True, exist_ok=True)
REPAIRS_DIR.mkdir(parents=True, exist_ok=True)
