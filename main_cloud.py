"""
Helix Mythos — Cloud Entry Point (Render.com / Linux)
Self-pinging keeps Render free tier ALWAYS awake. Never sleeps.
"""

import logging
import sys
import os
import threading
import time
import requests
from pathlib import Path
from flask import Flask

os.chdir(Path(__file__).parent)
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler("helix.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("HelixCloud")

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

def self_ping():
    """Ping own health endpoint every 4 minutes — keeps Render free tier awake forever."""
    time.sleep(30)  # Wait for Flask to start
    port = int(os.environ.get("PORT", 10000))
    url  = f"http://localhost:{port}/health"
    while True:
        try:
            requests.get(url, timeout=5)
            logger.debug("Self-ping OK")
        except Exception:
            pass
        time.sleep(240)  # Every 4 minutes

def main():
    logger.info("=" * 60)
    logger.info("  HELIX MYTHOS v2.0 — CLOUD DEPLOYMENT")
    logger.info("  Autonomous Intelligence | 185 sources | 17 categories")
    logger.info("=" * 60)

    flask_thread = threading.Thread(target=run_flask, daemon=True, name="FlaskHealth")
    flask_thread.start()

    ping_thread = threading.Thread(target=self_ping, daemon=True, name="SelfPing")
    ping_thread.start()
    logger.info("Flask + self-ping started. Render will never sleep.")

    from core.engine_cloud import HelixEngineCloud
    engine = HelixEngineCloud()
    engine.start()

if __name__ == "__main__":
    main()
