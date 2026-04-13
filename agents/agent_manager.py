"""
Helix Mythos — Multi-Agent Manager
7 agents: Planner · Research · Coding · Vision · Learning · Automation · Intelligence
"""

import logging
import threading
import time
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import config

logger = logging.getLogger("HelixAgents")


class BaseAgent:
    def __init__(self, name, memory, description=""):
        self.name        = name
        self.memory      = memory
        self.description = description
        self.status      = "idle"
        self.last_run    = None
        self.task_count  = 0
        self._log        = []

    def run_task(self, task: str) -> str:
        self.status      = "running"
        self.task_count += 1
        start = time.time()
        try:
            result = self._execute(task)
            self.status = "idle"
        except Exception as e:
            result = f"Error: {e}"
            self.status = "error"
        elapsed       = round(time.time() - start, 3)
        self.last_run = datetime.utcnow().isoformat()
        self._log.append({"task": task, "result": result[:200], "elapsed": elapsed, "ts": self.last_run})
        self._log = self._log[-20:]
        self.memory.log_decision(self.name, task, result[:100], 0.7)
        return result

    def _execute(self, task: str) -> str:
        raise NotImplementedError

    def info(self) -> dict:
        return {"name": self.name, "status": self.status,
                "tasks_run": self.task_count, "last_run": self.last_run,
                "description": self.description}


# ── Planner ───────────────────────────────────────────────────────────────────
class PlannerAgent(BaseAgent):
    def __init__(self, memory):
        super().__init__("PlannerAgent", memory, "Breaks goals into actionable task sequences")
        self._plans = []

    def _execute(self, task: str) -> str:
        plan = [
            f"1. Analyse: {task}",
            "2. Gather data from intelligence feed",
            "3. Cross-reference memory for related knowledge",
            "4. Formulate action steps",
            "5. Delegate to specialist agents",
            "6. Monitor outcomes & reinforce learning",
        ]
        plan_str = "\n".join(plan)
        self.memory.store("plans", task[:50], plan_str, "PlannerAgent")
        return f"Plan created:\n{plan_str}"


# ── Research ──────────────────────────────────────────────────────────────────
class ResearchAgent(BaseAgent):
    def __init__(self, memory):
        super().__init__("ResearchAgent", memory, "Searches internet and synthesizes information")

    def _execute(self, task: str) -> str:
        try:
            import requests
            from bs4 import BeautifulSoup
            query   = task.replace(" ", "+")
            url     = f"https://duckduckgo.com/html/?q={query}"
            headers = {"User-Agent": "Mozilla/5.0 HelixMythos/2.0"}
            resp    = requests.get(url, headers=headers, timeout=10)
            soup    = BeautifulSoup(resp.text, "html.parser")
            results = soup.select(".result__snippet")[:5]
            snippets = [r.get_text(strip=True) for r in results]
            if snippets:
                combined = " | ".join(snippets[:3])
                self.memory.learn_fact(f"Research [{task[:40]}]: {combined[:150]}", confidence=0.65)
                return f"Research on '{task}':\n" + "\n".join(f"• {s[:150]}" for s in snippets)
            return f"No results found for: {task}"
        except Exception as e:
            return f"Research failed: {e}"


# ── Coding ────────────────────────────────────────────────────────────────────
class CodingAgent(BaseAgent):
    def __init__(self, memory, sandbox):
        super().__init__("CodingAgent", memory,
                         "Generates, tests, and runs code experiments")
        self.sandbox = sandbox

    def _execute(self, task: str) -> str:
        code_map = {
            "prime":     "primes=[x for x in range(2,50) if all(x%i for i in range(2,x))]\nprint(primes)",
            "fibonacci": "a,b=0,1\nseq=[]\nfor _ in range(10): seq.append(a); a,b=b,a+b\nprint(seq)",
            "sort":      "import random\nd=random.sample(range(100),10)\nprint(f'Unsorted: {d}')\nd.sort()\nprint(f'Sorted: {d}')",
            "stats":     "import numpy as np\nd=np.random.randn(100)\nprint(f'Mean={d.mean():.3f} Std={d.std():.3f} Max={d.max():.3f}')",
            "hash":      "import hashlib\nfor algo in ['md5','sha256','sha512']:\n    h=hashlib.new(algo,b'HelixMythos').hexdigest()\n    print(f'{algo}: {h}')",
            "encode":    "import base64\nmsg=b'Helix Mythos'\nenc=base64.b64encode(msg)\nprint(f'Base64: {enc}')\nprint(f'Decoded: {base64.b64decode(enc)}')",
            "network":   "import socket\nip=socket.gethostbyname(socket.gethostname())\nprint(f'Host IP: {ip}')\nprint(f'Hostname: {socket.gethostname()}')",
        }
        t    = task.lower()
        code = next((v for k, v in code_map.items() if k in t),
                    f"print('CodingAgent task: {task}')")
        result = self.sandbox.run_experiment(code)
        return self.sandbox.format_result(result)


# ── Vision ────────────────────────────────────────────────────────────────────
class VisionAgent(BaseAgent):
    def __init__(self, memory, vision_engine):
        super().__init__("VisionAgent", memory,
                         "YOLO object detection · face recognition · motion · OCR · scene analysis")
        self.vision = vision_engine

    def _execute(self, task: str) -> str:
        t = task.lower()
        if "screenshot" in t or "screen" in t or "ocr" in t:
            data = self.vision.capture_screenshot()
            if data:
                return f"Screenshot captured ({len(data)//1024} KB) with OCR annotations."
            return "Screenshot not available."
        if "ocr" in t or "text" in t or "read" in t:
            return self.vision.get_ocr_text()
        # Default: camera snapshot
        data = self.vision.capture_frame()
        if data:
            stats = self.vision.stats()
            return (
                f"Camera frame captured ({len(data)//1024} KB)\n"
                f"YOLO: {'active' if stats['yolo_available'] else 'using Haar fallback'}\n"
                f"FPS: {stats['fps']}"
            )
        return "Camera not available."


