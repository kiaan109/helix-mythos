"""
Helix Mythos — Network Master Agent
Full home network control: ARP scan, device info, OS detect, MAC vendors, blocking.
Works on YOUR local network via the local Helix instance.
"""

import os
import re
import socket
import logging
import subprocess
import threading
import time
import ipaddress
import platform
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

logger = logging.getLogger("HelixNetworkMaster")

IS_WINDOWS = platform.system() == "Windows"

# MAC vendor cache to avoid repeat API calls
_vendor_cache: dict = {}


def _get_mac_vendor(mac: str) -> str:
    """Look up MAC address vendor via macvendors.com (free API)."""
    if not mac or mac == "unknown":
        return "Unknown"
    clean = mac.upper().replace(":", "").replace("-", "")[:6]
    if clean in _vendor_cache:
        return _vendor_cache[clean]
    try:
        r = requests.get(f"https://api.macvendors.com/{mac}", timeout=3)
        vendor = r.text.strip() if r.status_code == 200 else "Unknown"
    except Exception:
        vendor = "Unknown"
    _vendor_cache[clean] = vendor
    return vendor


def _ttl_to_os(ttl: int) -> str:
    """Guess OS from TTL value."""
    if ttl <= 0:
        return "Unknown"
    elif ttl <= 64:
        return "Linux/macOS/Android"
    elif ttl <= 128:
        return "Windows"
    elif ttl <= 255:
        return "Cisco/Network Device"
    return "Unknown"


