"""
Helix Mythos — Code Creator Agent
Creates files, writes code, builds projects via Telegram commands.
"""

import os
import re
import logging
import subprocess
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("HelixCodeCreator")

WORKSPACE = Path("helix_workspace")
WORKSPACE.mkdir(exist_ok=True)


class CodeCreatorAgent:
    def __init__(self, memory):
        self.memory    = memory
        self._files    = []  # list of created file paths
        self._history  = []

    # ── Public API ────────────────────────────────────────────────────────────
    def create_file(self, filename: str, content: str) -> str:
        path = WORKSPACE / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self._files.append(str(path))
        self.memory.append_log({"event": "file_created", "path": str(path)})
        logger.info(f"Created file: {path}")
        return f"✅ Created `{filename}` ({len(content)} chars)"

    def read_file(self, filename: str) -> str:
        path = WORKSPACE / filename
        if not path.exists():
            return f"❌ File not found: {filename}"
        return path.read_text(encoding="utf-8")[:3000]

    def list_files(self) -> str:
        files = list(WORKSPACE.rglob("*"))
        if not files:
            return "Workspace is empty."
        lines = ["📁 *Helix Workspace Files:*\n"]
        for f in files:
            if f.is_file():
                size = f.stat().st_size
                lines.append(f"• `{f.relative_to(WORKSPACE)}` ({size} bytes)")
        return "\n".join(lines)

    def run_file(self, filename: str) -> str:
        path = WORKSPACE / filename
        if not path.exists():
            return f"❌ File not found: {filename}"
        try:
            result = subprocess.run(
                ["C:\\Python312\\python.exe", str(path)],
                capture_output=True, text=True, timeout=15,
                cwd=str(WORKSPACE)
            )
            out = result.stdout[:1500] or result.stderr[:1500] or "(no output)"
            return f"▶️ *Running {filename}:*\n```\n{out}\n```"
        except subprocess.TimeoutExpired:
            return f"⏱ Execution timed out after 15s"
        except Exception as e:
            return f"❌ Run error: {e}"

    def delete_file(self, filename: str) -> str:
        path = WORKSPACE / filename
        if not path.exists():
            return f"❌ Not found: {filename}"
        path.unlink()
        return f"🗑 Deleted `{filename}`"

    def generate_code(self, description: str) -> tuple[str, str]:
        """
        Auto-generate a Python file based on natural language description.
        Returns (filename, code).
        """
        d    = description.lower()
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = re.sub(r"[^a-z0-9_]", "_", d[:30]).strip("_") or "script"
        filename = f"{name}_{ts}.py"

        # ── Template library ──────────────────────────────────────────────────
        if any(k in d for k in ["web scraper", "scrape", "scraping"]):
            url = re.search(r"https?://\S+", description)
            target = url.group(0) if url else "https://example.com"
            code = f'''import requests
from bs4 import BeautifulSoup

url = "{target}"
headers = {{"User-Agent": "Mozilla/5.0 HelixMythos/2.0"}}
resp = requests.get(url, headers=headers, timeout=10)
soup = BeautifulSoup(resp.text, "html.parser")

print(f"Title: {{soup.title.string if soup.title else 'N/A'}}")
print(f"Status: {{resp.status_code}}")

links = soup.find_all("a", href=True)[:10]
print(f"\\nFirst 10 links:")
for a in links:
    print(f"  {{a.get_text(strip=True)[:50]}} -> {{a['href'][:80]}}")
'''
        elif any(k in d for k in ["api", "rest", "fetch", "request"]):
            code = f'''import requests
import json

# Generated: {description}
url = "https://api.example.com/data"
headers = {{"Content-Type": "application/json", "User-Agent": "HelixMythos"}}

response = requests.get(url, headers=headers, timeout=10)
print(f"Status: {{response.status_code}}")
data = response.json()
print(json.dumps(data, indent=2))
'''
        elif any(k in d for k in ["sort", "algorithm", "search", "data structure"]):
            code = f'''# Generated: {description}
import random, time

def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left  = [x for x in arr if x < pivot]
    mid   = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + mid + quicksort(right)

def binary_search(arr, target):
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1

data   = random.sample(range(1000), 20)
print(f"Unsorted: {{data}}")
sorted_data = quicksort(data)
print(f"Sorted:   {{sorted_data}}")
target = sorted_data[5]
idx    = binary_search(sorted_data, target)
print(f"Search {{target}}: found at index {{idx}}")
'''
        elif any(k in d for k in ["file", "read", "write", "csv", "json", "text"]):
            code = f'''# Generated: {description}
import json, csv, os
from pathlib import Path

# Write JSON
data = {{"name": "Helix", "version": "2.0", "status": "active", "items": [1,2,3]}}
with open("output.json", "w") as f:
    json.dump(data, f, indent=2)
print("Written: output.json")

# Write CSV
rows = [["name","score","grade"],["Alice",95,"A"],["Bob",82,"B"],["Carol",78,"C"]]
with open("output.csv", "w", newline="") as f:
    csv.writer(f).writerows(rows)
print("Written: output.csv")

# Read back
loaded = json.load(open("output.json"))
print(f"Loaded JSON: {{loaded}}")
'''
        elif any(k in d for k in ["chat", "bot", "discord", "telegram"]):
            code = f'''# Generated: {description}
# Telegram bot example
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "YOUR_BOT_TOKEN_HERE"

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I am a bot created by Helix Mythos.")

async def echo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"You said: {{update.message.text}}")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
app.run_polling()
'''
        elif any(k in d for k in ["ml", "machine learning", "train", "model", "neural", "predict"]):
            code = f'''# Generated: {description}
import numpy as np
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report

# Generate dataset
X, y = make_classification(n_samples=1000, n_features=10, n_classes=2, random_state=42)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train ensemble
models = {{
    "RandomForest":    RandomForestClassifier(n_estimators=100, random_state=42),
    "GradientBoost":   GradientBoostingClassifier(n_estimators=100, random_state=42),
    "LogisticReg":     LogisticRegression(max_iter=1000),
}}
for name, model in models.items():
    model.fit(X_train, y_train)
    acc = accuracy_score(y_test, model.predict(X_test))
    print(f"{{name}}: {{acc*100:.2f}}% accuracy")
'''
        else:
            code = f'''# Helix Mythos — Generated Script
# Task: {description}
# Created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

import sys, os, json
from pathlib import Path
from datetime import datetime

def main():
    print("=" * 50)
    print(f"Task: {description}")
    print(f"Time: {{datetime.now()}}")
    print("=" * 50)

    # Main logic goes here
    result = {{
        "task": "{description}",
        "status": "executed",
        "timestamp": datetime.now().isoformat()
    }}
    print(json.dumps(result, indent=2))
    return result

if __name__ == "__main__":
    main()
'''
        return filename, code

    def auto_create(self, description: str) -> str:
        filename, code = self.generate_code(description)
        self.create_file(filename, code)
        preview = "\n".join(code.split("\n")[:15])
        return (
            f"🛠 *Code Created:* `{filename}`\n"
            f"📝 Description: {description}\n"
            f"```python\n{preview}\n...\n```\n"
            f"Use `/runfile {filename}` to execute."
        )

    def build_project(self, project_name: str, project_type: str) -> str:
        """Create a full project structure."""
        pdir   = WORKSPACE / project_name
        pdir.mkdir(parents=True, exist_ok=True)
        created = []

        if "web" in project_type.lower() or "flask" in project_type.lower():
            files = {
                "app.py": '''from flask import Flask, jsonify, request
app = Flask(__name__)

@app.route("/")
def index():
    return jsonify({"status": "ok", "message": "Helix Web App"})

@app.route("/api/data", methods=["GET", "POST"])
def data():
    if request.method == "POST":
        return jsonify({"received": request.json})
    return jsonify({"data": [1, 2, 3]})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
''',
                "requirements.txt": "flask\nrequests\n",
                "README.md": f"# {project_name}\nGenerated by Helix Mythos\n",
            }
        elif "bot" in project_type.lower():
            files = {
                "bot.py": '''from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram import Update

TOKEN = "YOUR_TOKEN"

async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text("Bot created by Helix Mythos!")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.run_polling()
''',
                "requirements.txt": "python-telegram-bot>=20.0\n",
                "README.md": f"# {project_name} Bot\nGenerated by Helix Mythos\n",
            }
        else:
            files = {
                "main.py": f'''"""
{project_name} — Generated by Helix Mythos
Type: {project_type}
"""

def main():
    print("Project: {project_name}")
    print("Type: {project_type}")

if __name__ == "__main__":
    main()
''',
                "requirements.txt": "requests\nnumpy\npandas\n",
                "README.md": f"# {project_name}\nType: {project_type}\nGenerated by Helix Mythos\n",
                "config.json": f'{{"project": "{project_name}", "version": "1.0.0"}}',
            }

        for fname, content in files.items():
            (pdir / fname).write_text(content, encoding="utf-8")
            created.append(fname)

        self.memory.append_log({"event": "project_created", "name": project_name, "type": project_type})
        return (
            f"🏗 *Project Created:* `{project_name}/`\n"
            f"Type: {project_type}\n"
            f"Files: {', '.join(f'`{f}`' for f in created)}\n"
            f"Location: `helix_workspace/{project_name}/`"
        )
