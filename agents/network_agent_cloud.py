"""
Helix Mythos — Network Intelligence Agent (Cloud/Linux version)
Uses Linux-compatible commands (ping -c, traceroute).
"""

import socket
import logging
import subprocess
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger("HelixNetworkCloud")


class NetworkAgentCloud:
    def __init__(self, memory):
        self.memory = memory

    def get_local_info(self) -> str:
        try:
            hostname  = socket.gethostname()
            local_ip  = socket.gethostbyname(hostname)
            lines = [
                "🌐 *CLOUD SERVER NETWORK INFO*",
                f"Hostname:  `{hostname}`",
                f"Local IP:  `{local_ip}`",
            ]
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

    def scan_ports(self, host: str, port_range: str = "1-1024") -> str:
        try:
            start_p, end_p = (int(x) for x in port_range.split("-"))
            open_ports = []

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
            total = end_p - start_p + 1
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

    def discover_hosts(self, subnet: str = None) -> str:
        try:
            if subnet is None:
                local_ip = socket.gethostbyname(socket.gethostname())
                parts    = local_ip.split(".")
                subnet   = f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"

            network = ipaddress.ip_network(subnet, strict=False)
            hosts   = list(network.hosts())[:254]
            alive   = []

            def ping(ip):
                try:
                    result = subprocess.run(
                        ["ping", "-c", "1", "-W", "1", str(ip)],
                        capture_output=True, timeout=3
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

    def traceroute(self, host: str) -> str:
        try:
            result = subprocess.run(
                ["traceroute", "-m", "15", host],
                capture_output=True, text=True, timeout=30
            )
            output = result.stdout[:2000]
            return f"🗺 *Traceroute to {host}:*\n```\n{output}\n```"
        except Exception as e:
            return f"Traceroute error: {e}"

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
