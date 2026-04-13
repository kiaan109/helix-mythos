"""
Helix Mythos — Security & Pentesting Agent
FOR AUTHORIZED TESTING ONLY: own networks, CTF challenges, security research.
"""

import socket
import hashlib
import re
import ssl
import logging
import subprocess
import requests
import itertools
import string
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

logger = logging.getLogger("HelixSecurity")

# Common passwords wordlist (top 500 — for CTF/authorized testing only)
COMMON_PASSWORDS = [
    "123456","password","123456789","12345678","12345","1234567","1234567890",
    "qwerty","abc123","password1","111111","123123","admin","letmein","welcome",
    "monkey","1234","dragon","master","sunshine","princess","shadow","superman",
    "michael","football","batman","iloveyou","trustno1","hunter","ranger",
    "harley","thomas","robert","soccer","hockey","killer","george","andrew",
    "jordan","hunter2","pass","test","test123","root","toor","admin123",
    "password123","qwerty123","abc1234","pass123","login","admin1","user",
    "guest","changeme","default","secret","1q2w3e","qazwsx","zxcvbn",
    "asdfgh","654321","987654321","pass1234","p@ssw0rd","p@ss","Pa$$w0rd",
    "P@ssword","passw0rd","Password1","Password123","administrator","raspberry",
    "alpine","ubuntu","debian","fedora","centos","kali","hacker","h4ck3r",
    "hack","security","pentest","exploit","reverse","payload","shellcode",
]

# Hash patterns for identification
HASH_PATTERNS = [
    (r"^[a-f0-9]{32}$",      "MD5"),
    (r"^[a-f0-9]{40}$",      "SHA-1"),
    (r"^[a-f0-9]{56}$",      "SHA-224"),
    (r"^[a-f0-9]{64}$",      "SHA-256"),
    (r"^[a-f0-9]{96}$",      "SHA-384"),
    (r"^[a-f0-9]{128}$",     "SHA-512"),
    (r"^\$2[aby]\$\d+\$.+$", "bcrypt"),
    (r"^\$1\$.+$",            "MD5-crypt"),
    (r"^\$6\$.+$",            "SHA-512-crypt"),
    (r"^\$5\$.+$",            "SHA-256-crypt"),
    (r"^[a-f0-9]{8}$",       "CRC32"),
    (r"^[a-zA-Z0-9+/]{24}=$","Base64-16B"),
    (r"^[A-Z0-9]{13}$",      "LM Hash (partial)"),
]


