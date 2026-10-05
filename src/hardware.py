import platform
import psutil
import socket
import subprocess
import json
import os

def get_system_specs():
    specs = {
        "hostname": socket.gethostname(),
        "fqdn": socket.getfqdn(),
        "os": platform.system() + " " + platform.release() + " (" + platform.version() + ")",
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "cpu_physical_cores": psutil.cpu_count(logical=False),
        "cpu_logical_cores": psutil.cpu_count(logical=True),
        "cpu_freq": None,
        "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        "ram_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
        "ram_percent": psutil.virtual_memory().percent,
        "disks": [],
        "network_interfaces": [],
        "brand": "Unknown",
        "model": "Unknown",
        "dns_servers": []
    }

    # CPU Frequency
    try:
        freq = psutil.cpu_freq()
        if freq:
            specs["cpu_freq"] = f"{freq.current:.2f} MHz"
    except Exception:
        pass

    # Disk partitions
    try:
        for partition in psutil.disk_partitions():
            if 'cdrom' in partition.opts or partition.fstype == '':
                continue
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                specs["disks"].append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "percent": usage.percent
                })
            except Exception:
                continue
    except Exception:
        pass

    # Windows specific: Get Computer Manufacturer and Model via wmic / powershell
    if platform.system() == "Windows":
        try:
            cmd = "wmic csproduct get vendor,name"
            output = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL, timeout=5).decode('utf-8', errors='ignore')
            lines = [line.strip() for line in output.split('\n') if line.strip()]
            if len(lines) >= 2:
                parts = lines[1].split(None, 1)
                if len(parts) >= 1:
                    specs["brand"] = parts[0]
                specs["model"] = lines[1]
        except Exception:
            try:
                # Fallback to PowerShell Get-CimInstance
                cmd = "powershell -Command \"Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer, Model | ConvertTo-Json\""
                output = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL, timeout=5).decode('utf-8', errors='ignore')
                data = json.loads(output)
                if data:
                    specs["brand"] = data.get("Manufacturer", "Unknown")
                    specs["model"] = data.get("Model", "Unknown")
            except Exception:
                pass

        # Get DNS servers via ipconfig /all
        try:
            output = subprocess.check_output("ipconfig /all", shell=True, stderr=subprocess.DEVNULL, timeout=5).decode('utf-8', errors='ignore')
            dns_list = []
            for line in output.split('\n'):
                if "DNS Servers" in line or "Servidores DNS" in line:
                    parts = line.split(":")
                    if len(parts) > 1:
                        dns_list.append(parts[1].strip())
            # Also catch multi-line continuation
            capture = False
            for line in output.split('\n'):
                if "DNS Servers" in line or "Servidores DNS" in line:
                    capture = True
                    parts = line.split(":")
                    if len(parts) > 1 and parts[1].strip():
                        dns_list.append(parts[1].strip())
                    continue
                if capture:
                    stripped = line.strip()
                    if stripped and ("   " in line or line.startswith("    ")) and not ":" in stripped:
                        dns_list.append(stripped)
                    elif stripped and ":" in stripped:
                        capture = False
            specs["dns_servers"] = list(set(dns_list))
        except Exception:
            pass

    # Network interfaces via psutil
    try:
        ifaddrs = psutil.net_if_addrs()
        ifstats = psutil.net_if_stats()
        for interface, addrs in ifaddrs.items():
            if_info = {
                "interface": interface,
                "is_up": ifstats[interface].isup if interface in ifstats else False,
                "speed": ifstats[interface].speed if interface in ifstats else 0,
                "ip_addresses": [],
                "mac_address": None
            }
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    if_info["ip_addresses"].append({
                        "ip": addr.address,
                        "netmask": addr.netmask,
                        "broadcast": addr.broadcast
                    })
                elif addr.family == psutil.AF_LINK:
                    if_info["mac_address"] = addr.address
            specs["network_interfaces"].append(if_info)
    except Exception:
        pass

    return specs

if __name__ == "__main__":
    print(json.dumps(get_system_specs(), indent=2))
