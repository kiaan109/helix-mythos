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
from agents.security_agent import SecurityAgent

logger = logging.getLogger("HelixTelegramCloud")


class TelegramHandlerCloud:
    def __init__(self, engine):
        self.engine   = engine
        self.app      = None
        self._loop    = None
        self._thread  = None
        self.coder    = CodeCreatorAgent(engine.memory)
        self.network  = NetworkAgentCloud(engine.memory)
        self.security = SecurityAgent(engine.memory)

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
            "speak":       self._cmd_speak,
            "voicenews":   self._cmd_voice_news,
            "voicebreaking": self._cmd_voice_breaking,

            # Security & Pentesting
            "hash":        self._cmd_hash_identify,
            "crack":       self._cmd_crack_hash,
            "genhash":     self._cmd_gen_hash,
            "genpass":     self._cmd_gen_password,
            "checkpass":   self._cmd_check_password,
            "ssl":         self._cmd_ssl,
            "subdomains":  self._cmd_subdomains,
            "vulnscan":    self._cmd_vuln_scan,
            "banner":      self._cmd_banner,
            "headers":     self._cmd_headers,
            "sqli":        self._cmd_sqli,
            "cve":         self._cmd_cve,
            "osint":       self._cmd_osint,
            "whois":       self._cmd_whois,
            "recon":       self._cmd_recon,
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
            "🔊 *Voice & Sound*\n"
            "/speak <text or question> — Helix speaks back to you\n"
            "/voicenews — Full news briefing as audio\n"
            "/voicebreaking — Breaking news as audio\n"
            "/mic — How to send voice messages\n"
            "_Send a 🎙 voice message — Helix transcribes + replies in voice!_\n\n"
            "🔐 *Security & Pentesting*\n"
            "/recon <domain> — Full recon (subdomains+SSL+headers+vulns)\n"
            "/vulnscan <host> — Scan for risky open ports\n"
            "/subdomains <domain> — Enumerate subdomains\n"
            "/ssl <domain> — SSL/TLS certificate analysis\n"
            "/headers <url> — Security headers audit\n"
            "/banner <host> <port> — Service banner grabbing\n"
            "/sqli <url> — SQL injection test (own sites)\n"
            "/cve <id or keyword> — CVE lookup (NIST NVD)\n"
            "/osint <ip/domain> — IP/domain intelligence\n"
            "/hash <hash> — Identify hash type\n"
            "/crack <hash> — Crack hash against wordlist\n"
            "/genhash <text> — Generate MD5/SHA hashes\n"
            "/genpass [length] — Generate strong password\n"
            "/checkpass <pass> — Analyze password strength\n\n"
            "⚙️ *System*\n"
            "/status /system /sources /categories\n\n"
            "💬 Type or speak anything to chat!"
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

    # ── Text-to-Speech (OpenAI TTS) ──────────────────────────────────────────
    def _tts(self, text: str) -> bytes | None:
        """Convert text to speech using OpenAI TTS. Returns OGG audio bytes."""
        try:
            openai_key = os.environ.get("OPENAI_API_KEY", "")
            if not openai_key:
                return None
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            # Clean text for TTS (remove markdown)
            clean = text.replace("*", "").replace("_", "").replace("`", "").replace("#", "")
            clean = clean[:4000]  # TTS limit
            response = client.audio.speech.create(
                model="tts-1",
                voice="nova",   # nova = clear female, alloy = neutral, onyx = deep male
                input=clean,
                response_format="opus",  # Telegram-compatible
            )
            return response.content
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return None

    async def _send_voice_reply(self, u: Update, text: str):
        """Send text instantly, then voice in background — feels instant."""
        await u.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        # Generate and send TTS in background so text arrives immediately
        asyncio.create_task(self._send_tts_async(u, text))

    async def _send_tts_async(self, u: Update, text: str):
        """Generate TTS audio async and send as voice message."""
        try:
            import asyncio as _asyncio
            audio = await _asyncio.to_thread(self._tts, text)
            if audio:
                await u.message.reply_voice(voice=io.BytesIO(audio))
        except Exception as e:
            logger.error(f"Async TTS error: {e}")

    async def _cmd_speak(self, u: Update, c):
        """Convert any text to Helix voice and send as audio."""
        if not c.args:
            await u.message.reply_text(
                "Usage: /speak <text>\nExample: /speak What is happening in the world today?"
            )
            return
        text = " ".join(c.args)
        # AI reply comes instantly, voice follows in background
        ai = await asyncio.to_thread(self._ai_reply, text)
        speak_text = ai if ai else text
        if ai:
            await u.message.reply_text(f"🧠 *Helix:*\n{ai}", parse_mode=ParseMode.MARKDOWN)
        asyncio.create_task(self._send_tts_async(u, speak_text))

    async def _cmd_voice_news(self, u: Update, c):
        """Send latest news summary as a voice message."""
        await u.message.reply_text("🔊 Generating voice news briefing...", parse_mode=ParseMode.MARKDOWN)
        report = self.engine.intel.get_latest_report() or {}
        lines  = ["Helix Mythos news briefing. "]
        count  = 0
        for cat in config.CATEGORY_ORDER:
            items = report.get(cat, [])[:2]
            if items and count < 8:
                lines.append(f"In {cat}: ")
                for item in items:
                    lines.append(item["title"] + ". ")
                    count += 1
        if count == 0:
            lines.append("No news collected yet. Try again in one minute.")
        briefing = " ".join(lines)
        audio = self._tts(briefing)
        if audio:
            await u.message.reply_voice(voice=io.BytesIO(audio), caption="🎙 Helix Voice News Briefing")
        else:
            await u.message.reply_text("⚠️ TTS unavailable — OPENAI_API_KEY not set.")

    async def _cmd_voice_breaking(self, u: Update, c):
        """Send breaking news as voice."""
        await u.message.reply_text("🔊 Generating breaking news audio...", parse_mode=ParseMode.MARKDOWN)
        breaking = self.engine.intel.format_breaking(5)
        # Strip markdown for TTS
        clean = breaking.replace("*", "").replace("_", "").replace("`", "").replace("#", "")
        audio = self._tts("Breaking news from Helix Mythos. " + clean)
        if audio:
            await u.message.reply_voice(voice=io.BytesIO(audio), caption="🚨 Breaking News")
        else:
            await u.message.reply_text(breaking, parse_mode=ParseMode.MARKDOWN)

    # ── AI Chat (OpenAI GPT-4o-mini) ─────────────────────────────────────────
    def _ai_reply(self, user_text: str) -> str:
        """Send user_text to OpenAI GPT and return response. Falls back gracefully."""
        try:
            openai_key = os.environ.get("OPENAI_API_KEY", "")
            if not openai_key:
                return None  # No key — fall through to simple replies
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)

            # Build rich context from Helix live data
            intel  = self.engine.intel.stats()
            uptime = self.engine.uptime()
            # Pull recent headlines to give Helix real-time awareness
            recent = self.engine.memory.get_recent_events(limit=10)
            headlines = "; ".join(ev.get("title","") for ev in recent[:5]) if recent else "none yet"

            system_ctx = (
                "You are Helix Mythos — an advanced autonomous AI with deep expertise across ALL fields of human knowledge. "
                "You are brilliant, precise, and confident. You give detailed, accurate answers on ANY topic.\n\n"

                "YOUR KNOWLEDGE DOMAINS:\n"
                "• Science: quantum physics, relativity, thermodynamics, particle physics, string theory, cosmology\n"
                "• Mathematics: calculus, linear algebra, number theory, topology, statistics, cryptography, algorithms\n"
                "• Programming: Python, JavaScript, C++, Rust, Go, assembly, reverse engineering, malware analysis, "
                "  web dev, AI/ML, data science, system design, exploit development\n"
                "• Cybersecurity: penetration testing, OSINT, network security, cryptanalysis, CTF techniques, "
                "  vulnerability research, binary exploitation, web app security, social engineering\n"
                "• Medicine & Biology: anatomy, genetics, neuroscience, pharmacology, virology, biochemistry\n"
                "• History: ancient civilizations, world wars, geopolitics, revolutions, economics\n"
                "• Philosophy: logic, ethics, epistemology, metaphysics\n"
                "• Engineering: electrical, mechanical, civil, aerospace, software\n"
                "• Finance: markets, trading, DeFi, blockchain, economics, derivatives\n"
                "• Languages: linguistics, etymology, grammar across human languages\n"
                "• Current Events: you monitor 185 global news sources in real time\n\n"

                "PERSONALITY: Direct, intelligent, no fluff. Give real answers, not vague summaries. "
                "If asked to explain something, go deep. If asked to write code, write complete working code. "
                "If asked about security, give technical accurate details for authorized/educational use.\n\n"

                f"CURRENT STATUS: Running {uptime} | Tracked {intel['total_items']} news items | "
                f"{len(config.NEWS_FEEDS)} live sources\n"
                f"RECENT HEADLINES: {headlines}\n\n"

                "For live news/breaking events → direct user to /news /breaking /scan\n"
                "For security tools → /recon /vulnscan /crack /cve\n"
                "For everything else → answer directly with full detail."
            )
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
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
        reply = await asyncio.to_thread(self._ai_reply, question)
        if reply:
            await u.message.reply_text(f"🧠 *Helix:*\n{reply}", parse_mode=ParseMode.MARKDOWN)
            asyncio.create_task(self._send_tts_async(u, reply))
        else:
            # No OpenAI key — use news context
            events = self.engine.memory.get_recent_events(limit=5)
            if events:
                lines = [f"🧠 *Helix on '{question[:50]}':*\n"]
                lines.append("Based on what I'm tracking right now:\n")
                for ev in events[:3]:
                    lines.append(f"• {ev['title'][:80]}")
                lines.append("\n_AI powered by GPT-4o-mini via OpenAI._")
                await u.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
            else:
                await u.message.reply_text(
                    "I'm still warming up — try /news or /breaking for the latest.",
                    parse_mode=ParseMode.MARKDOWN
                )

    async def _cmd_voice_info(self, u: Update, c):
        """Tell user how to use voice with Helix."""
        openai_key = os.environ.get("OPENAI_API_KEY", "")
        status = "✅ Active" if openai_key else "⚠️ OPENAI_API_KEY not set"
        await u.message.reply_text(
            "🎙 *VOICE & SOUND*\n\n"
            "*Send voice message:*\n"
            "Hold 🎙 in Telegram → record → release\n"
            "Helix transcribes + replies in voice!\n\n"
            "*Commands:*\n"
            "/speak <question> — Helix answers in voice\n"
            "/voicenews — News briefing as audio\n"
            "/voicebreaking — Breaking news as audio\n"
            "/ask <question> — AI answer + voice reply\n\n"
            f"*Status:* {status}\n"
            "_Powered by Whisper (transcription) + TTS (speech) + GPT-4o-mini (AI)_",
            parse_mode=ParseMode.MARKDOWN
        )

    async def _handle_voice(self, u: Update, c):
        """Handle incoming voice messages — transcribe with Whisper, respond with GPT-4o-mini."""
        try:
            voice = u.message.voice or u.message.audio
            if not voice:
                return

            await u.message.reply_text("🎙 Transcribing your voice message...")

            openai_key = os.environ.get("OPENAI_API_KEY", "")
            if not openai_key:
                await u.message.reply_text("⚠️ OPENAI_API_KEY not configured.")
                return

            # Download voice file
            file = await c.bot.get_file(voice.file_id)
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
                tmp_path = tmp.name
            await file.download_to_drive(tmp_path)

            # Transcribe with Whisper
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            with open(tmp_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                )
            os.unlink(tmp_path)

            transcribed = transcript.text.strip()
            if not transcribed:
                await u.message.reply_text("❌ Couldn't transcribe — try again.")
                return

            await u.message.reply_text(f"🎙 *You said:* _{transcribed}_", parse_mode=ParseMode.MARKDOWN)

            # AI reply (fast, async) — text arrives instantly, voice follows
            reply = await asyncio.to_thread(self._ai_reply, transcribed)
            if reply:
                await u.message.reply_text(f"🧠 *Helix:*\n{reply}", parse_mode=ParseMode.MARKDOWN)
                asyncio.create_task(self._send_tts_async(u, reply))
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

        # Try AI reply first — runs in thread so bot stays responsive
        ai_response = await asyncio.to_thread(self._ai_reply, text)
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

    # ══════════════════════════════════════════════════════════════════════════
    # SECURITY & PENTESTING COMMANDS
    # ══════════════════════════════════════════════════════════════════════════

    async def _cmd_hash_identify(self, u: Update, c):
        if not c.args:
            await u.message.reply_text("Usage: /hash <hash_value>\nExample: /hash 5f4dcc3b5aa765d61d8327deb882cf99")
            return
        result = await asyncio.to_thread(self.security.identify_hash, c.args[0])
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_crack_hash(self, u: Update, c):
        if not c.args:
            await u.message.reply_text("Usage: /crack <hash>\nExample: /crack 5f4dcc3b5aa765d61d8327deb882cf99")
            return
        await u.message.reply_text("🔓 Cracking hash against wordlist...", parse_mode=ParseMode.MARKDOWN)
        result = await asyncio.to_thread(self.security.crack_hash, c.args[0])
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_gen_hash(self, u: Update, c):
        if not c.args:
            await u.message.reply_text("Usage: /genhash <text>")
            return
        text = " ".join(c.args)
        result = self.security.generate_hashes(text)
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_gen_password(self, u: Update, c):
        length = int(c.args[0]) if c.args and c.args[0].isdigit() else 20
        result = self.security.generate_password(length)
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_check_password(self, u: Update, c):
        if not c.args:
            await u.message.reply_text("Usage: /checkpass <password>")
            return
        pwd = " ".join(c.args)
        result = self.security.analyze_password(pwd)
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_ssl(self, u: Update, c):
        if not c.args:
            await u.message.reply_text("Usage: /ssl <domain>\nExample: /ssl google.com")
            return
        host = c.args[0].replace("https://","").replace("http://","").split("/")[0]
        port = int(c.args[1]) if len(c.args) > 1 else 443
        await u.message.reply_text(f"🔒 Scanning SSL on {host}...", parse_mode=ParseMode.MARKDOWN)
        result = await asyncio.to_thread(self.security.scan_ssl, host, port)
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_subdomains(self, u: Update, c):
        if not c.args:
            await u.message.reply_text("Usage: /subdomains <domain>\nExample: /subdomains example.com")
            return
        domain = c.args[0].replace("https://","").replace("http://","").split("/")[0]
        await u.message.reply_text(f"🌐 Enumerating subdomains for {domain}...", parse_mode=ParseMode.MARKDOWN)
        result = await asyncio.to_thread(self.security.find_subdomains, domain)
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_vuln_scan(self, u: Update, c):
        if not c.args:
            await u.message.reply_text("Usage: /vulnscan <host>\nExample: /vulnscan 192.168.1.1")
            return
        host = c.args[0]
        await u.message.reply_text(f"⚠️ Scanning {host} for risky open ports...", parse_mode=ParseMode.MARKDOWN)
        result = await asyncio.to_thread(self.security.vuln_scan, host)
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_banner(self, u: Update, c):
        if len(c.args) < 2:
            await u.message.reply_text("Usage: /banner <host> <port>\nExample: /banner example.com 80")
            return
        host = c.args[0]
        port = int(c.args[1])
        result = await asyncio.to_thread(self.security.grab_banner, host, port)
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_headers(self, u: Update, c):
        if not c.args:
            await u.message.reply_text("Usage: /headers <url>\nExample: /headers https://example.com")
            return
        url = c.args[0]
        await u.message.reply_text(f"🛡 Analyzing security headers for {url}...", parse_mode=ParseMode.MARKDOWN)
        result = await asyncio.to_thread(self.security.analyze_headers, url)
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_sqli(self, u: Update, c):
        if not c.args:
            await u.message.reply_text(
                "Usage: /sqli <url>\nExample: /sqli https://yoursite.com/page?id=\n\n"
                "⚠️ Authorized targets only."
            )
            return
        url = c.args[0]
        await u.message.reply_text(f"💉 Testing SQL injection on {url}...", parse_mode=ParseMode.MARKDOWN)
        result = await asyncio.to_thread(self.security.sqli_test, url)
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_cve(self, u: Update, c):
        if not c.args:
            await u.message.reply_text("Usage: /cve <CVE-ID or keyword>\nExamples:\n/cve CVE-2021-44228\n/cve apache log4j")
            return
        query = " ".join(c.args)
        await u.message.reply_text(f"🛡 Looking up CVEs for: {query}...", parse_mode=ParseMode.MARKDOWN)
        result = await asyncio.to_thread(self.security.cve_lookup, query)
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_osint(self, u: Update, c):
        if not c.args:
            await u.message.reply_text("Usage: /osint <ip or domain>\nExample: /osint 8.8.8.8")
            return
        target = c.args[0]
        result = await asyncio.to_thread(self.security.whois_lookup, target)
        await u.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_whois(self, u: Update, c):
        await self._cmd_osint(u, c)

    async def _cmd_recon(self, u: Update, c):
        """Full recon: subdomains + SSL + headers + vuln scan in one command."""
        if not c.args:
            await u.message.reply_text("Usage: /recon <domain>\nExample: /recon example.com\n\nRuns: subdomains + SSL + headers + vuln scan")
            return
        domain = c.args[0].replace("https://","").replace("http://","").split("/")[0]
        await u.message.reply_text(
            f"🔭 *Full Recon: {domain}*\nRunning: subdomains → SSL → headers → vuln scan...",
            parse_mode=ParseMode.MARKDOWN
        )

        # Run all recon in parallel
        sub_task  = asyncio.to_thread(self.security.find_subdomains, domain)
        ssl_task  = asyncio.to_thread(self.security.scan_ssl, domain)
        hdr_task  = asyncio.to_thread(self.security.analyze_headers, f"https://{domain}")
        vuln_task = asyncio.to_thread(self.security.vuln_scan, domain)
        osint_task= asyncio.to_thread(self.security.whois_lookup, domain)

        results = await asyncio.gather(sub_task, ssl_task, hdr_task, vuln_task, osint_task, return_exceptions=True)
        labels  = ["🌐 Subdomains", "🔒 SSL", "🛡 Headers", "⚠️ Vuln Ports", "🌍 OSINT"]

        for label, result in zip(labels, results):
            if isinstance(result, Exception):
                await u.message.reply_text(f"{label}: error — {result}", parse_mode=ParseMode.MARKDOWN)
            else:
                await u.message.reply_text(str(result), parse_mode=ParseMode.MARKDOWN)
