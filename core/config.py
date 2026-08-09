from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv(override=True)

ROOT = Path(__file__).resolve().parent.parent

DATABASE_PATH = Path(
    os.getenv(
        "DATABASE_PATH",
        ROOT / "nyc-taxi" / "nyc_taxi_pipeline.db",
    )
)

LOCAL_REPO = Path(
    os.getenv(
        "LOCAL_REPO",
        ROOT,
    )
)

OUTPUT_DIR = ROOT / "output"

EXAMPLES_DIR = ROOT / "examples"

REPAIR_DIR = ROOT / "repairs"

GITHUB_OWNER = os.getenv("GITHUB_OWNER")

GITHUB_REPO = os.getenv("GITHUB_REPO")
DATAHUB_GMS_URL = (
    os.getenv("DATAHUB_GMS_URL", "http://localhost:8080").strip().replace("\r", "")
)

DATAHUB_GMS_TOKEN = os.getenv(
    "DATAHUB_GMS_TOKEN",
    "",
)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GMS_URL = (
    os.getenv(
        "GMS_URL",
        "http://localhost:8080/api/graphql",
    )
    .strip()
    .replace("\r", "")
)

MAX_REPAIR_ATTEMPTS = 3

MAX_LLM_RETRIES = 3

_demo_mode_env = os.getenv("DEMO_MODE")
_REQUIRED_LIVE_VARS = (GROQ_API_KEY, GITHUB_OWNER, GITHUB_REPO, GITHUB_TOKEN)

if _demo_mode_env is not None:
    DEMO_MODE = _demo_mode_env.strip().lower() == "true"
else:
    DEMO_MODE = not all(_REQUIRED_LIVE_VARS)
LOG_LEVEL = os.getenv(
    "LOG_LEVEL",
    "INFO",
)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
REPAIR_DIR.mkdir(parents=True, exist_ok=True)