# ── Learning ──────────────────────────────────────────────────────────────────
class LearningAgentWrapper(BaseAgent):
    def __init__(self, memory, learning_engine):
        super().__init__("LearningAgent", memory,
                         "Ensemble ML · topic modeling · clustering · anomaly detection · knowledge graph")
        self.engine = learning_engine

    def _execute(self, task: str) -> str:
        t = task.lower()
        if "topic" in t:
            topics = self.engine.get_topics(6)
            if not topics:
                return "No topics extracted yet."
            return "Topics:\n" + "\n".join(
                f"Topic {tp['topic_id']}: {', '.join(tp['words'][:5])}" for tp in topics
            )
        if "trend" in t:
            trends = self.engine.get_trends(8)
            lines  = ["Rising: " + ", ".join(w for w,_,_ in trends["rising"][:5])]
            lines += ["Falling: " + ", ".join(w for w,_,_ in trends["falling"][:5])]
            return "\n".join(lines)
        if "anomal" in t:
            anomalies = self.engine.get_anomalies(5)
            return "Anomalies:\n" + "\n".join(anomalies) if anomalies else "No anomalies detected."
        if "entity" in t or "entities" in t:
            entities = self.engine.get_entities()
            return str(entities)[:500]
        if "summary" in t or "summarize" in t:
            return self.engine.summarize(n_sentences=4)
        return self.engine.format_report()


# ── Automation ────────────────────────────────────────────────────────────────
class AutomationAgent(BaseAgent):
    def __init__(self, memory):
        super().__init__("AutomationAgent", memory,
                         "System health monitoring · process management · resource tracking")

    def _execute(self, task: str) -> str:
        try:
            import psutil
            cpu   = psutil.cpu_percent(interval=1)
            mem   = psutil.virtual_memory()
            disk  = psutil.disk_usage("/")
            procs = [(p.info["name"], p.info["cpu_percent"])
                     for p in psutil.process_iter(["name", "cpu_percent"])
                     if p.info["cpu_percent"] > 1.0][:5]
            top_procs = "\n".join(f"  {n}: {c:.1f}%" for n, c in sorted(procs, key=lambda x: -x[1]))
            report = (
                f"⚙️ *System Health*\n"
                f"CPU: {cpu:.1f}% | RAM: {mem.percent:.1f}% ({mem.used//1024//1024} MB used)\n"
                f"Disk: {disk.percent:.1f}% ({disk.free//1024//1024//1024} GB free)\n"
                f"Top processes:\n{top_procs or '  All idle'}"
            )
            self.memory.store("system", "cpu",  str(cpu), "AutomationAgent")
            self.memory.store("system", "ram",  str(mem.percent), "AutomationAgent")
            self.memory.store("system", "disk", str(disk.percent), "AutomationAgent")
            return report
        except Exception as e:
            return f"System check failed: {e}"


# ── Intelligence ──────────────────────────────────────────────────────────────
class IntelligenceAgent(BaseAgent):
    def __init__(self, memory, intel_engine):
        super().__init__("IntelligenceAgent", memory,
                         "Scans and synthesizes global intelligence across 150+ sources")
        self.intel = intel_engine

    def _execute(self, task: str) -> str:
        t = task.lower()
        for cat in config.CATEGORY_ORDER:
            if cat.lower() in t:
                return self.intel.format_category(cat, limit=5)
        report = self.intel.fetch_now()
        return self.intel.format_report(report, max_per_cat=2)


# ── Manager ───────────────────────────────────────────────────────────────────
class AgentManager:
    def __init__(self, memory, vision_engine, learning_engine, intel_engine, sandbox):
        self.memory = memory

        self.agents: dict[str, BaseAgent] = {
            "planner":     PlannerAgent(memory),
            "research":    ResearchAgent(memory),
            "coding":      CodingAgent(memory, sandbox),
            "vision":      VisionAgent(memory, vision_engine),
            "learning":    LearningAgentWrapper(memory, learning_engine),
            "automation":  AutomationAgent(memory),
            "intelligence": IntelligenceAgent(memory, intel_engine),
        }
        logger.info(f"AgentManager ready — {len(self.agents)} agents.")

    def dispatch(self, agent_name: str, task: str) -> str:
        key   = agent_name.lower().replace("agent", "").strip()
        agent = self.agents.get(key)
        if not agent:
            for k, a in self.agents.items():
                if key in k or k in key:
                    agent = a
                    break
        if not agent:
            return f"Agent '{agent_name}' not found. Available: {list(self.agents.keys())}"
        return agent.run_task(task)

    def run_all(self, task="routine check") -> list:
        results = []
        lock    = threading.Lock()

        def run(a):
            r = a.run_task(task)
            with lock:
                results.append({"agent": a.name, "result": r})

        threads = [threading.Thread(target=run, args=(a,), daemon=True)
                   for a in self.agents.values()]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        return results

    def status_report(self) -> str:
        lines = ["🤖 *AGENTS STATUS*\n"]
        for a in self.agents.values():
            info   = a.info()
            icon   = "🟢" if info["status"] == "idle" else "🟡" if info["status"] == "running" else "🔴"
            last   = info["last_run"][:19] if info["last_run"] else "never"
            lines.append(
                f"{icon} *{info['name']}* | Tasks: {info['tasks_run']} | Last: {last}\n"
                f"   _{info['description']}_"
            )
        return "\n".join(lines)
