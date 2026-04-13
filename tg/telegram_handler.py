"""
Helix Mythos — Telegram Handler
All commands · VisionEngine · LearningEngine · Full intelligence
"""

import asyncio
import logging
import threading
import io
from datetime import datetime

from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from telegram.constants import ParseMode

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import config
from agents.code_creator import CodeCreatorAgent
from agents.network_agent import NetworkAgent

logger = logging.getLogger("HelixTelegram")


class TelegramHandler:
    def __init__(self, engine):
        self.engine   = engine
        self.app      = None
        self._loop    = None
        self._thread  = None
        self.coder    = CodeCreatorAgent(engine.memory)
        self.network  = NetworkAgent(engine.memory)

    # ── Bootstrap ─────────────────────────────────────────────────────────────
    def start(self):
        self._thread = threading.Thread(
            target=self._run_bot, daemon=True, name="TelegramBot"
        )
        self._thread.start()
        logger.info("Telegram handler started.")

    def _run_bot(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._async_run())

    async def _async_run(self):
        self.app = ApplicationBuilder().token(config.BOT_TOKEN).build()
        self._register_handlers()
        await self.app.initialize()
        await self.app.start()
        await self.send_message(
            f"🟢 *{config.HELIX_NAME} v{config.HELIX_VERSION} ONLINE*\n"
            f"📡 {len(config.NEWS_FEEDS)} sources | 17 categories | 60s updates\n"
            f"_{config.HELIX_MOTTO}_\nType /help",
            parse_mode=ParseMode.MARKDOWN
        )
        await self.app.updater.start_polling(drop_pending_updates=True)
        while True:
            await asyncio.sleep(60)

    # ── Outbound ──────────────────────────────────────────────────────────────
    async def send_message(self, text: str, parse_mode=ParseMode.MARKDOWN):
        if not self.app:
            return
        try:
            for chunk in self._chunk(text, 4000):
                await self.app.bot.send_message(
                    chat_id=config.CHAT_ID, text=chunk, parse_mode=parse_mode
                )
        except Exception as e:
            logger.error(f"send_message: {e}")

    async def send_photo(self, data: bytes, caption: str = ""):
        if not self.app or not data:
            return
        try:
            await self.app.bot.send_photo(
                chat_id=config.CHAT_ID, photo=io.BytesIO(data),
                caption=caption[:1000], parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"send_photo: {e}")

    def send_sync(self, text: str):
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self.send_message(text), self._loop)

    def send_photo_sync(self, data: bytes, caption: str = ""):
        if self._loop and self._loop.is_running() and data:
            asyncio.run_coroutine_threadsafe(self.send_photo(data, caption), self._loop)

    # ── Handler registration ──────────────────────────────────────────────────
    def _register_handlers(self):
        cmds = {
            # Core
            "start":       self._cmd_start,
            "help":        self._cmd_help,
            "status":      self._cmd_status,
            "system":      self._cmd_system,

            # Intelligence
            "news":        self._cmd_news,
            "breaking":    self._cmd_breaking,
            "latest":      self._cmd_latest,
            "scan":        self._cmd_scan,
            "all":         self._cmd_all,

            # Categories
            "world":       lambda u,c: self._cat(u,c,"World"),
            "geo":         lambda u,c: self._cat(u,c,"Geopolitics"),
            "geopolitics": lambda u,c: self._cat(u,c,"Geopolitics"),
            "military":    lambda u,c: self._cat(u,c,"Military"),
            "politics":    lambda u,c: self._cat(u,c,"Politics"),
            "finance":     lambda u,c: self._cat(u,c,"Finance"),
            "crypto":      lambda u,c: self._cat(u,c,"Crypto"),
            "science":     lambda u,c: self._cat(u,c,"Science"),
            "research":    lambda u,c: self._cat(u,c,"Research"),
            "health":      lambda u,c: self._cat(u,c,"Health"),
            "ai":          lambda u,c: self._cat(u,c,"AI_Tech"),
            "tech":        lambda u,c: self._cat(u,c,"Technology"),
            "space":       lambda u,c: self._cat(u,c,"Space"),
            "climate":     lambda u,c: self._cat(u,c,"Climate"),
            "energy":      lambda u,c: self._cat(u,c,"Energy"),
            "disasters":   lambda u,c: self._cat(u,c,"Disasters"),
            "culture":     lambda u,c: self._cat(u,c,"Culture"),

            # Learning / ML
            "learned":     self._cmd_learned,
            "topics":      self._cmd_topics,
            "trends":      self._cmd_trends,
            "anomalies":   self._cmd_anomalies,
            "entities":    self._cmd_entities,
            "summarize":   self._cmd_summarize,
            "concepts":    self._cmd_concepts,
            "memory":      self._cmd_memory,
            "facts":       self._cmd_facts,

            # Vision
            "camera":      self._cmd_camera,
            "camera_live": self._cmd_camera_live,
            "camera_stop": self._cmd_camera_stop,
            "screenshot":  self._cmd_screenshot,
            "ocr":         self._cmd_ocr,
            "vision":      self._cmd_vision_status,

            # Agents & sandbox
            "agents":      self._cmd_agents,
            "tasks":       self._cmd_tasks,
            "sandbox":     self._cmd_sandbox,
            "run":         self._cmd_run,

            # Sources / meta
            "sources":     self._cmd_sources,
            "categories":  self._cmd_categories,

            # Code Creator
            "create":      self._cmd_create,
            "build":       self._cmd_build,
            "files":       self._cmd_files,
            "readfile":    self._cmd_readfile,
            "runfile":     self._cmd_runfile,
            "deletefile":  self._cmd_deletefile,

            # Network Intelligence
            "network":     self._cmd_network,
            "portscan":    self._cmd_portscan,
            "wifi":        self._cmd_wifi,
            "discover":    self._cmd_discover,
            "dns":         self._cmd_dns,
            "myip":        self._cmd_myip,
            "connections": self._cmd_connections,
            "traceroute":  self._cmd_traceroute,
        }
        for cmd, handler in cmds.items():
            self.app.add_handler(CommandHandler(cmd, handler))
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )

    # ══════════════════════════════════════════════════════════════════════════
    # COMMANDS
    # ══════════════════════════════════════════════════════════════════════════

    async def _cmd_start(self, u: Update, c):
        await u.message.reply_text(
            f"🧬 *{config.HELIX_NAME} v{config.HELIX_VERSION}*\n"
            f"_{config.HELIX_MOTTO}_\n\n"
            f"Monitoring *{len(config.NEWS_FEEDS)} sources* | *17 categories*\n"
            f"Full report every *60 seconds*.\n\nType /help",
            parse_mode=ParseMode.MARKDOWN
        )

    async def _cmd_help(self, u: Update, c):
        text = (
            "🤖 *HELIX MYTHOS — COMMANDS*\n\n"
            "📡 *Intelligence*\n"
            "/news /breaking /latest /scan /all\n\n"
            "🌍 *Categories*\n"
            "/world /geo /military /politics\n"
            "/finance /crypto /science /research\n"
            "/health /ai /tech /space\n"
            "/climate /energy /disasters /culture\n\n"
            "🧠 *Learning & ML*\n"
            "/learned — Full ML report\n"
            "/topics — NMF topic model\n"
            "/trends — Rising/falling keywords\n"
            "/anomalies — Anomaly detection\n"
            "/entities — Named entity extraction\n"
            "/concepts — Knowledge graph top concepts\n"
            "/summarize — Auto-summarize recent news\n"
            "/facts — High-confidence facts\n"
            "/memory — Memory DB stats\n\n"
            "👁️ *Vision (YOLOv8 + Face + Motion + OCR)*\n"
            "/camera — Snapshot with full annotations\n"
            "/camera_live — Continuous live feed to Telegram\n"
            "/camera_stop — Stop live feed\n"
            "/screenshot — Screen capture + OCR\n"
            "/ocr — Read text from screen\n"
            "/vision — Vision system status\n\n"
            "🤖 *Agents*\n"
            "/agents — All 7 agent statuses\n"
            "/tasks — Recent agent decisions\n\n"
            "🧪 *Sandbox*\n"
            "/sandbox — Run built-in experiments\n"
            "/run <code> — Run Python in sandbox\n\n"
            "🛠 *Code Creator*\n"
            "/create <description> — Generate a Python script\n"
            "/build <name> <type> — Build full project\n"
            "/files — List all created files\n"
            "/readfile <name> — Read a file\n"
            "/runfile <name> — Execute a file\n"
            "/deletefile <name> — Delete a file\n\n"
            "🌐 *Network Intelligence*\n"
            "/network — Local network info\n"
            "/wifi — Scan all visible WiFi networks\n"
            "/discover — Find all devices on network\n"
            "/portscan <host> [range] — Scan ports\n"
            "/dns <domain> — DNS lookup\n"
            "/myip — Your public IP & location\n"
            "/connections — Active network connections\n"
            "/traceroute <host> — Trace network path\n\n"
            "⚙️ *System*\n"
            "/status /system /sources /categories\n\n"
            "💬 Type anything to chat!"
        )
        await u.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_status(self, u: Update, c):
        e     = self.engine
        mem   = e.memory.stats()
        intel = e.intel.stats()
        vs    = e.vision.stats()
        text  = (
            f"🟢 *{config.HELIX_NAME} STATUS*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏱ Uptime: `{e.uptime()}`\n"
            f"🔄 Cycles: {e.cycle_count}\n"
            f"📡 Scans: {intel['scan_count']} | Items: {intel['total_items']}\n\n"
            f"*Memory:* Events={mem['events']} | Facts={mem['facts']} | Decisions={mem['decisions']}\n\n"
            f"*Vision:* YOLO={'✅' if vs['yolo_available'] else '❌'} | "
            f"FPS={vs['fps']} | Running={'✅' if vs['running'] else '❌'}\n\n"
            f"{e.agent_mgr.status_report()}"
        )
        await u.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_news(self, u: Update, c):
        await u.message.reply_text("📡 Compiling global report...", parse_mode=ParseMode.MARKDOWN)
        report = self.engine.intel.get_latest_report() or self.engine.intel.fetch_now()
        await u.message.reply_text(
            self.engine.intel.format_report(report, max_per_cat=4),
            parse_mode=ParseMode.MARKDOWN
        )

    async def _cmd_breaking(self, u: Update, c):
        await u.message.reply_text(
            self.engine.intel.format_breaking(8), parse_mode=ParseMode.MARKDOWN
        )

    async def _cmd_latest(self, u: Update, c):
        events = self.engine.memory.get_recent_events(limit=15)
        if not events:
            await u.message.reply_text("No events yet.")
            return
        lines = ["📰 *LATEST 15 EVENTS*\n"]
        for ev in events:
            ts  = datetime.utcfromtimestamp(ev["ts"]).strftime("%H:%M UTC")
            em  = config.CATEGORY_EMOJI.get(ev["category"], "📌")
            lines.append(f"{em} *{ev['title'][:65]}*\n   _{ev['source']} · {ts}_\n")
        await u.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    async def _cmd_scan(self, u: Update, c):
        await u.message.reply_text(f"🔍 Scanning {len(config.NEWS_FEEDS)} sources...", parse_mode=ParseMode.MARKDOWN)
        report = self.engine.intel.fetch_now()
        await u.message.reply_text(
            self.engine.intel.format_report(report, max_per_cat=3),
            parse_mode=ParseMode.MARKDOWN
        )

    async def _cmd_all(self, u: Update, c):
        await u.message.reply_text("📡 Dumping all 17 categories...", parse_mode=ParseMode.MARKDOWN)
        for cat in config.CATEGORY_ORDER:
            text = self.engine.intel.format_category(cat, limit=8)
            await u.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            await asyncio.sleep(0.3)

    async def _cat(self, u: Update, c, cat: str):
        await u.message.reply_text(
            self.engine.intel.format_category(cat, limit=12),
            parse_mode=ParseMode.MARKDOWN
        )

    # ── Learning commands ─────────────────────────────────────────────────────
    async def _cmd_learned(self, u: Update, c):
        await u.message.reply_text(
            self.engine.learning.format_report(), parse_mode=ParseMode.MARKDOWN
        )

    async def _cmd_topics(self, u: Update, c):
        topics = self.engine.learning.get_topics(8)
        if not topics:
            await u.message.reply_text("No topics yet — need more data.")
            return
        lines = ["📌 *NMF TOPIC MODEL*\n"]
        for t in topics:
            lines.append(f"Topic {t['topic_id']}: `{', '.join(t['words'][:6])}`")
        await u.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    async def _cmd_trends(self, u: Update, c):
        trends  = self.engine.learning.get_trends(10)
        rising  = trends.get("rising", [])
        falling = trends.get("falling", [])
        lines   = ["📈 *KEYWORD TRENDS*\n"]
        if rising:
            lines.append("*Rising:*")
            for word, today, yest in rising[:8]:
                lines.append(f"  ↑ `{word}` +{today-yest} ({yest}→{today})")
        if falling:
            lines.append("\n*Falling:*")
            for word, today, yest in falling[:6]:
                lines.append(f"  ↓ `{word}` -{yest-today} ({yest}→{today})")
        if not rising and not falling:
            lines.append("Not enough data yet — check back after a few scans.")
        await u.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    async def _cmd_anomalies(self, u: Update, c):
        anomalies = self.engine.learning.get_anomalies(8)
        if not anomalies:
            await u.message.reply_text("🚨 No anomalies detected yet.")
            return
        lines = ["🚨 *ANOMALY DETECTION*\n"]
        for a in anomalies:
            lines.append(f"• {a[:100]}")
        await u.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    async def _cmd_entities(self, u: Update, c):
        entities = self.engine.learning.get_entities()
        lines    = ["🏷 *EXTRACTED ENTITIES*\n"]
        for etype, values in entities.items():
            if values:
                lines.append(f"*{etype}:* {', '.join(str(v)[:40] for v in values[:5])}")
        await u.message.reply_text("\n".join(lines) if len(lines) > 1 else "No entities extracted yet.",
                                   parse_mode=ParseMode.MARKDOWN)

    async def _cmd_summarize(self, u: Update, c):
        await u.message.reply_text("📝 Auto-summarizing recent news...", parse_mode=ParseMode.MARKDOWN)
        summary = self.engine.learning.summarize(n_sentences=6)
        await u.message.reply_text(f"📝 *AUTO-SUMMARY*\n\n{summary}", parse_mode=ParseMode.MARKDOWN)

    async def _cmd_concepts(self, u: Update, c):
        concepts = self.engine.learning.get_top_concepts(20)
        if not concepts:
            await u.message.reply_text("Knowledge graph not built yet.")
            return
        lines = ["💡 *KNOWLEDGE GRAPH — TOP CONCEPTS*\n"]
        for word, weight in concepts[:20]:
            lines.append(f"• `{word}` (weight: {weight})")
        await u.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    async def _cmd_memory(self, u: Update, c):
        stats = self.engine.memory.stats()
        await u.message.reply_text(
            f"🗄️ *MEMORY DB*\n"
            f"Events: {stats['events']}\nFacts: {stats['facts']}\n"
            f"Knowledge: {stats['knowledge']}\nDecisions: {stats['decisions']}",
            parse_mode=ParseMode.MARKDOWN
        )

    async def _cmd_facts(self, u: Update, c):
        facts = self.engine.memory.get_facts(limit=15)
        if not facts:
            await u.message.reply_text("No facts yet.")
            return
        lines = ["💡 *TOP FACTS*\n"]
        for f in facts:
            conf = int(f["confidence"] * 100)
            lines.append(f"[{conf}%] {f['fact'][:90]}")
        await u.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    # ── Vision commands ───────────────────────────────────────────────────────
    async def _cmd_camera(self, u: Update, c):
        await u.message.reply_text("📷 Capturing annotated frame...", parse_mode=ParseMode.MARKDOWN)
        data = self.engine.vision.capture_frame()
        if data:
            await self.send_photo(data, caption="📷 *Helix Vision* — YOLOv8 + Face + Motion + Scene")
        else:
            # Try last frame from live loop
            data = self.engine.vision.get_last_frame()
            if data:
                await self.send_photo(data, caption="📷 *Last Live Frame*")
            else:
                await u.message.reply_text("⚠️ Camera not available.", parse_mode=ParseMode.MARKDOWN)

    async def _cmd_camera_live(self, u: Update, c):
        await u.message.reply_text(
            "📹 *Live camera feed active.*\n"
            "Frames with YOLO annotations sent continuously.\n"
            "Use /camera_stop to stop.",
            parse_mode=ParseMode.MARKDOWN
        )
        # Live loop already running in engine — just set send interval to fast
        self.engine.vision._send_interval = 5   # send every 5 seconds

    async def _cmd_camera_stop(self, u: Update, c):
        self.engine.vision._send_interval = 999999   # effectively stop sending
        await u.message.reply_text("📹 Live camera feed paused.", parse_mode=ParseMode.MARKDOWN)

    async def _cmd_screenshot(self, u: Update, c):
        await u.message.reply_text("🖥️ Capturing screen + OCR...", parse_mode=ParseMode.MARKDOWN)
        data = self.engine.vision.capture_screenshot()
        if data:
            await self.send_photo(data, caption="🖥️ *Screenshot* — OCR annotated")
        else:
            await u.message.reply_text("⚠️ Screenshot failed (pyautogui may need display).",
                                       parse_mode=ParseMode.MARKDOWN)

    async def _cmd_ocr(self, u: Update, c):
        await u.message.reply_text("🔡 Reading screen text...", parse_mode=ParseMode.MARKDOWN)
        text = self.engine.vision.get_ocr_text()
        await u.message.reply_text(
            f"🔡 *OCR Result:*\n```\n{text[:3000]}\n```",
            parse_mode=ParseMode.MARKDOWN
        )

    async def _cmd_vision_status(self, u: Update, c):
        vs = self.engine.vision.stats()
        lines = [
            "👁️ *VISION SYSTEM STATUS*",
            f"OpenCV: {'✅' if vs['opencv_available'] else '❌'}",
            f"YOLOv8: {'✅' if vs['yolo_available'] else '⚠️ (Haar fallback)'}",
            f"Face Recognition: {'✅' if vs['face_rec_available'] else '⚠️ (Haar fallback)'}",
            f"Tesseract OCR: {'✅' if vs['tesseract_available'] else '❌'}",
            f"Live Loop: {'✅ Running' if vs['running'] else '❌ Stopped'}",
            f"FPS: {vs['fps']}",
        ]
        await u.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    # ── Agent / sandbox commands ──────────────────────────────────────────────
    async def _cmd_agents(self, u: Update, c):
        await u.message.reply_text(
            self.engine.agent_mgr.status_report(), parse_mode=ParseMode.MARKDOWN
        )

    async def _cmd_tasks(self, u: Update, c):
        decisions = self.engine.memory.get_decisions(limit=10)
        if not decisions:
            await u.message.reply_text("No tasks logged yet.")
            return
        lines = ["📋 *RECENT TASKS*\n"]
        for d in decisions:
            ts = datetime.utcfromtimestamp(d["ts"]).strftime("%H:%M UTC")
            lines.append(f"🤖 *{d['agent']}* @ {ts}\n_{d['action'][:60]}_")
        await u.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    async def _cmd_sandbox(self, u: Update, c):
        await u.message.reply_text("🧪 Running experiments...", parse_mode=ParseMode.MARKDOWN)
        for r in self.engine.sandbox.predefined_experiments():
            name   = r.get("name", f"Exp #{r['id']}")
            status = "✅" if r["success"] else "❌"
            out    = r["output"][:300] if r["output"] else r["error"][:300]
            await u.message.reply_text(
                f"🧪 *{name}* {status}\n```\n{out}\n```",
                parse_mode=ParseMode.MARKDOWN
            )

    async def _cmd_run(self, u: Update, c):
        code = " ".join(c.args) if c.args else ""
        if not code:
            await u.message.reply_text("Usage: /run <python code>")
            return
        result = self.engine.sandbox.run_experiment(code)
        await u.message.reply_text(
            self.engine.sandbox.format_result(result), parse_mode=ParseMode.MARKDOWN
        )

    async def _cmd_sources(self, u: Update, c):
        by_cat = {}
        for cat, name, url in config.NEWS_FEEDS:
            by_cat.setdefault(cat, []).append(name)
        lines = [f"📡 *{len(config.NEWS_FEEDS)} MONITORED SOURCES*\n"]
        for cat in config.CATEGORY_ORDER:
            if cat not in by_cat:
                continue
            em = config.CATEGORY_EMOJI.get(cat, "📌")
            lines.append(f"{em} *{cat}* ({len(by_cat[cat])}): {', '.join(by_cat[cat])}")
        await u.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    async def _cmd_categories(self, u: Update, c):
        intel_stats = self.engine.intel.stats()
        lines = [
            f"📊 *CATEGORIES*",
            f"Total sources: {intel_stats['sources']}",
            f"Total items: {intel_stats['total_items']}\n",
        ]
        for cat in config.CATEGORY_ORDER:
            em    = config.CATEGORY_EMOJI.get(cat, "📌")
            count = intel_stats["categories"].get(cat, 0)
            srcs  = sum(1 for x,_,_ in config.NEWS_FEEDS if x == cat)
            lines.append(f"{em} *{cat}*: {count} items | {srcs} sources")
        await u.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    async def _cmd_system(self, u: Update, c):
        result = self.engine.agent_mgr.dispatch("automation", "system health check")
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    # ── Conversational ────────────────────────────────────────────────────────
    async def _handle_message(self, u: Update, c):
        msg      = u.message.text.lower().strip()
        response = self._converse(msg)
        await u.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

    def _converse(self, msg: str) -> str:
        e = self.engine

        if any(k in msg for k in ["learn", "know", "train", "model", "topics"]):
            return e.learning.format_report()

        if any(k in msg for k in ["world", "news", "happening", "global", "events"]):
            report = e.intel.get_latest_report()
            return e.intel.format_report(report, max_per_cat=2) if report else "Scanning..."

        for cat in config.CATEGORY_ORDER:
            if cat.lower() in msg:
                return e.intel.format_category(cat, limit=5)

        if any(k in msg for k in ["see", "camera", "look", "detect", "vision"]):
            data = e.vision.capture_frame() or e.vision.get_last_frame()
            if data:
                self.send_photo_sync(data, "👁️ *Helix Vision*")
                return "Frame sent with YOLO annotations."
            return "Camera not available."

        if any(k in msg for k in ["status", "doing", "running", "uptime"]):
            intel = e.intel.stats()
            vs    = e.vision.stats()
            return (
                f"🤖 *Running autonomously:*\n"
                f"• Sources: {intel['sources']} | Scans: {intel['scan_count']}\n"
                f"• Total items tracked: {intel['total_items']}\n"
                f"• Vision FPS: {vs['fps']} | YOLO: {'✅' if vs['yolo_available'] else '⚠️'}\n"
                f"• Uptime: {e.uptime()} | Cycles: {e.cycle_count}"
            )

        if any(k in msg for k in ["hello", "hi", "hey"]):
            return (
                f"👋 *{config.HELIX_NAME}* here!\n"
                f"Watching {len(config.NEWS_FEEDS)} sources right now.\n"
                f"Type /help to see everything I can do."
            )

        if any(k in msg for k in ["summarize", "summary", "brief"]):
            return e.learning.summarize(n_sentences=5)

        if any(k in msg for k in ["anomaly", "unusual", "strange"]):
            a = e.learning.get_anomalies(5)
            return ("🚨 Anomalies:\n" + "\n".join(f"• {x[:90]}" for x in a)) if a else "No anomalies detected."

        if any(k in msg for k in ["trend", "rising", "falling"]):
            trends = e.learning.get_trends(6)
            r = ", ".join(w for w,_,_ in trends["rising"][:5]) or "none"
            f_ = ", ".join(w for w,_,_ in trends["falling"][:5]) or "none"
            return f"📈 Rising: {r}\n📉 Falling: {f_}"

        # Fallback: research it
        result = e.agent_mgr.dispatch("research", msg)
        return f"🔍 *Research:*\n{result}"

    # ══════════════════════════════════════════════════════════════════════════
    # CODE CREATOR COMMANDS
    # ══════════════════════════════════════════════════════════════════════════

    async def _cmd_create(self, u: Update, c):
        """Create a code file: /create <description>"""
        desc = " ".join(c.args) if c.args else ""
        if not desc:
            await u.message.reply_text(
                "Usage: `/create <description>`\n"
                "Examples:\n"
                "• `/create web scraper for news sites`\n"
                "• `/create machine learning classifier`\n"
                "• `/create telegram bot`\n"
                "• `/create file reader and writer`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        await u.message.reply_text("🛠 Generating code...", parse_mode=ParseMode.MARKDOWN)
        result = self.coder.auto_create(desc)
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_build(self, u: Update, c):
        """Build a full project: /build <name> <type>"""
        if not c.args or len(c.args) < 2:
            await u.message.reply_text(
                "Usage: `/build <project_name> <type>`\n"
                "Types: `web`, `bot`, `ml`, `api`, `tool`\n"
                "Example: `/build myapp web`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        name    = c.args[0]
        ptype   = " ".join(c.args[1:])
        await u.message.reply_text(f"🏗 Building project `{name}`...", parse_mode=ParseMode.MARKDOWN)
        result  = self.coder.build_project(name, ptype)
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_files(self, u: Update, c):
        result = self.coder.list_files()
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_readfile(self, u: Update, c):
        fname = " ".join(c.args) if c.args else ""
        if not fname:
            await u.message.reply_text("Usage: `/readfile <filename>`", parse_mode=ParseMode.MARKDOWN)
            return
        content = self.coder.read_file(fname)
        await u.message.reply_text(f"📄 `{fname}`:\n```\n{content[:2500]}\n```", parse_mode=ParseMode.MARKDOWN)

    async def _cmd_runfile(self, u: Update, c):
        fname = " ".join(c.args) if c.args else ""
        if not fname:
            await u.message.reply_text("Usage: `/runfile <filename>`", parse_mode=ParseMode.MARKDOWN)
            return
        await u.message.reply_text(f"▶️ Running `{fname}`...", parse_mode=ParseMode.MARKDOWN)
        result = self.coder.run_file(fname)
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_deletefile(self, u: Update, c):
        fname = " ".join(c.args) if c.args else ""
        if not fname:
            await u.message.reply_text("Usage: `/deletefile <filename>`", parse_mode=ParseMode.MARKDOWN)
            return
        result = self.coder.delete_file(fname)
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    # ══════════════════════════════════════════════════════════════════════════
    # NETWORK INTELLIGENCE COMMANDS
    # ══════════════════════════════════════════════════════════════════════════

    async def _cmd_network(self, u: Update, c):
        await u.message.reply_text("🌐 Gathering local network info...", parse_mode=ParseMode.MARKDOWN)
        result = self.network.get_local_info()
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_portscan(self, u: Update, c):
        """Scan ports: /portscan <host> [port_range]"""
        if not c.args:
            await u.message.reply_text(
                "Usage: `/portscan <host> [port-range]`\n"
                "Examples:\n"
                "• `/portscan 192.168.1.1`\n"
                "• `/portscan 192.168.1.1 1-500`\n"
                "⚠️ Use on your own network only.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        host       = c.args[0]
        port_range = c.args[1] if len(c.args) > 1 else "1-1024"
        await u.message.reply_text(f"🔍 Scanning {host}:{port_range}...", parse_mode=ParseMode.MARKDOWN)
        result = await asyncio.get_event_loop().run_in_executor(
            None, self.network.scan_ports, host, port_range
        )
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_wifi(self, u: Update, c):
        await u.message.reply_text("📶 Scanning WiFi networks...", parse_mode=ParseMode.MARKDOWN)
        result = await asyncio.get_event_loop().run_in_executor(
            None, self.network.scan_wifi
        )
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_discover(self, u: Update, c):
        subnet = c.args[0] if c.args else None
        msg    = f"Scanning subnet {subnet}..." if subnet else "Discovering hosts on local network..."
        await u.message.reply_text(f"📡 {msg}", parse_mode=ParseMode.MARKDOWN)
        result = await asyncio.get_event_loop().run_in_executor(
            None, self.network.discover_hosts, subnet
        )
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_dns(self, u: Update, c):
        domain = c.args[0] if c.args else ""
        if not domain:
            await u.message.reply_text("Usage: `/dns <domain>`\nExample: `/dns google.com`", parse_mode=ParseMode.MARKDOWN)
            return
        result = self.network.dns_lookup(domain)
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_myip(self, u: Update, c):
        await u.message.reply_text("🌍 Looking up public IP...", parse_mode=ParseMode.MARKDOWN)
        result = await asyncio.get_event_loop().run_in_executor(
            None, self.network.get_public_ip
        )
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_connections(self, u: Update, c):
        result = self.network.active_connections()
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_traceroute(self, u: Update, c):
        host = c.args[0] if c.args else ""
        if not host:
            await u.message.reply_text("Usage: `/traceroute <host>`", parse_mode=ParseMode.MARKDOWN)
            return
        await u.message.reply_text(f"🗺 Tracing route to {host}...", parse_mode=ParseMode.MARKDOWN)
        result = await asyncio.get_event_loop().run_in_executor(
            None, self.network.traceroute, host
        )
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    # ── Utility ───────────────────────────────────────────────────────────────
    @staticmethod
    def _chunk(text: str, size: int) -> list:
        return [text[i:i+size] for i in range(0, len(text), size)]
