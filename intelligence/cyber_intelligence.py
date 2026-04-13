"""
Helix Mythos — Cybersecurity Intelligence Engine
Defensive security awareness · CVE monitoring · OSINT · Threat intelligence
All content is framed for DEFENSIVE and EDUCATIONAL purposes only.
"""

import gzip
import hashlib
import json
import logging
import re
import time
import threading
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import config

logger = logging.getLogger("HelixCyber")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests not installed. Cyber intelligence feed fetching disabled.")

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False
    logger.warning("feedparser not installed. RSS cyber feeds disabled.")

# ── Severity thresholds ───────────────────────────────────────────────────────
SEVERITY_CRITICAL = 9.0
SEVERITY_HIGH     = 7.0
SEVERITY_MEDIUM   = 4.0
SEVERITY_LOW      = 0.0


def classify_severity(score):
    """Classify a CVSS score into a severity label."""
    if score is None:
        return "UNKNOWN"
    try:
        score = float(score)
    except (TypeError, ValueError):
        return "UNKNOWN"
    if score >= SEVERITY_CRITICAL:
        return "CRITICAL"
    if score >= SEVERITY_HIGH:
        return "HIGH"
    if score >= SEVERITY_MEDIUM:
        return "MEDIUM"
    return "LOW"


# ── Security RSS feeds ────────────────────────────────────────────────────────
CYBER_RSS_FEEDS = [
    ("Krebs on Security",    "https://krebsonsecurity.com/feed/"),
    ("Dark Reading",         "https://www.darkreading.com/rss.xml"),
    ("Threatpost",           "https://threatpost.com/feed/"),
    ("Hacker News Security", "https://hnrss.org/frontpage?q=security+vulnerability+CVE"),
    ("CISA Advisories",      "https://www.cisa.gov/cybersecurity-advisories/all.xml"),
    ("Schneier on Security", "https://www.schneier.com/feed/atom"),
    ("SecurityWeek",         "https://www.securityweek.com/rss.xml"),
    ("NVD Recent CVEs",      "https://nvd.nist.gov/feeds/xml/cve/misc/nvd-rss.xml"),
    ("Exploit-DB",           "https://www.exploit-db.com/rss.xml"),
    ("CERT Latest",          "https://www.kb.cert.org/vuls/atomfeed"),
    ("BleepingComputer",     "https://www.bleepingcomputer.com/feed/"),
    ("The Hacker News",      "https://feeds.feedburner.com/TheHackersNews"),
    ("Graham Cluley",        "https://www.grahamcluley.com/feed/"),
    ("TroyHunt",             "https://www.troyhunt.com/rss/"),
    ("SecurityAffairs",      "https://securityaffairs.co/wordpress/feed"),
    ("SANS ISC",             "https://isc.sans.edu/rssfeed_full.xml"),
    ("Packet Storm",         "https://rss.packetstormsecurity.com/files/"),
    ("Full Disclosure",      "https://seclists.org/rss/fulldisclosure.rss"),
]