class SecurityAgent:
    def __init__(self, memory):
        self.memory = memory

    # ── Hash Identification ───────────────────────────────────────────────────
    def identify_hash(self, hash_str: str) -> str:
        h = hash_str.strip()
        matches = []
        for pattern, name in HASH_PATTERNS:
            if re.match(pattern, h, re.IGNORECASE):
                matches.append(name)
        if not matches:
            return f"🔍 *Hash Analysis: `{h[:40]}...`*\nUnknown hash type (length: {len(h)})"
        return (
            f"🔍 *Hash Identified*\n"
            f"Hash: `{h[:50]}`\n"
            f"Type: *{' / '.join(matches)}*\n"
            f"Length: {len(h)} chars"
        )

    # ── Hash Cracker (wordlist) ───────────────────────────────────────────────
    def crack_hash(self, hash_str: str, wordlist: list = None) -> str:
        h = hash_str.strip().lower()
        wl = wordlist or COMMON_PASSWORDS
        hash_type = None

        for pattern, name in HASH_PATTERNS:
            if re.match(pattern, h, re.IGNORECASE):
                hash_type = name
                break

        if not hash_type:
            return f"❌ Unknown hash type for: `{h[:40]}`"

        if hash_type not in ("MD5", "SHA-1", "SHA-256", "SHA-512", "SHA-224", "SHA-384"):
            return f"⚠️ `{hash_type}` cracking not supported via wordlist — use Hashcat."

        algo_map = {
            "MD5":     hashlib.md5,
            "SHA-1":   hashlib.sha1,
            "SHA-224": hashlib.sha224,
            "SHA-256": hashlib.sha256,
            "SHA-384": hashlib.sha384,
            "SHA-512": hashlib.sha512,
        }
        algo = algo_map[hash_type]

        for word in wl:
            if algo(word.encode()).hexdigest() == h:
                self.memory.append_log({"event": "hash_cracked", "type": hash_type})
                return (
                    f"🔓 *HASH CRACKED!*\n"
                    f"Hash: `{h[:50]}`\n"
                    f"Type: {hash_type}\n"
                    f"Password: *`{word}`*\n"
                    f"Checked {wl.index(word)+1}/{len(wl)} passwords"
                )

        return (
            f"🔒 *Hash not in wordlist*\n"
            f"Hash: `{h[:50]}`\n"
            f"Type: {hash_type}\n"
            f"Tried: {len(wl)} common passwords\n"
            f"_Try a larger wordlist or use Hashcat for brute force._"
        )

    # ── Hash Generator ────────────────────────────────────────────────────────
    def generate_hashes(self, text: str) -> str:
        return (
            f"#️⃣ *Hash Generator: `{text}`*\n\n"
            f"MD5:    `{hashlib.md5(text.encode()).hexdigest()}`\n"
            f"SHA-1:  `{hashlib.sha1(text.encode()).hexdigest()}`\n"
            f"SHA-256:`{hashlib.sha256(text.encode()).hexdigest()}`\n"
            f"SHA-512:`{hashlib.sha512(text.encode()).hexdigest()[:64]}...`"
        )

    # ── Password Strength Analyzer ────────────────────────────────────────────
    def analyze_password(self, password: str) -> str:
        length   = len(password)
        has_upper = bool(re.search(r'[A-Z]', password))
        has_lower = bool(re.search(r'[a-z]', password))
        has_digit = bool(re.search(r'\d', password))
        has_special = bool(re.search(r'[^a-zA-Z0-9]', password))
        is_common = password.lower() in [p.lower() for p in COMMON_PASSWORDS]

        score = 0
        if length >= 8:  score += 1
        if length >= 12: score += 1
        if length >= 16: score += 1
        if has_upper:    score += 1
        if has_lower:    score += 1
        if has_digit:    score += 1
        if has_special:  score += 2
        if is_common:    score = 0

        rating = ["💀 Terrible","🔴 Very Weak","🔴 Weak","🟠 Fair",
                  "🟡 Moderate","🟢 Good","🟢 Strong","✅ Very Strong","✅ Excellent"][min(score,8)]

        # Crack time estimate
        charset = 0
        if has_lower: charset += 26
        if has_upper: charset += 26
        if has_digit: charset += 10
        if has_special: charset += 32
        if charset == 0: charset = 26
        combinations = charset ** length
        seconds = combinations / 1_000_000_000  # 1 billion guesses/sec (GPU)
        if seconds < 1:
            crack_time = "< 1 second"
        elif seconds < 60:
            crack_time = f"{seconds:.0f} seconds"
        elif seconds < 3600:
            crack_time = f"{seconds/60:.0f} minutes"
        elif seconds < 86400:
            crack_time = f"{seconds/3600:.0f} hours"
        elif seconds < 31536000:
            crack_time = f"{seconds/86400:.0f} days"
        else:
            crack_time = f"{seconds/31536000:.0f} years"

        return (
            f"🔐 *Password Analysis*\n"
            f"{'(hidden for security)':}\n\n"
            f"Length: {length} chars\n"
            f"Uppercase: {'✅' if has_upper else '❌'} | "
            f"Lowercase: {'✅' if has_lower else '❌'}\n"
            f"Digits: {'✅' if has_digit else '❌'} | "
            f"Special: {'✅' if has_special else '❌'}\n"
            f"In common list: {'⚠️ YES — change it!' if is_common else '✅ No'}\n\n"
            f"*Strength: {rating}*\n"
            f"GPU crack time: `{crack_time}`\n"
            f"Combinations: `{combinations:,.0f}`"
        )

    # ── Password Generator ────────────────────────────────────────────────────
    def generate_password(self, length: int = 20) -> str:
        import secrets
        chars = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|"
        pwd = "".join(secrets.choice(chars) for _ in range(length))
        return (
            f"🔑 *Generated Secure Password*\n"
            f"`{pwd}`\n\n"
            f"Length: {length} | All character types included\n"
            f"Entropy: ~{length * 6:.0f} bits"
        )

    # ── Banner Grabbing / Service Fingerprinting ──────────────────────────────
    def grab_banner(self, host: str, port: int) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((host, port))
            try:
                s.send(b"HEAD / HTTP/1.0\r\n\r\n")
                banner = s.recv(1024).decode(errors="replace").strip()[:500]
            except Exception:
                banner = s.recv(1024).decode(errors="replace").strip()[:500]
            s.close()
            return (
                f"🏷 *Banner Grab: {host}:{port}*\n"
                f"```\n{banner}\n```"
            )
        except Exception as e:
            return f"Banner grab failed: {e}"

    # ── SSL/TLS Certificate Scanner ───────────────────────────────────────────
    def scan_ssl(self, host: str, port: int = 443) -> str:
        try:
            ctx  = ssl.create_default_context()
            conn = ctx.wrap_socket(socket.socket(), server_hostname=host)
            conn.settimeout(8)
            conn.connect((host, port))
            cert = conn.getpeercert()
            conn.close()

            subject  = dict(x[0] for x in cert.get("subject", []))
            issuer   = dict(x[0] for x in cert.get("issuer", []))
            san      = cert.get("subjectAltName", [])
            not_after = cert.get("notAfter", "?")

            # Check expiry
            try:
                expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                days_left = (expiry - datetime.utcnow()).days
                expiry_status = f"✅ Valid ({days_left} days left)" if days_left > 30 else f"⚠️ Expires in {days_left} days!"
            except Exception:
                expiry_status = not_after

            domains = [v for t, v in san if t == "DNS"][:8]

            return (
                f"🔒 *SSL Certificate: {host}*\n\n"
                f"Subject: `{subject.get('commonName','?')}`\n"
                f"Issuer: `{issuer.get('organizationName','?')}`\n"
                f"Expires: {expiry_status}\n"
                f"SANs: {', '.join(domains[:5])}"
                + (f" +{len(domains)-5} more" if len(domains) > 5 else "")
            )
        except ssl.SSLCertVerificationError as e:
            return f"⚠️ *SSL INVALID on {host}*\n`{e}`"
        except Exception as e:
            return f"SSL scan error: {e}"

    # ── Subdomain Finder ──────────────────────────────────────────────────────
    def find_subdomains(self, domain: str) -> str:
        common_subs = [
            "www","mail","ftp","admin","api","dev","test","staging","beta",
            "m","mobile","shop","blog","forum","portal","vpn","remote",
            "cdn","static","media","img","images","assets","upload",
            "smtp","pop","imap","ns1","ns2","dns","mx","cpanel","webmail",
            "login","auth","oauth","sso","secure","dashboard","app","web",
        ]
        found = []

        def check(sub):
            try:
                hostname = f"{sub}.{domain}"
                ip = socket.gethostbyname(hostname)
                return f"{hostname} → {ip}"
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=50) as ex:
            futures = [ex.submit(check, s) for s in common_subs]
            for f in as_completed(futures):
                r = f.result()
                if r:
                    found.append(r)

        found.sort()
        lines = [f"🌐 *Subdomain Scan: {domain}*", f"Found: {len(found)}\n"]
        for s in found[:20]:
            lines.append(f"  ✅ `{s}`")
        if not found:
            lines.append("  No common subdomains found.")
        self.memory.append_log({"event": "subdomain_scan", "domain": domain, "found": len(found)})
        return "\n".join(lines)

    # ── WHOIS / IP Intel ──────────────────────────────────────────────────────
    def whois_lookup(self, target: str) -> str:
        try:
            data = requests.get(f"https://ipapi.co/{target}/json/", timeout=8).json()
            if data.get("error"):
                # Try as domain
                ip = socket.gethostbyname(target)
                data = requests.get(f"https://ipapi.co/{ip}/json/", timeout=8).json()
            return (
                f"🌍 *IP/Domain Intel: {target}*\n\n"
                f"IP:       `{data.get('ip','?')}`\n"
                f"City:     {data.get('city','?')}\n"
                f"Region:   {data.get('region','?')}\n"
                f"Country:  {data.get('country_name','?')} {data.get('country_code','')}\n"
                f"ISP/ASN:  `{data.get('org','?')}`\n"
                f"Timezone: {data.get('timezone','?')}\n"
                f"Lat/Lon:  {data.get('latitude','?')}, {data.get('longitude','?')}"
            )
        except Exception as e:
            return f"WHOIS lookup failed: {e}"

    # ── CVE Lookup (NIST NVD) ─────────────────────────────────────────────────
    def cve_lookup(self, query: str) -> str:
        try:
            # If it's a CVE ID
            if query.upper().startswith("CVE-"):
                url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={query.upper()}"
            else:
                url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch={query}&resultsPerPage=5"

            resp = requests.get(url, timeout=10).json()
            vulns = resp.get("vulnerabilities", [])
            if not vulns:
                return f"No CVEs found for: {query}"

            lines = [f"🛡 *CVE Lookup: {query}*\n"]
            for v in vulns[:5]:
                cve  = v["cve"]
                cid  = cve["id"]
                desc = cve.get("descriptions", [{}])[0].get("value", "N/A")[:150]
                metrics = cve.get("metrics", {})
                score = "N/A"
                sev   = ""
                if "cvssMetricV31" in metrics:
                    d     = metrics["cvssMetricV31"][0]["cvssData"]
                    score = d.get("baseScore", "N/A")
                    sev   = d.get("baseSeverity", "")
                elif "cvssMetricV2" in metrics:
                    d     = metrics["cvssMetricV2"][0]["cvssData"]
                    score = d.get("baseScore", "N/A")

                sev_emoji = {"CRITICAL":"🔴","HIGH":"🟠","MEDIUM":"🟡","LOW":"🟢"}.get(sev, "⚪")
                lines.append(f"{sev_emoji} *{cid}* — Score: {score} {sev}")
                lines.append(f"  _{desc}_\n")

            return "\n".join(lines)
        except Exception as e:
            return f"CVE lookup error: {e}"

    # ── SQL Injection Tester (own sites only) ─────────────────────────────────
    def sqli_test(self, url: str) -> str:
        payloads = ["'", "''", "' OR '1'='1", "' OR 1=1--", "1' ORDER BY 1--",
                    "1 UNION SELECT NULL--", "admin'--", "' OR 'x'='x"]
        results = []
        errors  = ["sql syntax","mysql","sqlite","postgresql","ora-","syntax error",
                   "unclosed quotation","quoted string","sqlstate"]
        try:
            for payload in payloads[:5]:
                test_url = f"{url}{payload}"
                try:
                    r = requests.get(test_url, timeout=5)
                    body = r.text.lower()
                    if any(e in body for e in errors):
                        results.append(f"⚠️ Possible SQLi with: `{payload}`")
                    else:
                        results.append(f"✅ Clean: `{payload[:20]}`")
                except Exception as ex:
                    results.append(f"❌ Error: {ex}")

            lines = [f"💉 *SQL Injection Test: {url[:50]}*\n"]
            lines += results
            if any("⚠️" in r for r in results):
                lines.append("\n🚨 *Possible vulnerability detected — test on authorized targets only*")
            else:
                lines.append("\n✅ No obvious SQL injection detected")
            return "\n".join(lines)
        except Exception as e:
            return f"SQLi test error: {e}"

    # ── Header Security Analyzer ──────────────────────────────────────────────
    def analyze_headers(self, url: str) -> str:
        try:
            if not url.startswith("http"):
                url = "https://" + url
            r = requests.get(url, timeout=8)
            h = r.headers

            checks = [
                ("Strict-Transport-Security", "HSTS"),
                ("Content-Security-Policy",   "CSP"),
                ("X-Frame-Options",           "Clickjacking Protection"),
                ("X-Content-Type-Options",    "MIME Sniffing Protection"),
                ("X-XSS-Protection",          "XSS Filter"),
                ("Referrer-Policy",           "Referrer Policy"),
                ("Permissions-Policy",        "Permissions Policy"),
            ]
            lines = [f"🛡 *Security Headers: {url[:50]}*\n"]
            score = 0
            for header, name in checks:
                if header in h:
                    lines.append(f"✅ {name}: `{h[header][:60]}`")
                    score += 1
                else:
                    lines.append(f"❌ {name}: *missing*")

            rating = ["💀","🔴","🔴","🟠","🟡","🟢","🟢","✅"][score]
            lines.append(f"\n*Security Score: {rating} {score}/{len(checks)}*")
            lines.append(f"Server: `{h.get('Server','hidden')}`")
            lines.append(f"Tech: `{h.get('X-Powered-By','hidden')}`")
            return "\n".join(lines)
        except Exception as e:
            return f"Header analysis error: {e}"

    # ── Port + Vuln Quick Scan ────────────────────────────────────────────────
    def vuln_scan(self, host: str) -> str:
        """Quick vulnerability assessment: open ports + service banners + known risks."""
        risky_ports = {
            21:   "FTP — often unencrypted, check for anonymous login",
            22:   "SSH — ensure key-based auth, no root login",
            23:   "Telnet — UNENCRYPTED, replace with SSH immediately",
            25:   "SMTP — check for open relay",
            53:   "DNS — check for zone transfer vulnerability",
            80:   "HTTP — no encryption, redirect to HTTPS",
            110:  "POP3 — unencrypted email",
            143:  "IMAP — unencrypted email",
            445:  "SMB — EternalBlue risk, patch immediately",
            1433: "MSSQL — restrict access",
            3306: "MySQL — should not be exposed publicly",
            3389: "RDP — brute force target, use VPN",
            5432: "PostgreSQL — restrict access",
            5900: "VNC — weak auth risk",
            6379: "Redis — often no auth, critical risk",
            8080: "HTTP Alt — check for exposed admin panels",
            8443: "HTTPS Alt",
            27017:"MongoDB — often no auth, critical risk",
        }
        open_ports = []

        def check(port):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.7)
            r = s.connect_ex((host, port))
            s.close()
            return port if r == 0 else None

        with ThreadPoolExecutor(max_workers=100) as ex:
            futures = [ex.submit(check, p) for p in risky_ports]
            for f in as_completed(futures):
                p = f.result()
                if p:
                    open_ports.append(p)

        open_ports.sort()
        lines = [f"⚠️ *Vulnerability Scan: {host}*\n"]
        if not open_ports:
            lines.append("✅ No high-risk ports open")
        else:
            lines.append(f"Found {len(open_ports)} potentially risky open ports:\n")
            for p in open_ports:
                risk = risky_ports.get(p, "Unknown service")
                lines.append(f"🔴 `{p}` — {risk}")

        self.memory.append_log({"event": "vuln_scan", "host": host, "found": len(open_ports)})
        return "\n".join(lines)
