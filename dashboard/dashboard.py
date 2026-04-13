"""
Helix Mythos — Terminal Dashboard
Live ASCII dashboard showing system status
"""

import os
import sys
import time
import threading
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def render(engine):
    try:
        import psutil
        cpu    = psutil.cpu_percent(interval=0.5)
        mem    = psutil.virtual_memory()
        disk   = psutil.disk_usage("/")
        hw     = f"CPU {cpu:.1f}%  RAM {mem.percent:.1f}%  Disk {disk.percent:.1f}%"
    except Exception:
        hw = "Hardware stats unavailable"

    stats  = engine.memory.stats()
    events = engine.memory.get_recent_events(limit=5)
    facts  = engine.memory.get_facts(limit=5)
    agents = engine.agent_mgr.agents

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    clear()
    print("=" * 70)
    print(f"  {config.HELIX_NAME} v{config.HELIX_VERSION}  |  {now}")
    print(f"  {config.HELIX_MOTTO}")
    print("=" * 70)
    print(f"  Uptime: {engine.uptime()}  |  Cycles: {engine.cycle_count}  |  {hw}")
    print("-" * 70)

    print(f"\n  MEMORY: Events={stats['events']}  Facts={stats['facts']}  "
          f"Knowledge={stats['knowledge']}  Decisions={stats['decisions']}")

    print("\n  AGENTS:")
    for name, agent in agents.items():
        st = "IDLE" if agent.status == "idle" else agent.status.upper()
        print(f"    [{st:7s}] {agent.name}  (tasks: {agent.task_count})")

    print("\n  LATEST EVENTS:")
    for ev in events[:5]:
        print(f"    [{ev['category']:10s}] {ev['title'][:55]}")

    print("\n  TOP FACTS:")
    for f in facts[:5]:
        conf = int(f["confidence"] * 100)
        print(f"    [{conf:3d}%] {f['fact'][:60]}")

    print("\n" + "=" * 70)
    print("  Press Ctrl+C to stop Helix Mythos")
    print("=" * 70)


def run_dashboard(engine):
    """Run dashboard in a background thread."""
    def _loop():
        while True:
            try:
                render(engine)
            except Exception:
                pass
            time.sleep(5)
    t = threading.Thread(target=_loop, daemon=True, name="Dashboard")
    t.start()
