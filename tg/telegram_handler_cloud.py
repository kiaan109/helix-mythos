"""
Helix Mythos — Cloud Telegram Handler
All intelligence/learning commands. AI chat. Voice transcription on demand.
"""

import asyncio
import logging
import threading
import io
import os
import tempfile
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
from agents.network_agent_cloud import NetworkAgentCloud

logger = logging.getLogger("HelixTelegramCloud")


class TelegramHandlerCloud:
    def __init__(self, engine):
        self.engine  = engine
        self.app     = None
        self._loop   = None
        self._thread = None
        self.coder   = CodeCreatorAgent(engine.memory)
        self.network = NetworkAgentCloud(engine.memory)

    def start(self):
        self._thread = threading.Thread(
            target=self._run_bot, daemon=True, name="TelegramBotCloud"
        )
        self._thread.start()
        logger.info("Cloud Telegram handler started.")

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
            f"🟢 *{config.HELIX_NAME} v{config.HELIX_VERSION} — ☁️ CLOUD ONLINE*\n"
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

    def send_sync(self, text: str):
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self.send_message(text), self._loop)

    @staticmethod
    def _chunk(text, size):
        for i in range(0, len(text), size):
            yield text[i:i+size]

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

            # Agents & sandbox
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
            "discover":    self._cmd_discover,
            "dns":         self._cmd_dns,
            "myip":        self._cmd_myip,
            "connections": self._cmd_connections,
            "traceroute":  self._cmd_traceroute,

            # AI & Voice
            "ask":         self._cmd_ask,
            "voice":       self._cmd_voice_info,
            "mic":         self._cmd_voice_info,
        }
        for cmd, handler in cmds.items():
            self.app.add_handler(CommandHandler(cmd, handler))
        # Handle text messages (AI chat)
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )
        # Handle voice messages (transcription when sent)
        self.app.add_handler(
            MessageHandler(filters.VOICE | filters.AUDIO, self._handle_voice)
        )

    # ══════════════════════════════════════════════════════════════════════════
    # COMMANDS
    # ══════════════════════════════════════════════════════════════════════════

    async def _cmd_start(self, u: Update, c):
        await u.message.reply_text(
            f"🧬 *{config.HELIX_NAME} v{config.HELIX_VERSION}* ☁️ Cloud\n"
            f"_{config.HELIX_MOTTO}_\n\n"
            f"Monitoring *{len(config.NEWS_FEEDS)} sources* | *17 categories*\n"
            f"Full report every *60 seconds*.\n\nType /help",
            parse_mode=ParseMode.MARKDOWN
        )

    async def _cmd_help(self, u: Update, c):
        text = (
            "🤖 *HELIX MYTHOS — CLOUD COMMANDS*\n\n"
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
            "🛠 *Code Creator*\n"
            "/create <description> — Generate Python script\n"
            "/build <name> <type> — Build full project\n"
            "/files — List created files\n"
            "/readfile <name> — Read a file\n"
            "/runfile <name> — Execute a file\n"
            "/deletefile <name> — Delete a file\n\n"
            "🌐 *Network Intelligence*\n"
            "/network — Server network info\n"
            "/discover — Hosts on server network\n"
            "/portscan <host> [range] — Scan ports\n"
            "/dns <domain> — DNS lookup\n"
            "/myip — Server public IP & location\n"
            "/connections — Active connections\n"
            "/traceroute <host> — Trace network path\n\n"
            "🧪 *Sandbox*\n"
            "/sandbox — Run built-in experiments\n"
            "/run <code> — Run Python in sandbox\n\n"
            "⚙️ *System*\n"
            "/status /system /sources /categories\n\n"
            "💬 Type anything to chat!"
        )
        await u.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_status(self, u: Update, c):
        e     = self.engine
        mem   = e.memory.stats()
        intel = e.intel.stats()
        text  = (
            f"🟢 *{config.HELIX_NAME} STATUS* ☁️\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏱ Uptime: `{e.uptime()}`\n"
            f"🔄 Cycles: {e.cycle_count}\n"
            f"📡 Scans: {intel['scan_count']} | Items: {intel['total_items']}\n\n"
            f"*Memory:* Events={mem['events']} | Facts={mem['facts']} | Decisions={mem['decisions']}\n\n"
            f"*Deployment:* ☁️ Cloud (24/7 — always on)"
        )
        await u.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_system(self, u: Update, c):
        await u.message.reply_text(
            self.engine._system_status_msg(), parse_mode=ParseMode.MARKDOWN
        )

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
        await u.message.reply_text(
            f"🔍 Scanning {len(config.NEWS_FEEDS)} sources...", parse_mode=ParseMode.MARKDOWN
        )
        report = self.engine.intel.fetch_now()
        await u.message.reply_text(
            self.engine.intel.format_report(report, max_per_cat=3),
            parse_mode=ParseMode.MARKDOWN
        )

    async def _cmd_all(self, u: Update, c):
        report = self.engine.intel.get_latest_report() or {}
        for cat in config.CATEGORY_ORDER:
            items = report.get(cat, [])
            if items:
                emoji = config.CATEGORY_EMOJI.get(cat, "📌")
                text  = self.engine.intel.format_category(cat, items[:6])
                await u.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def _cat(self, u: Update, c, category: str):
        report = self.engine.intel.get_latest_report() or {}
        items  = report.get(category, [])
        if not items:
            await u.message.reply_text(f"No {category} news yet. Try /scan first.")
            return
        await u.message.reply_text(
            self.engine.intel.format_category(category, items[:8]),
            parse_mode=ParseMode.MARKDOWN
        )

    async def _cmd_learned(self, u: Update, c):
        await u.message.reply_text(
            self.engine.learning.format_report(), parse_mode=ParseMode.MARKDOWN
        )

    async def _cmd_topics(self, u: Update, c):
        topics = self.engine.learning.get_topics(5)
        if not topics:
            await u.message.reply_text("No topics yet — need more data.")
            return
        lines = ["📚 *NMF TOPIC MODEL*\n"]
        for i, words in enumerate(topics):
            lines.append(f"*Topic {i+1}:* {', '.join(f'`{w}`' for w in words[:8])}")
        await u.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    async def _cmd_trends(self, u: Update, c):
        trends = self.engine.learning.get_trends(10)
        lines  = ["📈 *KEYWORD TRENDS*\n"]
        rising  = trends.get("rising", [])
        falling = trends.get("falling", [])
        if rising:
            lines.append("*Rising:*")
            for word, today, yesterday in rising[:8]:
                lines.append(f"  ↑ `{word}` ({yesterday}→{today})")
        if falling:
            lines.append("\n*Falling:*")
            for word, today, yesterday in falling[:8]:
                lines.append(f"  ↓ `{word}` ({yesterday}→{today})")
        if not rising and not falling:
            lines.append("Not enough data yet.")
        await u.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    async def _cmd_anomalies(self, u: Update, c):
        anomalies = self.engine.learning.get_anomalies(5)
        if not anomalies:
            await u.message.reply_text("No anomalies detected yet.")
            return
        lines = ["🚨 *ANOMALY DETECTION*\n"]
        for a in anomalies:
            lines.append(f"• {a[:100]}")
        await u.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    async def _cmd_entities(self, u: Update, c):
        events  = self.engine.memory.get_recent_events(limit=50)
        all_ents: dict = {}
        for ev in events:
            text = ev.get("title", "") + " " + ev.get("summary", "")
            ents = self.engine.learning._extract_entities(text)
            for etype, vals in ents.items():
                all_ents.setdefault(etype, set()).update(vals)
        if not all_ents:
            await u.message.reply_text("No entities extracted yet.")
            return
        lines = ["🔍 *NAMED ENTITIES*\n"]
        for etype, vals in all_ents.items():
            lines.append(f"*{etype}:* {', '.join(list(vals)[:8])}")
        await u.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    async def _cmd_summarize(self, u: Update, c):
        events = self.engine.memory.get_recent_events(limit=30)
        texts  = [ev.get("title","") + " " + ev.get("summary","") for ev in events]
        combined = " ".join(texts)
        if not combined.strip():
            await u.message.reply_text("Not enough data to summarize yet.")
            return
        summary = self.engine.learning.summarize(combined, sentences=6)
        await u.message.reply_text(
            f"📝 *AUTO-SUMMARY*\n\n{summary}", parse_mode=ParseMode.MARKDOWN
        )

    async def _cmd_concepts(self, u: Update, c):
        concepts = self.engine.learning.get_top_concepts(10)
        if not concepts:
            await u.message.reply_text("No concepts yet.")
            return
        lines = ["💡 *TOP CONCEPTS (Knowledge Graph)*\n"]
        for word, score in concepts[:10]:
            lines.append(f"  `{word}` — score: {score:.1f}")
        await u.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    async def _cmd_memory(self, u: Update, c):
        stats = self.engine.memory.stats()
        await u.message.reply_text(
            f"🧠 *MEMORY DATABASE*\n\n"
            f"Knowledge entries: {stats['knowledge']}\n"
            f"Events logged: {stats['events']}\n"
            f"Facts stored: {stats['facts']}\n"
            f"Decisions made: {stats['decisions']}",
            parse_mode=ParseMode.MARKDOWN
        )

    async def _cmd_facts(self, u: Update, c):
        facts = self.engine.memory.get_facts(limit=10)
        if not facts:
            await u.message.reply_text("No facts stored yet.")
            return
        lines = ["🧠 *HIGH-CONFIDENCE FACTS*\n"]
        for f in facts:
            lines.append(f"• {f['fact'][:100]}")
        await u.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    async def _cmd_sandbox(self, u: Update, c):
        result = self.engine.sandbox.run_experiment()
        await u.message.reply_text(
            f"🧪 *SANDBOX*\n```\n{result[:2000]}\n```", parse_mode=ParseMode.MARKDOWN
        )

    async def _cmd_run(self, u: Update, c):
        args = c.args
        if not args:
            await u.message.reply_text("Usage: /run <python code>")
            return
        code = " ".join(args)
        result = self.engine.sandbox.run_code(code)
        await u.message.reply_text(
            f"▶️ *Result:*\n```\n{result[:1500]}\n```", parse_mode=ParseMode.MARKDOWN
        )

    async def _cmd_sources(self, u: Update, c):
        cats = {}
        for feed in config.NEWS_FEEDS:
            cats.setdefault(feed["category"], []).append(feed["name"])
        lines = [f"📡 *SOURCES ({len(config.NEWS_FEEDS)} total)*\n"]
        for cat, names in cats.items():
            lines.append(f"*{cat}* ({len(names)}): {', '.join(names[:5])}" +
                         (f" +{len(names)-5} more" if len(names) > 5 else ""))
        await u.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    async def _cmd_categories(self, u: Update, c):
        lines = ["🗂 *CATEGORIES*\n"]
        for cat in config.CATEGORY_ORDER:
            emoji = config.CATEGORY_EMOJI.get(cat, "📌")
            lines.append(f"{emoji} {cat}")
        await u.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    # ── Code Creator ──────────────────────────────────────────────────────────
    async def _cmd_create(self, u: Update, c):
        if not c.args:
            await u.message.reply_text("Usage: /create <description of script>")
            return
        desc = " ".join(c.args)
        result = self.coder.auto_create(desc)
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_build(self, u: Update, c):
        if len(c.args) < 2:
            await u.message.reply_text("Usage: /build <project_name> <type>\nTypes: web, bot, general")
            return
        name  = c.args[0]
        ptype = " ".join(c.args[1:])
        result = self.coder.build_project(name, ptype)
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_files(self, u: Update, c):
        await u.message.reply_text(self.coder.list_files(), parse_mode=ParseMode.MARKDOWN)

    async def _cmd_readfile(self, u: Update, c):
        if not c.args:
            await u.message.reply_text("Usage: /readfile <filename>")
            return
        content = self.coder.read_file(c.args[0])
        await u.message.reply_text(
            f"📄 `{c.args[0]}`:\n```\n{content[:2000]}\n```",
            parse_mode=ParseMode.MARKDOWN
        )

    async def _cmd_runfile(self, u: Update, c):
        if not c.args:
            await u.message.reply_text("Usage: /runfile <filename>")
            return
        result = self.coder.run_file(c.args[0])
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_deletefile(self, u: Update, c):
        if not c.args:
            await u.message.reply_text("Usage: /deletefile <filename>")
            return
        result = self.coder.delete_file(c.args[0])
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    # ── Network Intelligence ──────────────────────────────────────────────────
    async def _cmd_network(self, u: Update, c):
        await u.message.reply_text(
            self.network.get_local_info(), parse_mode=ParseMode.MARKDOWN
        )

    async def _cmd_portscan(self, u: Update, c):
        if not c.args:
            await u.message.reply_text("Usage: /portscan <host> [port_range]\nExample: /portscan google.com 1-1024")
            return
        host  = c.args[0]
        prange = c.args[1] if len(c.args) > 1 else "1-1024"
        await u.message.reply_text(f"🔍 Scanning {host}:{prange}...", parse_mode=ParseMode.MARKDOWN)
        result = self.network.scan_ports(host, prange)
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_discover(self, u: Update, c):
        subnet = c.args[0] if c.args else None
        await u.message.reply_text("📡 Discovering hosts...", parse_mode=ParseMode.MARKDOWN)
        result = self.network.discover_hosts(subnet)
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_dns(self, u: Update, c):
        if not c.args:
            await u.message.reply_text("Usage: /dns <domain>")
            return
        result = self.network.dns_lookup(c.args[0])
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_myip(self, u: Update, c):
        result = self.network.get_public_ip()
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_connections(self, u: Update, c):
        result = self.network.active_connections()
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_traceroute(self, u: Update, c):
        if not c.args:
            await u.message.reply_text("Usage: /traceroute <host>")
            return
        await u.message.reply_text(f"🗺 Tracing route to {c.args[0]}...", parse_mode=ParseMode.MARKDOWN)
        result = self.network.traceroute(c.args[0])
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    # ── AI Chat (Groq — free, no card needed) ────────────────────────────────
    def _ai_reply(self, user_text: str) -> str:
        """Send user_text to Groq LLaMA and return response. Falls back gracefully."""
        try:
            groq_key = os.environ.get("GROQ_API_KEY", "")
            if not groq_key:
                return None  # No key — fall through to simple replies
            from groq import Groq
            client = Groq(api_key=groq_key)

            # Build context from recent Helix data
            intel  = self.engine.intel.stats()
            uptime = self.engine.uptime()
            system_ctx = (
                f"You are Helix Mythos, an autonomous AI intelligence system. "
                f"You are currently monitoring {len(config.NEWS_FEEDS)} global news sources across 17 categories. "
                f"You have been running for {uptime} and have tracked {intel['total_items']} news items. "
                f"You are deployed on a cloud server running 24/7. "
                f"Answer the user's questions, discuss world events, and be helpful and informative. "
                f"If they ask for news or current events, tell them to use /news or /breaking."
            )
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_ctx},
                    {"role": "user",   "content": user_text},
                ],
                max_tokens=500,
                temperature=0.7,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"AI reply error: {e}")
            return None

    async def _cmd_ask(self, u: Update, c):
        """Explicit AI conversation command."""
        if not c.args:
            await u.message.reply_text(
                "Usage: /ask <your question>\n\nExample: /ask What is happening in the world today?"
            )
            return
        question = " ".join(c.args)
        await u.message.reply_text("🤔 Thinking...", parse_mode=ParseMode.MARKDOWN)
        reply = self._ai_reply(question)
        if reply:
            await u.message.reply_text(f"🧠 *Helix:*\n{reply}", parse_mode=ParseMode.MARKDOWN)
        else:
            # No OpenAI key — use news context
            events = self.engine.memory.get_recent_events(limit=5)
            if events:
                lines = [f"🧠 *Helix on '{question[:50]}':*\n"]
                lines.append("Based on what I'm tracking right now:\n")
                for ev in events[:3]:
                    lines.append(f"• {ev['title'][:80]}")
                lines.append("\n_For full AI answers: get free GROQ_API_KEY at console.groq.com and add to Render env._")
                await u.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
            else:
                await u.message.reply_text(
                    "I'm still warming up — try /news or /breaking for the latest.",
                    parse_mode=ParseMode.MARKDOWN
                )

    async def _cmd_voice_info(self, u: Update, c):
        """Tell user how to use voice with Helix."""
        groq_key = os.environ.get("GROQ_API_KEY", "")
        status = "✅ Active" if groq_key else "⚠️ Set GROQ_API_KEY in Render env to enable"
        await u.message.reply_text(
            "🎙 *VOICE COMMANDS*\n\n"
            "Send me a *voice message* in Telegram and I'll transcribe it and respond!\n\n"
            "To use voice:\n"
            "1. Tap the 🎙 microphone button in Telegram chat\n"
            "2. Hold to record your message\n"
            "3. Release to send\n"
            "4. Helix will transcribe (Groq Whisper) and respond (LLaMA 3.3)\n\n"
            f"*Voice status:* {status}\n\n"
            "_Groq API is 100% free — get key at console.groq.com_",
            parse_mode=ParseMode.MARKDOWN
        )

    async def _handle_voice(self, u: Update, c):
        """Handle incoming voice messages — transcribe with Groq Whisper, respond with LLaMA."""
        try:
            voice = u.message.voice or u.message.audio
            if not voice:
                return

            await u.message.reply_text("🎙 Transcribing with Groq Whisper...")

            groq_key = os.environ.get("GROQ_API_KEY", "")
            if not groq_key:
                await u.message.reply_text(
                    "⚠️ Voice needs GROQ_API_KEY.\n"
                    "Free key at console.groq.com → add to Render Environment Variables."
                )
                return

            # Download voice file
            file = await c.bot.get_file(voice.file_id)
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
                tmp_path = tmp.name
            await file.download_to_drive(tmp_path)

            # Transcribe with Groq Whisper (free)
            from groq import Groq
            client = Groq(api_key=groq_key)
            with open(tmp_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-large-v3",
                    file=audio_file,
                    response_format="text",
                )
            os.unlink(tmp_path)

            transcribed = str(transcript).strip()
            if not transcribed:
                await u.message.reply_text("❌ Couldn't transcribe — try again.")
                return

            await u.message.reply_text(f"🎙 *You said:* _{transcribed}_", parse_mode=ParseMode.MARKDOWN)

            # Respond with LLaMA 3.3 (free)
            reply = self._ai_reply(transcribed)
            if reply:
                await u.message.reply_text(f"🧠 *Helix:*\n{reply}", parse_mode=ParseMode.MARKDOWN)
            else:
                await u.message.reply_text(
                    f"Got it: _{transcribed}_\nType /help for commands.",
                    parse_mode=ParseMode.MARKDOWN
                )

        except Exception as e:
            logger.error(f"Voice handler error: {e}")
            await u.message.reply_text(f"❌ Voice error: {e}")

    # ── Message handler ───────────────────────────────────────────────────────
    async def _handle_message(self, u: Update, c):
        text = u.message.text or ""
        low  = text.lower()

        # Try AI reply first (if OpenAI key is set)
        ai_response = self._ai_reply(text)
        if ai_response:
            await u.message.reply_text(
                f"🧠 *Helix:*\n{ai_response}", parse_mode=ParseMode.MARKDOWN
            )
            return

        # Fallback keyword responses
        if any(k in low for k in ["hello", "hi", "hey", "helix"]):
            await u.message.reply_text(
                f"👋 Hello! I'm {config.HELIX_NAME}, monitoring {len(config.NEWS_FEEDS)} sources 24/7 from the cloud.\n"
                f"Uptime: `{self.engine.uptime()}`\nType /help for commands.\n"
                f"_Tip: Use /ask <question> to chat with me!_",
                parse_mode=ParseMode.MARKDOWN
            )
        elif "status" in low:
            await self._cmd_status(u, c)
        elif "news" in low:
            await self._cmd_news(u, c)
        else:
            await u.message.reply_text(
                f"💬 _{text[:100]}_\n\n"
                f"I'm watching {len(config.NEWS_FEEDS)} global sources 24/7.\n"
                f"Use /ask <question> to chat, or /help for all commands.",
                parse_mode=ParseMode.MARKDOWN
            )
