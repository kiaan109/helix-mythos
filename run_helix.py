"""
Helix Mythos — Persistent Runner
Keeps Helix alive: auto-restarts on crash, logs all errors to file.
Run this file instead of main.py when using pythonw / Task Scheduler.
"""

import sys
import os
import time
import subprocess
import traceback
from pathlib import Path
from datetime import datetime

BASE_DIR  = Path(__file__).parent
LOG_FILE  = BASE_DIR / "helix_runner.log"
PYTHON    = r"C:\Python312\python.exe"
MAIN      = str(BASE_DIR / "main.py")

def log(msg):
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass

def run():
    log("=" * 60)
    log("Helix Mythos Runner starting")
    restart_count = 0

    while True:
        restart_count += 1
        log(f"Starting Helix (attempt #{restart_count})...")
        try:
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"]       = "1"

            proc = subprocess.Popen(
                [PYTHON, "-u", MAIN],
                cwd=str(BASE_DIR),
                env=env,
                stdout=open(BASE_DIR / "helix_stdout.log", "a", encoding="utf-8"),
                stderr=open(BASE_DIR / "helix_stderr.log", "a", encoding="utf-8"),
            )
            log(f"Helix running — PID {proc.pid}")
            proc.wait()
            log(f"Helix exited with code {proc.returncode}")

        except Exception as e:
            log(f"Runner error: {e}")
            log(traceback.format_exc())

        log(f"Restarting in 5 seconds...")
        time.sleep(5)

if __name__ == "__main__":
    run()
