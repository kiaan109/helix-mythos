"""
Helix Mythos — Advanced Sandbox
Isolated execution · Security tools · Coding experiments · Network analysis
"""

import io
import sys
import time
import traceback
import logging
import importlib
import contextlib
from datetime import datetime

logger = logging.getLogger("HelixSandbox")


class Sandbox:
    def __init__(self, memory):
        self.memory   = memory
        self._history = []
        self._exp_id  = 0

    # ── Public API ────────────────────────────────────────────────────────────
    def run_experiment(self, code: str, timeout: int = 15) -> dict:
        self._exp_id += 1
        exp = {
            "id":      self._exp_id,
            "code":    code,
            "ts":      datetime.utcnow().isoformat(),
            "success": False,
            "output":  "",
            "error":   "",
            "runtime": 0.0,
        }
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        start      = time.time()
        try:
            with contextlib.redirect_stdout(stdout_buf), \
                 contextlib.redirect_stderr(stderr_buf):
                exec(compile(code, "<sandbox>", "exec"), self._safe_globals())
            exp["runtime"] = round(time.time() - start, 4)
            exp["output"]  = stdout_buf.getvalue()[:3000]
            exp["success"] = True
        except Exception:
            exp["runtime"] = round(time.time() - start, 4)
            exp["error"]   = traceback.format_exc()[-1500:]
        finally:
            extra = stderr_buf.getvalue()
            if extra:
                exp["output"] += "\n[stderr]\n" + extra[:500]

        self._history.append(exp)
        self._history = self._history[-50:]
        self.memory.append_log({
            "event": "sandbox_run", "exp_id": self._exp_id, "success": exp["success"]
        })
        return exp

    def predefined_experiments(self) -> list:
        experiments = [
            # ── Mathematics / Algorithms ────────────────────────────────────
            ("Primes < 100",
             "primes=[x for x in range(2,100) if all(x%i for i in range(2,x))]\n"
             "print(f'Primes: {primes}')"),

            ("Fibonacci 20",
             "a,b=0,1\nseq=[]\n"
             "for _ in range(20): seq.append(a); a,b=b,a+b\n"
             "print(f'Fibonacci: {seq}')"),

            # ── Data Science ────────────────────────────────────────────────
            ("NumPy Statistics",
             "import numpy as np\n"
             "data = np.random.randn(10000)\n"
             "print(f'N={len(data)} | Mean={data.mean():.4f} | "
             "Std={data.std():.4f} | Min={data.min():.4f} | Max={data.max():.4f}')"),

            ("Pandas Analysis",
             "import pandas as pd\nimport numpy as np\n"
             "df = pd.DataFrame({'A':np.random.randn(100),'B':np.random.randint(0,10,100)})\n"
             "print(df.describe())\nprint(f'\\nCorrelation: {df.corr().iloc[0,1]:.4f}')"),

            # ── Cryptography & Hashing ──────────────────────────────────────
            ("Hash Suite",
             "import hashlib\n"
             "msg = b'Helix Mythos Intelligence'\n"
             "for algo in ['md5','sha1','sha256','sha512','sha3_256','blake2b']:\n"
             "    h = hashlib.new(algo, msg).hexdigest()\n"
             "    print(f'{algo:12s}: {h}')"),

            ("Base64 Encode/Decode",
             "import base64\n"
             "original = 'Helix Mythos — All-Seeing AI'\n"
             "encoded  = base64.b64encode(original.encode()).decode()\n"
             "decoded  = base64.b64decode(encoded).decode()\n"
             "print(f'Original: {original}')\n"
             "print(f'Encoded:  {encoded}')\n"
             "print(f'Decoded:  {decoded}')"),

            ("Caesar Cipher",
             "def caesar(text, shift):\n"
             "    result = ''\n"
             "    for ch in text:\n"
             "        if ch.isalpha():\n"
             "            base = ord('A') if ch.isupper() else ord('a')\n"
             "            result += chr((ord(ch) - base + shift) % 26 + base)\n"
             "        else:\n"
             "            result += ch\n"
             "    return result\n"
             "msg = 'Helix Mythos is autonomous'\n"
             "enc = caesar(msg, 13)\n"
             "dec = caesar(enc, 13)\n"
             "print(f'Original:  {msg}')\n"
             "print(f'ROT13:     {enc}')\n"
             "print(f'Decrypted: {dec}')"),

            ("XOR Cipher",
             "def xor_cipher(data: bytes, key: int) -> bytes:\n"
             "    return bytes(b ^ key for b in data)\n"
             "msg = b'HelixMythos'\n"
             "key = 0x42\n"
             "enc = xor_cipher(msg, key)\n"
             "dec = xor_cipher(enc, key)\n"
             "print(f'Original:  {msg}')\n"
             "print(f'XOR key:   0x{key:02X}')\n"
             "print(f'Encrypted: {enc.hex()}')\n"
             "print(f'Decrypted: {dec}')"),

            # ── Networking / Recon ──────────────────────────────────────────
            ("Network Info",
             "import socket\n"
             "hostname = socket.gethostname()\n"
             "local_ip = socket.gethostbyname(hostname)\n"
             "print(f'Hostname:  {hostname}')\n"
             "print(f'Local IP:  {local_ip}')\n"
             "# Port check helper\n"
             "common_ports = [21,22,23,25,53,80,110,143,443,8080]\n"
             "print('\\nCommon ports (localhost check):')\n"
             "for port in common_ports[:5]:\n"
             "    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
             "    s.settimeout(0.3)\n"
             "    result = s.connect_ex(('127.0.0.1', port))\n"
             "    s.close()\n"
             "    status = 'OPEN' if result == 0 else 'closed'\n"
             "    print(f'  Port {port:5d}: {status}')"),

            ("DNS Lookup",
             "import socket\n"
             "domains = ['google.com','github.com','openai.com','cloudflare.com']\n"
             "print('DNS Resolution:')\n"
             "for domain in domains:\n"
             "    try:\n"
             "        ip = socket.gethostbyname(domain)\n"
             "        print(f'  {domain:25s} -> {ip}')\n"
             "    except Exception as e:\n"
             "        print(f'  {domain:25s} -> ERROR: {e}')"),

            # ── System / OS Info ────────────────────────────────────────────
            ("System Fingerprint",
             "import platform, os, sys\n"
             "print(f'OS:          {platform.system()} {platform.release()}')\n"
             "print(f'Version:     {platform.version()[:60]}')\n"
             "print(f'Machine:     {platform.machine()}')\n"
             "print(f'Processor:   {platform.processor()[:50]}')\n"
             "print(f'CPU cores:   {os.cpu_count()}')\n"
             "print(f'Python:      {sys.version[:40]}')\n"
             "print(f'Architecture:{platform.architecture()[0]}')"),

            ("Process List",
             "import psutil\n"
             "procs = [(p.info['name'], p.info['pid'], p.info.get('cpu_percent',0))\n"
             "         for p in psutil.process_iter(['name','pid','cpu_percent'])]\n"
             "procs.sort(key=lambda x: x[2], reverse=True)\n"
             "print(f'Top 15 Processes:')\n"
             "print(f'{\"Name\":30s} {\"PID\":8s} {\"CPU%\":6s}')\n"
             "print('-'*46)\n"
             "for name, pid, cpu in procs[:15]:\n"
             "    print(f'{name[:29]:30s} {pid:<8d} {cpu:6.1f}%')"),

            # ── Pattern Recognition ─────────────────────────────────────────
            ("Regex Pattern Extraction",
             "import re\n"
             "text = '''\n"
             "  IP: 192.168.1.1, 10.0.0.254, 172.16.0.1\n"
             "  Emails: admin@example.com, user@test.org\n"
             "  CVEs: CVE-2024-1234, CVE-2023-99999\n"
             "  URL: https://github.com/helix-ai\n"
             "  Phone: +1-555-0100\n"
             "'''\n"
             "print('IPs:',    re.findall(r'\\b\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\b', text))\n"
             "print('Emails:', re.findall(r'[\\w.-]+@[\\w.-]+\\.\\w+', text))\n"
             "print('CVEs:',   re.findall(r'CVE-\\d{4}-\\d+', text))\n"
             "print('URLs:',   re.findall(r'https?://\\S+', text))"),

            # ── ML Demo ─────────────────────────────────────────────────────
            ("ML Classification Demo",
             "from sklearn.datasets import load_iris\n"
             "from sklearn.model_selection import train_test_split\n"
             "from sklearn.ensemble import RandomForestClassifier\n"
             "from sklearn.metrics import accuracy_score, classification_report\n"
             "iris = load_iris()\n"
             "X_train, X_test, y_train, y_test = train_test_split(\n"
             "    iris.data, iris.target, test_size=0.3, random_state=42)\n"
             "clf = RandomForestClassifier(n_estimators=100, random_state=42)\n"
             "clf.fit(X_train, y_train)\n"
             "y_pred = clf.predict(X_test)\n"
             "print(f'Accuracy: {accuracy_score(y_test,y_pred)*100:.2f}%')\n"
             "print(classification_report(y_test, y_pred, target_names=iris.target_names))"),
        ]
        results = []
        for name, code in experiments:
            res        = self.run_experiment(code)
            res["name"] = name
            results.append(res)
        return results

    def get_history(self, limit: int = 10) -> list:
        return self._history[-limit:]

    def format_result(self, exp: dict) -> str:
        status = "✅ SUCCESS" if exp["success"] else "❌ FAILED"
        lines  = [
            f"🧪 *Sandbox Experiment #{exp['id']}*",
            f"Status: {status} | Runtime: {exp['runtime']}s",
        ]
        if exp["output"]:
            lines.append(f"```\n{exp['output'][:1200]}\n```")
        if exp["error"]:
            lines.append(f"*Error:*\n```\n{exp['error'][:500]}\n```")
        return "\n".join(lines)

    def format_history(self) -> str:
        h = self.get_history()
        if not h:
            return "No sandbox experiments run yet."
        lines = ["🧪 *Sandbox History*"]
        for exp in reversed(h):
            ok   = "✅" if exp["success"] else "❌"
            name = exp.get("name", f"Exp #{exp['id']}")
            lines.append(f"{ok} {name} ({exp['runtime']}s)")
        return "\n".join(lines)

    # ── Safe execution environment ────────────────────────────────────────────
    def _safe_globals(self) -> dict:
        ALLOWED_MODULES = {
            "math", "random", "statistics", "itertools", "functools",
            "collections", "datetime", "time", "string", "re", "io",
            "json", "csv", "base64", "hashlib", "hmac", "secrets",
            "struct", "binascii", "codecs",
            "socket", "ipaddress", "urllib", "http",
            "os", "sys", "platform", "pathlib",
            "numpy", "np", "pandas", "pd",
            "sklearn", "scipy",
            "psutil",
        }

        def safe_import(name, *args, **kwargs):
            root = name.split(".")[0]
            if root in ALLOWED_MODULES or name.split(".")[0] in ALLOWED_MODULES:
                return importlib.import_module(name)
            raise ImportError(f"Module '{name}' is not permitted in sandbox.")

        globs = {
            "__builtins__": {
                "print": print, "len": len, "range": range, "enumerate": enumerate,
                "zip": zip, "map": map, "filter": filter, "sorted": sorted,
                "reversed": reversed, "list": list, "dict": dict, "set": set,
                "tuple": tuple, "str": str, "int": int, "float": float,
                "bool": bool, "bytes": bytes, "bytearray": bytearray,
                "sum": sum, "min": min, "max": max, "abs": abs, "round": round,
                "type": type, "isinstance": isinstance, "hasattr": hasattr,
                "getattr": getattr, "dir": dir, "vars": vars, "repr": repr,
                "hex": hex, "oct": oct, "bin": bin, "ord": ord, "chr": chr,
                "format": format, "open": open,
                "__import__": safe_import,
            }
        }
        globs["__builtins__"]["__builtins__"] = globs["__builtins__"]
        return globs
