"""Small Shop Review Agent -- one-click start entry point.

Usage:
    python run_app.py          # launch Streamlit UI (default)
    python run_app.py --api    # launch FastAPI server
"""
import subprocess
import sys
from pathlib import Path as FsPath

from dotenv import load_dotenv

_PROJECT_ROOT = FsPath(__file__).resolve().parent
load_dotenv(_PROJECT_ROOT / ".env")

APP_PATH = _PROJECT_ROOT / "apps" / "streamlit_app" / "app.py"
API_PATH = _PROJECT_ROOT / "apps" / "api" / "main.py"

if __name__ == "__main__":
    import os
    mode = sys.argv[1] if len(sys.argv) > 1 else "ui"

    if mode == "--api":
        print("Small Shop Review Agent - API mode on http://localhost:8000")
        import uvicorn
        uvicorn.run(
            "apps.api.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
        )
    else:
        llm_mode = os.environ.get("LLM_MODE", "demo")
        if llm_mode == "live":
            try:
                import openai  # noqa: F401
            except ImportError:
                print("WARNING: openai package not installed. Live mode may fail.")
                print("  Install: pip install openai")

        print("Small Shop Review Agent - starting Streamlit...")
        print(f"   LLM_MODE = {llm_mode}")
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", str(APP_PATH), "--server.port", "8501"],
            cwd=str(_PROJECT_ROOT),
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
