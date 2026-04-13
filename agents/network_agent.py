"""
Helix Mythos — Network Intelligence Agent
Authorized network reconnaissance, scanning, and WiFi analysis.
FOR AUTHORIZED/OWN NETWORKS ONLY.
"""

import socket
import logging
import threading
import subprocess
import ipaddress
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger("HelixNetwork")


class NetworkAgent:
    def __init__(self, memory):
        self.memory   = memory
        self._results = {}

    # ── Host / Local Info ─────────────────────────────────────────────────────
    def get_local_info(self) -> str:
        try:
            hostname  = socket.gethostname()
            local_ip  = socket.gethostbyname(hostname)
            lines = [
                "🌐 *LOCAL NETWORK INFO*",
                f"Hostname:  `{hostname}`",
                f"Local IP:  `{local_ip}`",
            ]
            # Get all interfaces via socket
            try:
                import psutil
                for iface, addrs in psutil.net_if_addrs().items():
                    for addr in addrs:
                        if addr.family == socket.AF_INET:
                            lines.append(f"Interface: `{iface}` → `{addr.address}`")
            except ImportError:
                pass
            return "\n".join(lines)
        except Exception as e:
            return f"Local info error: {e}"

    # ── Port Scanner ──────────────────────────────────────────────────────────
    def scan_ports(self, host: str, port_range: str = "1-1024") -> str:
        """Scan ports on a target host. Use only on your own devices."""
        try:
            start_p, end_p = (int(x) for x in port_range.split("-"))
            open_ports     = []
            total          = end_p - start_p + 1

            def check_port(port):
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.5)
                result = s.connect_ex((host, port))
                s.close()
                return port if result == 0 else None

            with ThreadPoolExecutor(max_workers=200) as ex:
                futures = {ex.submit(check_port, p): p for p in range(start_p, end_p + 1)}
                for f in as_completed(futures):
                    port = f.result()
                    if port:
                        try:
                            svc = socket.getservbyport(port)
                        except Exception:
                            svc = "unknown"
                        open_ports.append((port, svc))

            open_ports.sort()
            lines = [
                f"🔍 *Port Scan: {host}*",
                f"Range: {port_range} ({total} ports)",
                f"Open ports: {len(open_ports)}\n",
            ]
            for port, svc in open_ports[:30]:
                lines.append(f"  `{port:5d}/tcp` — {svc}")
            if not open_ports:
                lines.append("  No open ports found.")
            self.memory.append_log({"event": "port_scan", "host": host, "open": len(open_ports)})
            return "\n".join(lines)
        except Exception as e:
            return f"Port scan error: {e}"

    # ── Network Discovery (ping sweep) ────────────────────────────────────────
    def discover_hosts(self, subnet: str = None) -> str:
        """Discover live hosts on the local network."""
        try:
            if subnet is None:
                # Auto-detect local subnet
                local_ip = socket.gethostbyname(socket.gethostname())
                parts    = local_ip.split(".")
                subnet   = f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"

            network = ipaddress.ip_network(subnet, strict=False)
            hosts   = list(network.hosts())[:254]
            alive   = []

            def ping(ip):
                try:
                    result = subprocess.run(
                        ["ping", "-n", "1", "-w", "300", str(ip)],
                        capture_output=True, timeout=2
                    )
                    return str(ip) if result.returncode == 0 else None
                except Exception:
                    return None

            with ThreadPoolExecutor(max_workers=50) as ex:
                futures = [ex.submit(ping, ip) for ip in hosts]
                for f in as_completed(futures):
                    r = f.result()
                    if r:
                        alive.append(r)

            alive.sort(key=lambda ip: [int(x) for x in ip.split(".")])

            lines = [
                f"📡 *Network Discovery: {subnet}*",
                f"Scanned: {len(hosts)} addresses",
                f"Live hosts: {len(alive)}\n",
            ]
            for ip in alive:
                try:
                    hostname = socket.gethostbyaddr(ip)[0]
                except Exception:
                    hostname = "unknown"
                lines.append(f"  `{ip:16s}` — {hostname}")

            if not alive:
                lines.append("  No live hosts found.")

            self.memory.append_log({"event": "host_discovery", "subnet": subnet, "found": len(alive)})
            return "\n".join(lines)
        except Exception as e:
            return f"Discovery error: {e}"

    # ── WiFi Scanner ──────────────────────────────────────────────────────────
    def scan_wifi(self) -> str:
        """Scan visible WiFi networks using Windows netsh."""
        try:
            result = subprocess.run(
                ["netsh", "wlan", "show", "networks", "mode=Bssid"],
                capture_output=True, text=True, timeout=15
            )
            output = result.stdout

            if not output.strip():
                return "⚠️ No WiFi interface found or WiFi is off."

            lines   = ["📶 *WIFI NETWORK SCAN*\n"]
            current = {}
            networks = []

            for line in output.split("\n"):
                line = line.strip()
                if line.startswith("SSID") and "BSSID" not in line:
                    if current:
                        networks.append(current)
                    current = {"ssid": line.split(":", 1)[-1].strip()}
                elif "Signal" in line:
                    current["signal"] = line.split(":", 1)[-1].strip()
                elif "Authentication" in line:
                    current["auth"] = line.split(":", 1)[-1].strip()
                elif "Radio type" in line:
                    current["radio"] = line.split(":", 1)[-1].strip()
                elif "BSSID" in line and "BSSID" not in current.get("ssid", ""):
                    current["bssid"] = line.split(":", 1)[-1].strip()

            if current:
                networks.append(current)

            for i, net in enumerate(networks[:20], 1):
                ssid   = net.get("ssid",   "Hidden")
                signal = net.get("signal", "?")
                auth   = net.get("auth",   "?")
                radio  = net.get("radio",  "?")
                bssid  = net.get("bssid",  "?")
                lines.append(
                    f"*{i}. {ssid}*\n"
                    f"   Signal: {signal} | Auth: {auth}\n"
                    f"   Radio: {radio} | BSSID: `{bssid}`"
                )

            lines.append(f"\n📊 Total networks found: {len(networks)}")
            self.memory.append_log({"event": "wifi_scan", "found": len(networks)})
            return "\n".join(lines)
        except Exception as e:
            return f"WiFi scan error: {e}"

    # ── DNS Lookup ────────────────────────────────────────────────────────────
    def dns_lookup(self, domain: str) -> str:
        try:
            ip   = socket.gethostbyname(domain)
            info = socket.gethostbyaddr(ip)
            return (
                f"🔎 *DNS Lookup: {domain}*\n"
                f"IP:       `{ip}`\n"
                f"Hostname: `{info[0]}`\n"
                f"Aliases:  {', '.join(info[1]) or 'none'}"
            )
        except Exception as e:
            return f"DNS lookup failed: {e}"

    # ── Traceroute ────────────────────────────────────────────────────────────
    def traceroute(self, host: str) -> str:
        try:
            result = subprocess.run(
                ["tracert", "-d", "-h", "15", host],
                capture_output=True, text=True, timeout=30
            )
            output = result.stdout[:2000]
            return f"🗺 *Traceroute to {host}:*\n```\n{output}\n```"
        except Exception as e:
            return f"Traceroute error: {e}"

    # ── Connection Monitor ────────────────────────────────────────────────────
    def active_connections(self) -> str:
        try:
            import psutil
            conns = psutil.net_connections(kind="inet")
            lines = ["🔌 *ACTIVE CONNECTIONS*\n"]
            seen  = set()
            for c in conns[:25]:
                if c.status == "ESTABLISHED" and c.raddr:
                    key = f"{c.raddr.ip}:{c.raddr.port}"
                    if key not in seen:
                        seen.add(key)
                        try:
                            host = socket.gethostbyaddr(c.raddr.ip)[0][:30]
                        except Exception:
                            host = c.raddr.ip
                        lines.append(f"  `{c.laddr.port}` → `{host}:{c.raddr.port}`")
            if len(lines) == 1:
                lines.append("  No established connections found.")
            return "\n".join(lines)
        except Exception as e:
            return f"Connection monitor error: {e}"

    # ── My public IP ──────────────────────────────────────────────────────────
    def get_public_ip(self) -> str:
        try:
            import requests
            data = requests.get("https://ipapi.co/json/", timeout=8).json()
            return (
                f"🌍 *Public IP Info*\n"
                f"IP:       `{data.get('ip')}`\n"
                f"City:     {data.get('city')}\n"
                f"Country:  {data.get('country_name')}\n"
                f"ISP:      {data.get('org')}\n"
                f"Timezone: {data.get('timezone')}"
            )
        except Exception as e:
            return f"Public IP lookup failed: {e}"