# ── OWASP Top 10 knowledge base ───────────────────────────────────────────────
OWASP_TOP_10 = {
    "A01:2021": {
        "name":        "Broken Access Control",
        "description": "Moving up from #5 in 2017. 94% of applications were tested for broken access control.",
        "defense":     "Implement least-privilege access controls, deny by default, log and alert failures.",
    },
    "A02:2021": {
        "name":        "Cryptographic Failures",
        "description": "Previously known as Sensitive Data Exposure. Focus on failures related to cryptography.",
        "defense":     "Use strong modern algorithms (AES-256, RSA-2048+, TLS 1.3). Never use MD5/SHA1 for passwords.",
    },
    "A03:2021": {
        "name":        "Injection",
        "description": "SQL, NoSQL, OS, LDAP injection. 94% of applications tested had some form of injection.",
        "defense":     "Use parameterized queries, ORM, input validation, least-privilege database accounts.",
    },
    "A04:2021": {
        "name":        "Insecure Design",
        "description": "New category for 2021 focusing on design flaws rather than implementation bugs.",
        "defense":     "Threat modeling, secure design patterns, security requirements in SDLC.",
    },
    "A05:2021": {
        "name":        "Security Misconfiguration",
        "description": "Moving up from #6. 90% of applications tested for misconfiguration.",
        "defense":     "Hardening, patch management, remove unused features, review cloud configs.",
    },
    "A06:2021": {
        "name":        "Vulnerable and Outdated Components",
        "description": "Previously known as Using Components with Known Vulnerabilities.",
        "defense":     "Maintain software inventory (SBOM), continuous vulnerability scanning, automated updates.",
    },
    "A07:2021": {
        "name":        "Identification and Authentication Failures",
        "description": "Previously known as Broken Authentication.",
        "defense":     "MFA, strong password policies, secure session management, account lockout.",
    },
    "A08:2021": {
        "name":        "Software and Data Integrity Failures",
        "description": "New category: insecure CI/CD pipelines, auto-update without integrity verification.",
        "defense":     "Use signed packages, verify checksums, secure CI/CD pipeline, SBOM.",
    },
    "A09:2021": {
        "name":        "Security Logging and Monitoring Failures",
        "description": "Insufficient logging enables attackers to persist undetected.",
        "defense":     "Centralized logging (SIEM), alerting on anomalies, retention policy, incident response plan.",
    },
    "A10:2021": {
        "name":        "Server-Side Request Forgery (SSRF)",
        "description": "New category. SSRF flaws occur when a server makes requests to attacker-specified URLs.",
        "defense":     "Allowlist outbound requests, disable unnecessary URL schemes, network segmentation.",
    },
}

# ── Security tools knowledge base ────────────────────────────────────────────
SECURITY_TOOLS_KB = {
    "nmap": {
        "purpose":    "Network discovery and security auditing tool.",
        "use_case":   "Port scanning, service/OS detection, network inventory.",
        "defense":    "Use firewalls to restrict unnecessary ports. Monitor for scan patterns in logs. "
                      "Deploy IDS/IPS (Snort, Suricata). Implement port knocking for sensitive services.",
        "category":  "Reconnaissance",
    },
    "metasploit": {
        "purpose":    "Penetration testing framework for developing and executing exploits.",
        "use_case":   "Exploit development, payload generation, post-exploitation modules.",
        "defense":    "Patch all CVEs promptly. Use EDR (Endpoint Detection & Response). "
                      "Network segmentation. Monitor for Meterpreter shellcode patterns.",
        "category":  "Exploitation",
    },
    "burp_suite": {
        "purpose":    "Web application security testing proxy.",
        "use_case":   "Intercepting HTTP/HTTPS, fuzzing, scanning web apps for vulnerabilities.",
        "defense":    "WAF (Web Application Firewall), input validation, CSP headers, rate limiting. "
                      "Scan your own apps before attackers do.",
        "category":  "Web Testing",
    },
    "wireshark": {
        "purpose":    "Network protocol analyzer (packet capture and analysis).",
        "use_case":   "Traffic analysis, troubleshooting, detecting unencrypted credentials.",
        "defense":    "Encrypt all traffic (TLS 1.3). Use network segmentation. "
                      "802.1X port authentication. Monitor for promiscuous mode NICs.",
        "category":  "Reconnaissance",
    },
    "sqlmap": {
        "purpose":    "Automated SQL injection detection and exploitation tool.",
        "use_case":   "Finding and exploiting SQL injection vulnerabilities in databases.",
        "defense":    "Parameterized queries / prepared statements. ORM usage. "
                      "WAF with SQL injection rules. Least-privilege DB accounts.",
        "category":  "Exploitation",
    },
    "aircrack-ng": {
        "purpose":    "WiFi network security auditing suite.",
        "use_case":   "WEP/WPA/WPA2 cracking, packet injection, network monitoring.",
        "defense":    "Use WPA3 or WPA2-Enterprise (802.1X). Strong passphrases (20+ chars). "
                      "Rogue AP detection. Monitor for deauth floods.",
        "category":  "Wireless",
    },
    "hashcat": {
        "purpose":    "Advanced GPU-accelerated password cracking tool.",
        "use_case":   "Cracking password hashes using dictionary, brute-force, and rule attacks.",
        "defense":    "Use bcrypt/Argon2/scrypt for password hashing. Long passphrases. "
                      "Account lockout. MFA everywhere.",
        "category":  "Password Attacks",
    },
    "john_the_ripper": {
        "purpose":    "Password security auditing and recovery tool.",
        "use_case":   "Cracking various password hash formats. Auditing password strength.",
        "defense":    "Strong password policies. Modern adaptive hashing algorithms. "
                      "Monitor for hash dump attempts.",
        "category":  "Password Attacks",
    },
    "hydra": {
        "purpose":    "Fast online network login brute-forcer.",
        "use_case":   "Brute-forcing login forms for SSH, FTP, HTTP, RDP and many other protocols.",
        "defense":    "Rate limiting. Account lockout. MFA. Fail2ban / IP reputation blocking. "
                      "SSH key-only authentication. VPN for administrative services.",
        "category":  "Credential Attacks",
    },
}

