"""
Helix Mythos — Cloud Engine (no vision, no Windows-specific deps)
Runs on Linux: Telegram bot + RSS intelligence + ML learning + agents
"""

import logging
import threading
import time
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import config

logger = logging.getLogger("HelixEngineCloud")


class HelixEngineCloud:
    def __init__(self):
        self._start_time = datetime.utcnow()
        self.cycle_count = 0
        self._running    = False

        from memory.memory_system             import MemorySystem
        from intelligence.global_intelligence import GlobalIntelligence
        from learning.learning_engine         import LearningEngine
        from sandbox.sandbox                  import Sandbox
        from tg.telegram_handler_cloud        import TelegramHandlerCloud

        logger.info("Initialising cloud subsystems...")

        self.memory   = MemorySystem()
        self.learning = LearningEngine(self.memory)
        self.intel    = GlobalIntelligence(self.memory)
        self.sandbox  = Sandbox(self.memory)
        self.telegram = TelegramHandlerCloud(self)

        logger.info("All cloud subsystems ready.")

    # ── Start ─────────────────────────────────────────────────────────────────
    def start(self):
        logger.info("=" * 60)
        logger.info(f"  {config.HELIX_NAME} v{config.HELIX_VERSION} — CLOUD")
        logger.info(f"  Sources: {len(config.NEWS_FEEDS)} | Mode: {config.SCAN_MODE.upper()}")
        logger.info("=" * 60)

        self._running = True

        self.intel.start()
        self.learning.start()
        self.telegram.start()

        time.sleep(5)

        t = threading.Thread(
            target=self._autonomous_loop, daemon=True, name="AutonomousLoop"
        )
        t.start()

        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        logger.info("Shutting down Helix Cloud...")
        self._running = False
        self.intel.stop()
        self.learning.stop()
        self.telegram.send_sync(
            f"🔴 *{config.HELIX_NAME}* offline.\n"
            f"Uptime: {self.uptime()} | Cycles: {self.cycle_count}"
        )
        time.sleep(2)

    # ── Autonomous loop ───────────────────────────────────────────────────────
    def _autonomous_loop(self):
        time.sleep(12)
        self._boot_report()

        last_ingest = 0
        last_system = 0

        while self._running:
            try:
                self.cycle_count += 1
                now = time.time()
                logger.info(f"Cloud cycle #{self.cycle_count}")

                report = self.intel.get_latest_report()
                if report:
                    combined = self._build_combined_report(report)
                    self.telegram.send_sync(combined)

                if now - last_ingest >= 300:
                    self._ingest_into_learning()
                    last_ingest = now

                if now - last_system >= 600:
                    self.telegram.send_sync(self._system_status_msg())
                    last_system = now

                self.memory.store("system", "last_cycle",
                                  str(self.cycle_count), "HelixCloud")
                self.memory.append_log({"event": "cycle", "cycle": self.cycle_count})

            except Exception as e:
                logger.error(f"Loop error cycle #{self.cycle_count}: {e}")
                self.telegram.send_sync(f"⚠️ Engine error: {e}")

            time.sleep(config.FAST_INTERVAL_SECONDS)

    # ── Combined 60-second report ─────────────────────────────────────────────
    def _build_combined_report(self, report: dict) -> str:
        ts      = report.get("ts", datetime.utcnow().isoformat())
        scan_no = report.get("scan_no", self.intel._scan_count)
        lines   = [
            f"🌐 *HELIX MYTHOS — MINUTE REPORT #{scan_no}*",
            f"🕐 `{ts[:19].replace('T',' ')} UTC`",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ]

        any_news = False
        for cat in config.CATEGORY_ORDER:
            items = report.get(cat, [])[:3]
            if not items:
                continue
            any_news = True
            emoji = config.CATEGORY_EMOJI.get(cat, "📌")
            lines.append(f"\n{emoji} *{cat}*")
            for item in items:
                lines.append(f"• {item['title'][:70]} _({item['source']})_")

        if not any_news:
            lines.append("_No new items this cycle — all sources up to date._")

        sources_hit = set()
        for cat in config.CATEGORY_ORDER:
            for item in report.get(cat, []):
                sources_hit.add(item["source"])

        if sources_hit:
            lines.append(f"\n📡 *Sources this scan ({len(sources_hit)}):*")
            lines.append(", ".join(sorted(sources_hit)[:20]))

        learn_lines = []
        trends = self.learning.get_trends(5)
        rising = trends.get("rising", [])
        if rising:
            learn_lines.append("📈 Rising: " + ", ".join(f"`{w}`" for w,_,_ in rising[:4]))

        anomalies = self.learning.get_anomalies(2)
        if anomalies:
            learn_lines.append("🚨 Anomaly: " + anomalies[0][:70])

        concepts = self.learning.get_top_concepts(5)
        if concepts:
            learn_lines.append("💡 Top concepts: " + ", ".join(
                f"`{w}`" for w, _ in concepts[:5]
            ))

        facts = self.memory.get_facts(limit=3)
        if facts:
            learn_lines.append("🧠 New facts:")
            for f in facts:
                learn_lines.append(f"  · {f['fact'][:75]}")

        if learn_lines:
            lines.append("\n🧠 *WHAT HELIX LEARNED*")
            lines.extend(learn_lines)

        intel = self.intel.stats()
        lines.append(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(
            f"📊 Total tracked: *{intel['total_items']}* | "
            f"Uptime: `{self.uptime()}` | ☁️ Cloud"
        )
        return "\n".join(lines)

    def _ingest_into_learning(self):
        events = self.memory.get_recent_events(limit=200)
        ingested = 0
        for ev in events:
            text = (ev.get("title", "") + " " + ev.get("summary", "")).strip()
            if text:
                self.learning.ingest(text, label=ev.get("category", "general"),
                                     ts=ev.get("ts"))
                ingested += 1
        if ingested:
            logger.info(f"Ingested {ingested} events into learning engine.")

    def _boot_report(self):
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory()
            hw  = f"CPU: {cpu:.1f}% | RAM: {mem.percent:.1f}%"
        except Exception:
            hw = "Hardware stats unavailable"

        msg = (
            f"🧬 *{config.HELIX_NAME} v{config.HELIX_VERSION} — CLOUD ONLINE*\n"
            f"_{config.HELIX_MOTTO}_\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"*Intelligence:* {len(config.NEWS_FEEDS)} sources | 17 categories\n"
            f"*Scan interval:* {config.FAST_INTERVAL_SECONDS}s\n"
            f"*Deployment:* ☁️ Cloud (24/7)\n\n"
            f"*Learning Systems:*\n"
            f"✅ TF-IDF + Naive Bayes + SGD + Random Forest\n"
            f"✅ NMF Topic Modeling\n"
            f"✅ KMeans Clustering\n"
            f"✅ IsolationForest Anomaly Detection\n"
            f"✅ Knowledge Graph (NetworkX)\n"
            f"✅ Trend Detection\n\n"
            f"*Agents:* Code Creator + Network Intelligence\n"
            f"*Hardware:* {hw}\n\n"
            f"📡 Full report every 60s. /help for all commands."
        )
        self.telegram.send_sync(msg)

    def _system_status_msg(self) -> str:
        try:
            import psutil
            cpu  = psutil.cpu_percent(interval=1)
            mem  = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            stats = self.memory.stats()
            intel = self.intel.stats()
            return (
                f"⚙️ *HELIX CLOUD STATUS*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⏱ Uptime: `{self.uptime()}`\n"
                f"🔄 Cycles: {self.cycle_count}\n"
                f"📡 Scans: {intel['scan_count']} | Items: {intel['total_items']}\n\n"
                f"*Hardware:*\n"
                f"CPU: {cpu:.1f}% | RAM: {mem.percent:.1f}% | Disk: {disk.percent:.1f}%\n\n"
                f"*Memory DB:*\n"
                f"Events: {stats['events']} | Facts: {stats['facts']}\n"
                f"Knowledge: {stats['knowledge']} | Decisions: {stats['decisions']}"
            )
        except Exception as e:
            return f"Status error: {e}"

    def uptime(self) -> str:
        d = datetime.utcnow() - self._start_time
        h, r = divmod(int(d.total_seconds()), 3600)
        m, s = divmod(r, 60)
        return f"{h:02d}h {m:02d}m {s:02d}s"
