"""
Helix Mythos — MAXIMUM Intelligence Engine
150+ sources · 17 categories · Runs every 60 seconds
World News · Geopolitics · Military · Finance · Crypto · Science ·
AI/Tech · Space · Health · Climate · Energy · Disasters · Research · Culture
"""

import time
import logging
import threading
import hashlib
from datetime import datetime
from pathlib import Path
from collections import defaultdict

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import config

logger = logging.getLogger("HelixIntelligence")


class GlobalIntelligence:
    def __init__(self, memory, notify_callback=None):
        self.memory        = memory
        self.notify        = notify_callback
        self._running      = False
        self._thread       = None
        self._seen         = set()
        self._report_cache = {}
        self._scan_count   = 0
        self._total_items  = 0

        # Per-category storage: category -> list of recent items
        self._category_items: dict[str, list] = defaultdict(list)

    # ── Public API ────────────────────────────────────────────────────────────
    def start(self):
        self._running = True
        self._thread  = threading.Thread(
            target=self._loop, daemon=True, name="Intelligence"
        )
        self._thread.start()
        logger.info(f"Intelligence Engine started — {len(config.NEWS_FEEDS)} sources active.")

    def stop(self):
        self._running = False

    def get_latest_report(self):
        return self._report_cache.copy()

    def get_category(self, cat: str, limit: int = 10):
        return self._category_items.get(cat, [])[:limit]

    def fetch_now(self):
        return self._scan_all()

    # ── Internal loop ─────────────────────────────────────────────────────────
    def _loop(self):
        while self._running:
            try:
                self._scan_all()
            except Exception as e:
                logger.error(f"Intelligence scan error: {e}")
            time.sleep(config.FAST_INTERVAL_SECONDS)   # Every 60 seconds

    def _scan_all(self):
        try:
            import feedparser
        except ImportError:
            logger.error("feedparser not installed. Run: pip install feedparser")
            return {}

        self._scan_count += 1
        logger.info(f"Intelligence scan #{self._scan_count} — scanning {len(config.NEWS_FEEDS)} sources...")

        # Build report structure
        report = {cat: [] for cat in config.CATEGORY_ORDER}
        report["ts"]      = datetime.utcnow().isoformat()
        report["scan_no"] = self._scan_count
        new_items = 0

        # Scan all feeds in parallel using threads
        results_lock = threading.Lock()
        threads      = []

        def scan_feed(label, cat, url):
            nonlocal new_items
            try:
                feed = feedparser.parse(url)
                items = []
                for entry in feed.entries[:8]:
                    title   = entry.get("title", "").strip()
                    link    = entry.get("link", "")
                    summary = (entry.get("summary", "") or
                               entry.get("description", ""))[:400]

                    if not title:
                        continue

                    # Dedup by hash
                    key = hashlib.md5(title.encode()).hexdigest()
                    if key in self._seen:
                        continue
                    self._seen.add(key)

                    item = {
                        "title":    title,
                        "source":   label,
                        "category": cat,
                        "url":      link,
                        "summary":  summary,
                        "ts":       datetime.utcnow().isoformat(),
                    }
                    items.append(item)

                if items:
                    with results_lock:
                        for item in items:
                            if cat in report:
                                report[cat].append(item)
                            else:
                                report["World"].append(item)
                            self._category_items[cat] = (
                                items + self._category_items[cat]
                            )[:100]   # Keep 100 per category
                            new_items += 1

                            # Persist to memory
                            self.memory.store_event(
                                item["title"], cat, label,
                                item["url"], item["summary"]
                            )
                            self.memory.learn_fact(
                                f"[{cat}] {item['title']}", confidence=0.75
                            )
            except Exception as e:
                logger.debug(f"Feed error [{label}]: {e}")

        for cat, label, url in config.NEWS_FEEDS:
            t = threading.Thread(target=scan_feed, args=(label, cat, url), daemon=True)
            threads.append(t)
            t.start()

        # Wait for all feeds (max 30 seconds)
        for t in threads:
            t.join(timeout=30)

        self._total_items += new_items
        self._report_cache = report
        self._trim_seen()

        logger.info(
            f"Scan #{self._scan_count} complete — {new_items} new items "
            f"| Total: {self._total_items}"
        )

        # Log to memory
        self.memory.append_log({
            "event":      "intelligence_scan",
            "scan_no":    self._scan_count,
            "new_items":  new_items,
            "total":      self._total_items,
        })
        self.memory.store("intelligence", "last_scan",
                          datetime.utcnow().isoformat(), "GlobalIntelligence")
        self.memory.store("intelligence", "total_items",
                          str(self._total_items), "GlobalIntelligence")

        return report

    def _trim_seen(self):
        if len(self._seen) > 20000:
            lst = list(self._seen)
            self._seen = set(lst[-10000:])

    # ── Formatted reports ─────────────────────────────────────────────────────
    def format_report(self, report: dict = None, max_per_cat: int = 4) -> str:
        if report is None:
            report = self._report_cache
        ts      = report.get("ts", datetime.utcnow().isoformat())
        scan_no = report.get("scan_no", self._scan_count)

        lines = [
            f"🌐 *HELIX MYTHOS — GLOBAL INTELLIGENCE REPORT*",
            f"🔍 Scan #{scan_no} | 🕐 `{ts[:19].replace('T',' ')} UTC`",
            f"📡 `{len(config.NEWS_FEEDS)} sources monitored continuously`",
            "━" * 35,
        ]

        total_shown = 0
        for cat in config.CATEGORY_ORDER:
            items = report.get(cat, [])[:max_per_cat]
            if not items:
                continue
            emoji = config.CATEGORY_EMOJI.get(cat, "📌")
            lines.append(f"\n{emoji} *{cat.upper()}*")
            for item in items:
                title = item["title"][:75]
                src   = item["source"]
                lines.append(f"• {title} _({src})_")
                total_shown += 1

        lines.append(f"\n━" + "━" * 34)
        lines.append(
            f"📊 *{total_shown} new events this cycle*"
        )
        lines.append(
            f"🗄️ Total tracked: *{self._total_items}* items"
        )
        lines.append(f"⏱ Next scan in {config.FAST_INTERVAL_SECONDS}s")
        lines.append(f"🧠 _{config.HELIX_MOTTO}_")

        return "\n".join(lines)

    def format_category(self, cat: str, limit: int = 10) -> str:
        """Detailed report for one specific category."""
        items = self.get_category(cat, limit)
        emoji = config.CATEGORY_EMOJI.get(cat, "📌")
        if not items:
            return f"{emoji} No data yet for category: {cat}"

        lines = [
            f"{emoji} *{cat.upper()} — DETAILED REPORT*",
            f"🕐 `{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}`",
            "━" * 35,
        ]
        for i, item in enumerate(items, 1):
            lines.append(f"\n*{i}. {item['title'][:80]}*")
            lines.append(f"   📰 {item['source']}")
            if item.get("summary"):
                lines.append(f"   _{item['summary'][:150]}_")
        return "\n".join(lines)

    def format_breaking(self, max_items: int = 5) -> str:
        """Only the most critical / breaking news across all categories."""
        all_items = []
        for cat in ["World", "Geopolitics", "Military", "Disasters"]:
            for item in self._category_items.get(cat, [])[:3]:
                all_items.append((cat, item))

        if not all_items:
            return "No breaking news at this time."

        lines = ["🔴 *BREAKING — TOP STORIES*", "━" * 35]
        for cat, item in all_items[:max_items]:
            emoji = config.CATEGORY_EMOJI.get(cat, "📌")
            lines.append(f"\n{emoji} *{item['title'][:80]}*")
            lines.append(f"   _{item['source']}_")
        return "\n".join(lines)

    # ── Stats ─────────────────────────────────────────────────────────────────
    def stats(self) -> dict:
        cat_counts = {
            cat: len(self._category_items.get(cat, []))
            for cat in config.CATEGORY_ORDER
        }
        return {
            "scan_count":  self._scan_count,
            "total_items": self._total_items,
            "sources":     len(config.NEWS_FEEDS),
            "categories":  cat_counts,
        }