# ── Pentest methodology knowledge base ───────────────────────────────────────
PENTEST_METHODOLOGY = {
    "phases": [
        {
            "phase":       "1. Reconnaissance",
            "description": "Passive and active information gathering about the target.",
            "techniques":  ["OSINT", "DNS enumeration", "WHOIS", "Google dorking", "Shodan"],
            "defense":     "Minimize public information exposure. Monitor OSINT about your org. "
                           "Use privacy-protecting WHOIS. Limit DNS zone transfers.",
        },
        {
            "phase":       "2. Scanning & Enumeration",
            "description": "Identify open ports, services, and vulnerabilities.",
            "techniques":  ["Nmap", "Nessus", "OpenVAS", "Nikto", "Gobuster"],
            "defense":     "Network segmentation. Firewall rules. IDS/IPS. "
                           "Honeypots. Disable unused services.",
        },
        {
            "phase":       "3. Exploitation",
            "description": "Attempt to gain access by exploiting identified vulnerabilities.",
            "techniques":  ["Metasploit", "SQLmap", "custom exploits", "phishing"],
            "defense":     "Patch management. WAF. EDR. Zero-trust architecture. "
                           "Email filtering. Security awareness training.",
        },
        {
            "phase":       "4. Post-Exploitation",
            "description": "Maintain access, escalate privileges, and pivot through the network.",
            "techniques":  ["Privilege escalation", "lateral movement", "persistence", "data exfiltration"],
            "defense":     "Least privilege. Network segmentation. DLP (Data Loss Prevention). "
                           "SIEM alerting. Behavioral analytics (UEBA).",
        },
        {
            "phase":       "5. Reporting",
            "description": "Document findings, evidence, impact, and remediation recommendations.",
            "techniques":  ["Executive report", "technical report", "risk scoring", "POC code"],
            "defense":     "Use findings to build a remediation roadmap. Retest after fixes.",
        },
    ]
}


