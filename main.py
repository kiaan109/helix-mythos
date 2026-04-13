"""
Helix Mythos — Entry Point
Run: python main.py
"""

import logging
import sys
import os
import io
from pathlib import Path

# Fix Windows console encoding (only when stdout exists — not pythonw)
if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── Working directory ─────────────────────────────────────────────────────────
os.chdir(Path(__file__).parent)
sys.path.insert(0, str(Path(__file__).parent))

# ── Logging — always write to file; only add console if stdout exists ─────────
_handlers = [logging.FileHandler("helix.log", encoding="utf-8")]
if sys.stdout is not None:
    try:
        _handlers.append(logging.StreamHandler(sys.stdout))
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=_handlers,
)
logger = logging.getLogger("HelixMain")

# ── ASCII Banner ──────────────────────────────────────────────────────────────
BANNER = """
  =====================================================================
   HELIX MYTHOS v2.0  --  Autonomous Intelligence System
   All-Seeing. All-Knowing. Always Evolving.
   Sources: 150+  |  Categories: 17  |  Update: 60 seconds
  =====================================================================
"""


def main():
    print(BANNER)
    logger.info("Helix Mythos starting up...")

    # Dependency check
    missing = _check_dependencies()
    if missing:
        logger.warning(f"Missing packages: {missing}")
        logger.warning("Run: pip install -r requirements.txt")

    from core.engine import HelixEngine
    engine = HelixEngine()

    # Start terminal dashboard
    try:
        from dashboard.dashboard import run_dashboard
        run_dashboard(engine)
    except Exception as e:
        logger.warning(f"Dashboard unavailable: {e}")

    engine.start()


def _check_dependencies() -> list[str]:
    required = [
        "telegram", "feedparser", "requests", "bs4",
        "sklearn", "numpy", "pandas", "psutil",
    ]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    return missing


if __name__ == "__main__":
    main()
