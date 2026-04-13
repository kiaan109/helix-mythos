"""
Helix Mythos — Memory System
Dual-layer memory: SQLite (structured) + JSON (episodic log)
"""

import sqlite3
import json
import os
import time
import logging
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import config

logger = logging.getLogger("HelixMemory")


class MemorySystem:
    def __init__(self):
        self.db_path  = config.DB_PATH
        self.log_path = config.LOG_PATH
        self._init_db()
        self._init_log()

    # ── SQLite layer ──────────────────────────────────────────────────────────
    def _init_db(self):
        conn = self._conn()
        cur  = conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS knowledge (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                category  TEXT NOT NULL,
                key       TEXT NOT NULL,
                value     TEXT NOT NULL,
                source    TEXT,
                ts        REAL DEFAULT (strftime('%s','now')),
                UNIQUE(category, key)
            );
            CREATE TABLE IF NOT EXISTS events (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                title     TEXT NOT NULL,
                category  TEXT,
                source    TEXT,
                url       TEXT,
                summary   TEXT,
                ts        REAL DEFAULT (strftime('%s','now'))
            );
            CREATE TABLE IF NOT EXISTS decisions (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                agent     TEXT,
                action    TEXT,
                outcome   TEXT,
                score     REAL,
                ts        REAL DEFAULT (strftime('%s','now'))
            );
            CREATE TABLE IF NOT EXISTS learned_facts (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                fact      TEXT UNIQUE,
                confidence REAL DEFAULT 0.5,
                ts        REAL DEFAULT (strftime('%s','now'))
            );
        """)
        conn.commit()
        conn.close()

    def _conn(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    # ── Knowledge CRUD ────────────────────────────────────────────────────────
    def store(self, category: str, key: str, value, source: str = ""):
        conn = self._conn()
        conn.execute(
            "INSERT OR REPLACE INTO knowledge (category, key, value, source) VALUES (?,?,?,?)",
            (category, key, str(value), source)
        )
        conn.commit()
        conn.close()

    def retrieve(self, category: str, key: str):
        conn = self._conn()
        row = conn.execute(
            "SELECT value FROM knowledge WHERE category=? AND key=?",
            (category, key)
        ).fetchone()
        conn.close()
        return row[0] if row else None

    def retrieve_all(self, category: str):
        conn = self._conn()
        rows = conn.execute(
            "SELECT key, value, source, ts FROM knowledge WHERE category=? ORDER BY ts DESC",
            (category,)
        ).fetchall()
        conn.close()
        return [{"key": r[0], "value": r[1], "source": r[2], "ts": r[3]} for r in rows]

    # ── Event storage ─────────────────────────────────────────────────────────
    def store_event(self, title: str, category: str, source: str, url: str, summary: str):
        conn = self._conn()
        # Avoid duplicates
        exists = conn.execute("SELECT id FROM events WHERE title=?", (title,)).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO events (title, category, source, url, summary) VALUES (?,?,?,?,?)",
                (title, category, source, url, summary)
            )
            conn.commit()
        conn.close()

    def get_recent_events(self, limit: int = 20, category: str = None):
        conn  = self._conn()
        query = "SELECT title, category, source, url, summary, ts FROM events"
        args  = []
        if category:
            query += " WHERE category=?"
            args.append(category)
        query += " ORDER BY ts DESC LIMIT ?"
        args.append(limit)
        rows = conn.execute(query, args).fetchall()
        conn.close()
        return [{"title": r[0], "category": r[1], "source": r[2],
                 "url": r[3], "summary": r[4], "ts": r[5]} for r in rows]

    # ── Decisions ─────────────────────────────────────────────────────────────
    def log_decision(self, agent: str, action: str, outcome: str, score: float = 0.5):
        conn = self._conn()
        conn.execute(
            "INSERT INTO decisions (agent, action, outcome, score) VALUES (?,?,?,?)",
            (agent, action, outcome, score)
        )
        conn.commit()
        conn.close()

    def get_decisions(self, limit: int = 50):
        conn  = self._conn()
        rows  = conn.execute(
            "SELECT agent, action, outcome, score, ts FROM decisions ORDER BY ts DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
        return [{"agent": r[0], "action": r[1], "outcome": r[2],
                 "score": r[3], "ts": r[4]} for r in rows]

    # ── Learned facts ─────────────────────────────────────────────────────────
    def learn_fact(self, fact: str, confidence: float = 0.7):
        conn = self._conn()
        conn.execute(
            "INSERT OR REPLACE INTO learned_facts (fact, confidence) VALUES (?,?)",
            (fact, confidence)
        )
        conn.commit()
        conn.close()

    def get_facts(self, limit: int = 30):
        conn = self._conn()
        rows = conn.execute(
            "SELECT fact, confidence, ts FROM learned_facts ORDER BY confidence DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
        return [{"fact": r[0], "confidence": r[1], "ts": r[2]} for r in rows]

    # ── Episodic JSON log ─────────────────────────────────────────────────────
    def _init_log(self):
        if not os.path.exists(self.log_path):
            with open(self.log_path, "w") as f:
                json.dump([], f)

    def append_log(self, entry: dict):
        try:
            with open(self.log_path, "r") as f:
                log = json.load(f)
        except Exception:
            log = []
        entry["timestamp"] = datetime.utcnow().isoformat()
        log.append(entry)
        # Keep last 1000 entries
        log = log[-1000:]
        with open(self.log_path, "w") as f:
            json.dump(log, f, indent=2)

    def read_log(self, limit: int = 50):
        try:
            with open(self.log_path, "r") as f:
                log = json.load(f)
            return log[-limit:]
        except Exception:
            return []

    # ── Stats ─────────────────────────────────────────────────────────────────
    def stats(self):
        conn  = self._conn()
        kc    = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
        ec    = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        dc    = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
        fc    = conn.execute("SELECT COUNT(*) FROM learned_facts").fetchone()[0]
        conn.close()
        return {"knowledge": kc, "events": ec, "decisions": dc, "facts": fc}
