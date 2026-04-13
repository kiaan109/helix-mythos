"""
Helix Mythos — Cloud Entry Point (Render.com / Linux)
No camera, no Windows deps. Flask health endpoint keeps Render alive.
"""

import logging
import sys
import os
import threading
from pathlib import Path
from flask import Flask

# ── Working directory ─────────────────────────────────────────────────────────
os.chdir(Path(__file__).parent)
sys.path.insert(0, str(Path(__file__).parent))

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler("helix.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("HelixCloud")

# ── Flask health server (keeps Render free tier alive) ────────────────────────
flask_app = Flask(__name__)

@flask_app.route("/")
def health():
    return "Helix Mythos — Online", 200

@flask_app.route("/health")
def health2():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


def main():
    logger.info("=" * 60)
    logger.info("  HELIX MYTHOS v2.0 — CLOUD DEPLOYMENT")
    logger.info("  Autonomous Intelligence | 185 sources | 17 categories")
    logger.info("=" * 60)

    # Start Flask health server in background
    flask_thread = threading.Thread(target=run_flask, daemon=True, name="FlaskHealth")
    flask_thread.start()
    logger.info("Flask health server started.")

    # Start Helix cloud engine
    from core.engine_cloud import HelixEngineCloud
    engine = HelixEngineCloud()
    engine.start()


if __name__ == "__main__":
    main()