class CyberIntelligence:
    def __init__(self, memory=None, notify_callback=None):
        self.memory         = memory
        self.notify         = notify_callback
        self._running       = False
        self._thread        = None
        self._lock          = threading.Lock()
        self._seen          = set()
        self._cve_store     = []   # list of CVE dicts
        self._feed_items    = []   # list of security news items
        self._scan_count    = 0
        self._total_cves    = 0
        self._alert_sent    = set()   # CVE IDs already alerted
        self._report_cache  = {}

    # ── Public API ────────────────────────────────────────────────────────────
    def start(self):
        self._running = True
        self._thread  = threading.Thread(
            target=self._loop, daemon=True, name="CyberIntel"
        )
        self._thread.start()
        logger.info("CyberIntelligence Engine started — monitoring 18 security feeds.")

    def stop(self):
        self._running = False

    def get_cves(self, severity=None, limit=20):
        """Return stored CVEs, optionally filtered by severity."""
        with self._lock:
            cves = list(self._cve_store)
        if severity:
            cves = [c for c in cves if c.get("severity") == severity.upper()]
        return cves[:limit]

    def get_feed_items(self, limit=30):
        with self._lock:
            return list(self._feed_items[:limit])

    def get_owasp(self, code=None):
        """Return OWASP Top 10 entry or all entries."""
        if code:
            return OWASP_TOP_10.get(code)
        return OWASP_TOP_10

    def get_tool_info(self, tool_name=None):
        """Return security tool knowledge base entry or all tools."""
        if tool_name:
            return SECURITY_TOOLS_KB.get(tool_name.lower().replace(" ", "_").replace("-", "_"))
        return SECURITY_TOOLS_KB

    def get_pentest_methodology(self):
        return PENTEST_METHODOLOGY

    def osint_lookup(self, query, query_type="domain"):
        """
        OSINT lookup using public APIs (VirusTotal, Shodan, AbuseIPDB).
        All require API keys; graceful fallback if unavailable.
        """
        results = {"query": query, "type": query_type, "sources": {}}

        if not REQUESTS_AVAILABLE:
            results["error"] = "requests library not available"
            return results

        vt_key   = getattr(config, "VIRUSTOTAL_API_KEY", None)
        sh_key   = getattr(config, "SHODAN_API_KEY", None)
        ab_key   = getattr(config, "ABUSEIPDB_API_KEY", None)

        # VirusTotal
        if vt_key:
            try:
                if query_type == "domain":
                    url  = f"https://www.virustotal.com/api/v3/domains/{query}"
                elif query_type == "ip":
                    url  = f"https://www.virustotal.com/api/v3/ip_addresses/{query}"
                elif query_type == "hash":
                    url  = f"https://www.virustotal.com/api/v3/files/{query}"
                else:
                    url = None
                if url:
                    r    = requests.get(url, headers={"x-apikey": vt_key}, timeout=10)
                    data = r.json()
                    stats = (
                        data.get("data", {})
                            .get("attributes", {})
                            .get("last_analysis_stats", {})
                    )
                    results["sources"]["virustotal"] = stats
            except Exception as e:
                results["sources"]["virustotal"] = f"error: {e}"
        else:
            results["sources"]["virustotal"] = "no API key configured"

        # Shodan (IP only)
        if sh_key and query_type == "ip":
            try:
                r    = requests.get(
                    f"https://api.shodan.io/shodan/host/{query}?key={sh_key}",
                    timeout=10
                )
                data = r.json()
                results["sources"]["shodan"] = {
                    "ports":    data.get("ports", []),
                    "org":      data.get("org", ""),
                    "country":  data.get("country_name", ""),
                    "vulns":    list(data.get("vulns", {}).keys())[:10],
                }
            except Exception as e:
                results["sources"]["shodan"] = f"error: {e}"
        elif not sh_key:
            results["sources"]["shodan"] = "no API key configured"

        # AbuseIPDB (IP only)
        if ab_key and query_type == "ip":
            try:
                r = requests.get(
                    "https://api.abuseipdb.com/api/v2/check",
                    headers={"Key": ab_key, "Accept": "application/json"},
                    params={"ipAddress": query, "maxAgeInDays": 90},
                    timeout=10,
                )
                data = r.json().get("data", {})
                results["sources"]["abuseipdb"] = {
                    "abuse_confidence": data.get("abuseConfidenceScore", 0),
                    "total_reports":    data.get("totalReports", 0),
                    "country":          data.get("countryCode", ""),
                    "isp":              data.get("isp", ""),
                    "is_whitelisted":   data.get("isWhitelisted", False),
                }
            except Exception as e:
                results["sources"]["abuseipdb"] = f"error: {e}"
        elif not ab_key:
            results["sources"]["abuseipdb"] = "no API key configured"

        return results

    # ── Internal scan loop ────────────────────────────────────────────────────
    def _loop(self):
        while self._running:
            try:
                self._scan_cycle()
            except Exception as e:
                logger.error(f"Cyber scan error: {e}")
            time.sleep(60)   # every 60 seconds

    def _scan_cycle(self):
        self._scan_count += 1
        logger.info(f"Cyber scan #{self._scan_count}")

        threads = []

        t1 = threading.Thread(target=self._fetch_nvd_cves,   daemon=True)
        t2 = threading.Thread(target=self._fetch_rss_feeds,  daemon=True)
        threads.extend([t1, t2])
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=45)

        self._build_report()
        logger.info(
            f"Cyber scan #{self._scan_count} done — "
            f"{self._total_cves} CVEs tracked, "
            f"{len(self._feed_items)} feed items."
        )

    # ── NVD CVE Feed ──────────────────────────────────────────────────────────
    def _fetch_nvd_cves(self):
        """Fetch recent CVEs from NVD JSON feed."""
        if not REQUESTS_AVAILABLE:
            return
        url = "https://nvd.nist.gov/feeds/json/cve/1.1/nvdcve-1.1-recent.json.gz"
        try:
            resp = requests.get(url, timeout=30, stream=True)
            if resp.status_code != 200:
                logger.debug(f"NVD fetch HTTP {resp.status_code}")
                return
            raw  = gzip.decompress(resp.content)
            data = json.loads(raw)
            cve_items = data.get("CVE_Items", [])
            new_count = 0
            with self._lock:
                for item in cve_items[:50]:
                    cve_id = (
                        item.get("cve", {})
                            .get("CVE_data_meta", {})
                            .get("ID", "")
                    )
                    if not cve_id or cve_id in self._seen:
                        continue
                    self._seen.add(cve_id)

                    # Extract description
                    descs = (
                        item.get("cve", {})
                            .get("description", {})
                            .get("description_data", [])
                    )
                    description = descs[0]["value"] if descs else ""

                    # CVSS v3 score
                    impact = item.get("impact", {})
                    cvss3  = impact.get("baseMetricV3", {}).get("cvssV3", {})
                    cvss2  = impact.get("baseMetricV2", {}).get("cvssV2", {})
                    score  = cvss3.get("baseScore") or cvss2.get("baseScore")
                    severity = classify_severity(score)

                    # Affected CPEs
                    cpe_nodes = (
                        item.get("configurations", {})
                            .get("nodes", [])
                    )
                    affected = []
                    for node in cpe_nodes[:3]:
                        for cpe_match in node.get("cpe_match", [])[:3]:
                            cpe = cpe_match.get("cpe23Uri", "")
                            if cpe:
                                affected.append(cpe.split(":")[-3] + " " + cpe.split(":")[-2])

                    published = item.get("publishedDate", "")[:10]

                    cve_dict = {
                        "id":          cve_id,
                        "description": description[:300],
                        "cvss_score":  score,
                        "severity":    severity,
                        "affected":    affected[:5],
                        "published":   published,
                        "patch_status":"check NVD/vendor",
                        "source":      "NVD",
                    }
                    self._cve_store.insert(0, cve_dict)
                    self._total_cves += 1
                    new_count += 1

                    # Alert for CRITICAL CVEs immediately
                    if severity == "CRITICAL" and cve_id not in self._alert_sent:
                        self._alert_sent.add(cve_id)
                        self._send_cve_alert(cve_dict)

                    # Persist to memory
                    if self.memory:
                        try:
                            self.memory.store_event(
                                f"CVE {cve_id} ({severity})",
                                "Cybersecurity", "NVD",
                                f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                                description[:200]
                            )
                        except Exception:
                            pass

                # Keep store trimmed
                self._cve_store = self._cve_store[:500]

            logger.info(f"NVD: {new_count} new CVEs ingested.")
        except Exception as e:
            logger.debug(f"NVD CVE fetch error: {e}")

    # ── RSS Security Feeds ────────────────────────────────────────────────────
    def _fetch_rss_feeds(self):
        if not FEEDPARSER_AVAILABLE:
            return
        new_items = []
        for source_name, url in CYBER_RSS_FEEDS:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:6]:
                    title   = entry.get("title", "").strip()
                    link    = entry.get("link", "")
                    summary = (entry.get("summary", "") or "")[:300]
                    if not title:
                        continue
                    key = hashlib.md5(title.encode()).hexdigest()
                    if key in self._seen:
                        continue
                    self._seen.add(key)

                    # Extract any CVE IDs mentioned
                    cves_mentioned = re.findall(
                        r"\bCVE-\d{4}-\d{4,7}\b",
                        title + " " + summary
                    )

                    # Severity heuristic from title keywords
                    severity = "INFO"
                    title_lower = title.lower()
                    if any(w in title_lower for w in [
                        "critical", "remote code execution", "rce", "zero-day",
                        "0-day", "unauthenticated", "actively exploited"
                    ]):
                        severity = "CRITICAL"
                    elif any(w in title_lower for w in [
                        "high", "privilege escalation", "authentication bypass",
                        "sql injection", "command injection"
                    ]):
                        severity = "HIGH"
                    elif any(w in title_lower for w in [
                        "medium", "xss", "csrf", "information disclosure", "patch"
                    ]):
                        severity = "MEDIUM"

                    item = {
                        "title":          title,
                        "source":         source_name,
                        "url":            link,
                        "summary":        summary,
                        "cves_mentioned": cves_mentioned,
                        "severity":       severity,
                        "ts":             datetime.utcnow().isoformat(),
                    }
                    new_items.append(item)

                    if self.memory:
                        try:
                            self.memory.store_event(
                                title, "Cybersecurity", source_name, link, summary
                            )
                        except Exception:
                            pass
            except Exception as e:
                logger.debug(f"Cyber RSS [{source_name}]: {e}")

        with self._lock:
            self._feed_items = new_items + self._feed_items
            self._feed_items = self._feed_items[:600]

        logger.info(f"Cyber RSS: {len(new_items)} new items.")

    # ── Alert sender ──────────────────────────────────────────────────────────
    def _send_cve_alert(self, cve):
        msg = (
            f"🔴 *CRITICAL CVE ALERT*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 `{cve['id']}`\n"
            f"📊 CVSS: `{cve['cvss_score']}` — *{cve['severity']}*\n"
            f"📅 Published: `{cve['published']}`\n"
            f"🖥 Affected: `{', '.join(cve['affected'][:3]) or 'see NVD'}`\n"
            f"📝 {cve['description'][:200]}\n"
            f"🔗 https://nvd.nist.gov/vuln/detail/{cve['id']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ *Patch immediately. Verify vendor advisories.*"
        )
        logger.warning(f"CRITICAL CVE: {cve['id']} CVSS:{cve['cvss_score']}")
        if self.notify:
            try:
                self.notify(msg, is_text=True)
            except Exception as e:
                logger.debug(f"CVE alert send error: {e}")

    # ── Report builder ────────────────────────────────────────────────────────
    def _build_report(self):
        with self._lock:
            cves  = list(self._cve_store[:30])
            feeds = list(self._feed_items[:30])

        severity_counts = defaultdict(int)
        for cve in cves:
            severity_counts[cve["severity"]] += 1

        self._report_cache = {
            "scan_count":      self._scan_count,
            "total_cves":      self._total_cves,
            "severity_counts": dict(severity_counts),
            "recent_cves":     cves[:10],
            "recent_feeds":    feeds[:15],
            "ts":              datetime.utcnow().isoformat(),
        }

    def get_report(self):
        return self._report_cache.copy()

    # ── Formatted report string ───────────────────────────────────────────────
    def format_report(self, max_cves=6, max_news=5):
        r = self._report_cache
        if not r:
            return "🔐 No cyber intelligence data yet. Scan in progress..."

        ts         = r.get("ts", "")[:19].replace("T", " ")
        sc         = r.get("severity_counts", {})
        lines = [
            "🔐 *CYBER INTELLIGENCE REPORT*",
            f"🕐 `{ts} UTC` | Scan #{r.get('scan_count', 0)}",
            f"📊 CVEs tracked: *{r.get('total_cves', 0)}*",
            f"🔴 Critical: {sc.get('CRITICAL', 0)} | "
            f"🟠 High: {sc.get('HIGH', 0)} | "
            f"🟡 Medium: {sc.get('MEDIUM', 0)} | "
            f"🟢 Low: {sc.get('LOW', 0)}",
            "━" * 35,
        ]

        # Recent CVEs
        recent_cves = r.get("recent_cves", [])
        if recent_cves:
            lines.append("\n🆔 *RECENT CVEs*")
            for cve in recent_cves[:max_cves]:
                sev_icon = {
                    "CRITICAL": "🔴", "HIGH": "🟠",
                    "MEDIUM":   "🟡", "LOW": "🟢"
                }.get(cve.get("severity", ""), "⚪")
                lines.append(
                    f"{sev_icon} `{cve['id']}` CVSS:{cve.get('cvss_score', 'N/A')} "
                    f"— {cve['description'][:70]}"
                )

        # Recent security news
        recent_feeds = r.get("recent_feeds", [])
        if recent_feeds:
            lines.append("\n📰 *SECURITY NEWS*")
            shown = set()
            count = 0
            for item in recent_feeds:
                if count >= max_news:
                    break
                title = item["title"][:80]
                if title in shown:
                    continue
                shown.add(title)
                sev_icon = {
                    "CRITICAL": "🔴", "HIGH": "🟠",
                    "MEDIUM":   "🟡"
                }.get(item.get("severity"), "📌")
                lines.append(f"{sev_icon} {title} _({item['source']})_")
                count += 1

        lines.append("\n━" + "━" * 34)
        lines.append("🛡 *All content is for defensive security awareness.*")
        return "\n".join(lines)

    def format_owasp(self):
        """Format OWASP Top 10 as a readable message."""
        lines = ["🔐 *OWASP TOP 10 — 2021*", "━" * 35]
        for code, entry in OWASP_TOP_10.items():
            lines.append(f"\n*{code}: {entry['name']}*")
            lines.append(f"🛡 Defense: _{entry['defense'][:100]}_")
        return "\n".join(lines)

    def format_tool(self, tool_name):
        """Format a security tool entry."""
        tool = self.get_tool_info(tool_name)
        if not tool:
            return f"Tool `{tool_name}` not found. Available: {', '.join(SECURITY_TOOLS_KB.keys())}"
        lines = [
            f"🔧 *{tool_name.upper()}*",
            f"📋 Purpose: {tool['purpose']}",
            f"🔎 Category: {tool['category']}",
            f"🛡 Defense: {tool['defense']}",
        ]
        return "\n".join(lines)

    def format_pentest_phases(self):
        """Format pentest methodology for educational display."""
        lines = ["🔐 *PENTEST METHODOLOGY — DEFENSIVE OVERVIEW*", "━" * 35]
        for phase in PENTEST_METHODOLOGY["phases"]:
            lines.append(f"\n*{phase['phase']}*")
            lines.append(f"🔎 Techniques: {', '.join(phase['techniques'][:4])}")
            lines.append(f"🛡 Defense: _{phase['defense'][:120]}_")
        lines.append("\n_All phases described for defensive awareness and authorized testing only._")
        return "\n".join(lines)

    def _trim_seen(self):
        if len(self._seen) > 15000:
            lst        = list(self._seen)
            self._seen = set(lst[-8000:])

    def stats(self):
        return {
            "scan_count":   self._scan_count,
            "total_cves":   self._total_cves,
            "feed_items":   len(self._feed_items),
            "running":      self._running,
            "feeds_active": len(CYBER_RSS_FEEDS),
        }