class NetworkMasterAgent:
    def __init__(self, memory):
        self.memory = memory
        self._blocked_ips: set = set()

    # ── Get local subnet ──────────────────────────────────────────────────────
    def _get_local_subnet(self) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            parts = local_ip.split(".")
            return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24", local_ip
        except Exception:
            return "192.168.1.0/24", "unknown"

    # ── ARP Table (instant — from OS cache) ───────────────────────────────────
    def _get_arp_table(self) -> dict:
        """Read ARP table from OS — returns {ip: mac}."""
        arp = {}
        try:
            if IS_WINDOWS:
                out = subprocess.check_output("arp -a", shell=True, text=True, timeout=10)
                for line in out.splitlines():
                    m = re.search(r"(\d+\.\d+\.\d+\.\d+)\s+([\w-]{17})", line)
                    if m:
                        ip  = m.group(1)
                        mac = m.group(2).replace("-", ":").upper()
                        arp[ip] = mac
            else:
                out = subprocess.check_output(["arp", "-n"], text=True, timeout=10)
                for line in out.splitlines()[1:]:
                    parts = line.split()
                    if len(parts) >= 3 and re.match(r"\d+\.\d+\.\d+\.\d+", parts[0]):
                        arp[parts[0]] = parts[2].upper() if parts[2] != "(incomplete)" else "unknown"
        except Exception as e:
            logger.error(f"ARP table error: {e}")
        return arp

    # ── Ping sweep to populate ARP ────────────────────────────────────────────
    def _ping_sweep(self, subnet: str):
        """Ping all hosts in subnet to populate ARP cache."""
        try:
            network = ipaddress.ip_network(subnet, strict=False)
            hosts   = list(network.hosts())[:254]

            def ping(ip):
                if IS_WINDOWS:
                    cmd = ["ping", "-n", "1", "-w", "300", str(ip)]
                else:
                    cmd = ["ping", "-c", "1", "-W", "1", str(ip)]
                try:
                    subprocess.run(cmd, capture_output=True, timeout=2)
                except Exception:
                    pass

            with ThreadPoolExecutor(max_workers=100) as ex:
                list(ex.map(ping, hosts))
        except Exception as e:
            logger.error(f"Ping sweep error: {e}")

    # ── Get TTL for OS detection ──────────────────────────────────────────────
    def _get_ttl(self, ip: str) -> int:
        try:
            if IS_WINDOWS:
                out = subprocess.check_output(
                    ["ping", "-n", "1", "-w", "500", ip],
                    text=True, timeout=3
                )
                m = re.search(r"TTL=(\d+)", out, re.IGNORECASE)
            else:
                out = subprocess.check_output(
                    ["ping", "-c", "1", "-W", "1", ip],
                    text=True, timeout=3
                )
                m = re.search(r"ttl=(\d+)", out, re.IGNORECASE)
            return int(m.group(1)) if m else 0
        except Exception:
            return 0

    # ── Resolve hostname ──────────────────────────────────────────────────────
    def _resolve_hostname(self, ip: str) -> str:
        try:
            return socket.gethostbyaddr(ip)[0]
        except Exception:
            return "unknown"

    # ── Full Network Scan ─────────────────────────────────────────────────────
    def scan_network(self) -> str:
        """
        Full network scan:
        1. Ping sweep to populate ARP
        2. Read ARP table for MAC addresses
        3. Resolve hostnames
        4. Detect OS via TTL
        5. Look up MAC vendors
        Returns formatted device list.
        """
        subnet, my_ip = self._get_local_subnet()

        # Step 1: ping sweep
        sweep_thread = threading.Thread(target=self._ping_sweep, args=(subnet,))
        sweep_thread.start()
        sweep_thread.join(timeout=15)

        # Step 2: ARP table
        arp = self._get_arp_table()
        if not arp:
            return f"No devices found on {subnet}. Make sure you're on a network."

        # Step 3+4+5: Enrich in parallel
        devices = []

        def enrich(ip, mac):
            hostname = self._resolve_hostname(ip)
            ttl      = self._get_ttl(ip)
            os_guess = _ttl_to_os(ttl)
            vendor   = _get_mac_vendor(mac) if mac != "unknown" else "Unknown"
            is_me    = "← YOU" if ip == my_ip else ""
            return {
                "ip": ip, "mac": mac, "hostname": hostname,
                "os": os_guess, "vendor": vendor, "me": is_me
            }

        with ThreadPoolExecutor(max_workers=30) as ex:
            futures = {ex.submit(enrich, ip, mac): ip for ip, mac in arp.items()}
            for f in as_completed(futures):
                try:
                    devices.append(f.result())
                except Exception:
                    pass

        # Sort by IP
        devices.sort(key=lambda d: [int(x) for x in d["ip"].split(".")])

        lines = [
            f"📡 *NETWORK SCAN — {subnet}*",
            f"My IP: `{my_ip}` | Devices found: *{len(devices)}*",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n",
        ]

        for d in devices:
            os_emoji = {"Windows": "🪟", "Linux/macOS/Android": "🐧", "Cisco/Network Device": "🔀"}.get(d["os"], "❓")
            lines.append(
                f"{os_emoji} `{d['ip']:16s}` {d['me']}\n"
                f"   📛 Hostname: `{d['hostname'][:35]}`\n"
                f"   🏷 MAC: `{d['mac']}` — {d['vendor'][:25]}\n"
                f"   💻 OS: {d['os']}\n"
            )

        self.memory.append_log({"event": "network_scan", "devices": len(devices), "subnet": subnet})
        return "\n".join(lines)

    # ── Block a device (Windows Firewall / iptables) ──────────────────────────
    def block_ip(self, ip: str) -> str:
        """Block all traffic to/from an IP using OS firewall."""
        try:
            # Validate IP
            ipaddress.ip_address(ip)

            if IS_WINDOWS:
                # Windows Firewall — block inbound and outbound
                name_in  = f"HelixBlock_IN_{ip.replace('.','_')}"
                name_out = f"HelixBlock_OUT_{ip.replace('.','_')}"
                subprocess.run(
                    ["netsh", "advfirewall", "firewall", "add", "rule",
                     f"name={name_in}", "dir=in", "action=block",
                     f"remoteip={ip}", "enable=yes"],
                    capture_output=True, timeout=10
                )
                subprocess.run(
                    ["netsh", "advfirewall", "firewall", "add", "rule",
                     f"name={name_out}", "dir=out", "action=block",
                     f"remoteip={ip}", "enable=yes"],
                    capture_output=True, timeout=10
                )
            else:
                # Linux iptables
                subprocess.run(["iptables", "-I", "INPUT",  "-s", ip, "-j", "DROP"], timeout=5)
                subprocess.run(["iptables", "-I", "OUTPUT", "-d", ip, "-j", "DROP"], timeout=5)

            self._blocked_ips.add(ip)
            self.memory.append_log({"event": "block_ip", "ip": ip})
            hostname = self._resolve_hostname(ip)
            return (
                f"🚫 *BLOCKED: {ip}*\n"
                f"Device: `{hostname}`\n"
                f"All traffic to/from this IP is now blocked.\n"
                f"Use /unblock {ip} to restore."
            )
        except Exception as e:
            return f"❌ Block failed: {e}\n_May need admin/root privileges._"

    # ── Unblock a device ──────────────────────────────────────────────────────
    def unblock_ip(self, ip: str) -> str:
        """Remove firewall block for an IP."""
        try:
            ipaddress.ip_address(ip)

            if IS_WINDOWS:
                name_in  = f"HelixBlock_IN_{ip.replace('.','_')}"
                name_out = f"HelixBlock_OUT_{ip.replace('.','_')}"
                subprocess.run(
                    ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={name_in}"],
                    capture_output=True, timeout=10
                )
                subprocess.run(
                    ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={name_out}"],
                    capture_output=True, timeout=10
                )
            else:
                subprocess.run(["iptables", "-D", "INPUT",  "-s", ip, "-j", "DROP"], timeout=5)
                subprocess.run(["iptables", "-D", "OUTPUT", "-d", ip, "-j", "DROP"], timeout=5)

            self._blocked_ips.discard(ip)
            self.memory.append_log({"event": "unblock_ip", "ip": ip})
            return f"✅ *UNBLOCKED: {ip}*\nTraffic restored."
        except Exception as e:
            return f"❌ Unblock failed: {e}"

    # ── List blocked IPs ──────────────────────────────────────────────────────
    def list_blocked(self) -> str:
        if IS_WINDOWS:
            try:
                out = subprocess.check_output(
                    ["netsh", "advfirewall", "firewall", "show", "rule", "name=all"],
                    text=True, timeout=10
                )
                helix_rules = [l for l in out.splitlines() if "HelixBlock" in l]
                ips = set()
                for r in helix_rules:
                    m = re.search(r"HelixBlock_(?:IN|OUT)_(\d+_\d+_\d+_\d+)", r)
                    if m:
                        ips.add(m.group(1).replace("_", "."))
                blocked = sorted(ips)
            except Exception:
                blocked = sorted(self._blocked_ips)
        else:
            blocked = sorted(self._blocked_ips)

        if not blocked:
            return "✅ No devices currently blocked by Helix."
        lines = [f"🚫 *BLOCKED DEVICES ({len(blocked)})*\n"]
        for ip in blocked:
            hostname = self._resolve_hostname(ip)
            lines.append(f"  • `{ip}` — {hostname}")
        lines.append("\n_Use /unblock <ip> to restore._")
        return "\n".join(lines)

    # ── Monitor new devices joining network ───────────────────────────────────
    def watch_new_devices(self, known_ips: set, callback) -> set:
        """Check for new devices since last scan. Calls callback(ip, hostname, mac) for each new one."""
        _, my_ip = self._get_local_subnet()
        self._ping_sweep(self._get_local_subnet()[0])
        arp = self._get_arp_table()
        current_ips = set(arp.keys())
        new_ips = current_ips - known_ips - {my_ip}
        for ip in new_ips:
            mac      = arp.get(ip, "unknown")
            hostname = self._resolve_hostname(ip)
            vendor   = _get_mac_vendor(mac)
            callback(ip, hostname, mac, vendor)
        return current_ips

    # ── WiFi scan (Windows only) ──────────────────────────────────────────────
    def scan_wifi(self) -> str:
        if not IS_WINDOWS:
            return "WiFi scanning via netsh is Windows-only. Use /network for server info."
        try:
            out = subprocess.check_output(
                ["netsh", "wlan", "show", "networks", "mode=Bssid"],
                text=True, timeout=15, encoding="utf-8", errors="replace"
            )
            networks = []
            current  = {}
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("SSID") and "BSSID" not in line:
                    if current:
                        networks.append(current)
                    current = {"ssid": line.split(":", 1)[-1].strip()}
                elif "Authentication" in line:
                    current["auth"] = line.split(":", 1)[-1].strip()
                elif "Signal" in line:
                    current["signal"] = line.split(":", 1)[-1].strip()
                elif "BSSID 1" in line:
                    current["bssid"] = line.split(":", 1)[-1].strip()
            if current:
                networks.append(current)

            lines = [f"📶 *WiFi Networks ({len(networks)} found)*\n"]
            for n in networks[:15]:
                ssid   = n.get("ssid", "Hidden")
                auth   = n.get("auth", "?")
                signal = n.get("signal", "?")
                bssid  = n.get("bssid", "?")
                sec_emoji = "🔒" if "WPA" in auth or "WEP" in auth else "🔓"
                lines.append(
                    f"{sec_emoji} *{ssid}*\n"
                    f"   BSSID: `{bssid}` | Signal: {signal} | Auth: {auth}\n"
                )
            return "\n".join(lines)
        except Exception as e:
            return f"WiFi scan error: {e}"

    # ── Speed test ────────────────────────────────────────────────────────────
    def speed_test(self) -> str:
        try:
            import time
            # Download test using a known large file
            url   = "https://speed.cloudflare.com/__down?bytes=10000000"  # 10MB
            start = time.time()
            r     = requests.get(url, timeout=30, stream=True)
            total = 0
            for chunk in r.iter_content(chunk_size=65536):
                total += len(chunk)
            elapsed  = time.time() - start
            mbps     = (total * 8) / (elapsed * 1_000_000)
            return (
                f"⚡ *Speed Test (Cloudflare)*\n"
                f"Downloaded: {total/1_000_000:.1f} MB in {elapsed:.1f}s\n"
                f"Speed: *{mbps:.1f} Mbps*\n"
                f"{'🟢 Fast' if mbps > 50 else '🟡 Medium' if mbps > 10 else '🔴 Slow'}"
            )
        except Exception as e:
            return f"Speed test error: {e}"

    # ── Router detection ──────────────────────────────────────────────────────
    def find_router(self) -> str:
        try:
            subnet, my_ip = self._get_local_subnet()
            # Router is usually .1 or .254
            base  = ".".join(my_ip.split(".")[:3])
            candidates = [f"{base}.1", f"{base}.254", f"{base}.100"]
            lines = [f"🔀 *Router/Gateway Detection*\n"]
            for ip in candidates:
                try:
                    hostname = socket.gethostbyaddr(ip)[0]
                    ttl      = self._get_ttl(ip)
                    lines.append(f"  ✅ `{ip}` — {hostname} | TTL={ttl}")
                except Exception:
                    # Try ping
                    ttl = self._get_ttl(ip)
                    if ttl > 0:
                        lines.append(f"  ✅ `{ip}` — (no hostname) | TTL={ttl}")
            if len(lines) == 1:
                lines.append("  No common gateway IPs responded.")
            return "\n".join(lines)
        except Exception as e:
            return f"Router detection error: {e}"
