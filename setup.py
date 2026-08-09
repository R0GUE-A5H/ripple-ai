from agents.coordinator import main
from rich.console import Console
from core.config import *
import traceback
import subprocess
import sys

console = Console()
OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

REPAIR_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

EXAMPLES_DIR.mkdir(
    parents=True,
    exist_ok=True,
)
if __name__ == "__main__":
    try:
        subprocess.run(
            [sys.executable, str(ROOT / "setup_mock_dashboard.py")],
            check=True,
        )
        main()
    except Exception:
        traceback.print_exc()
