"""Small Shop Review Agent — 一键启动入口."""
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(_PROJECT_ROOT / ".env")

APP_PATH = _PROJECT_ROOT / "apps" / "streamlit_app" / "app.py"

if __name__ == "__main__":
    import os

    # Quick dependency check for live mode
    llm_mode = os.environ.get("LLM_MODE", "demo")
    if llm_mode == "live":
        try:
            import openai  # noqa: F401
        except ImportError:
            print("WARNING: openai package not installed. Live mode may fail.")
            print("  Install: pip install openai")

    print("Small Shop Review Agent - starting...")
    print(f"   LLM_MODE = {llm_mode}")
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(APP_PATH), "--server.port", "8501"],
        cwd=str(_PROJECT_ROOT),
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
