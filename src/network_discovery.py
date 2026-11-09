import os
import platform
import subprocess
import re
import socket
import requests
import psutil
import ipaddress
import concurrent.futures
import shutil

OUI_DATABASE = {
    "00:11:32": "Synology",
    "00:1c:c0": "TP-Link",
    "1c:3b:f3": "TP-Link",
    "50:c7:bf": "TP-Link",
    "64:70:02": "TP-Link",
    "b0:be:76": "TP-Link",
    "e8:94:f6": "TP-Link",
    "f4:ec:38": "TP-Link",
    "00:24:8c": "ASUSTeK",
    "00:1d:60": "ASUSTeK",
    "1c:87:2c": "ASUSTeK",
    "2c:4d:54": "ASUSTeK",
    "f8:32:e4": "ASUSTeK",
    "00:14:bf": "Cisco",
    "00:1b:2a": "Cisco",
    "00:1e:14": "Cisco",
    "00:21:55": "Cisco",
    "00:22:90": "Cisco",
    "68:ef:bd": "Cisco",
    "00:0c:29": "VMware",
    "00:50:56": "VMware",
    "00:15:5d": "Microsoft (Hyper-V)",
    "00:25:9c": "Cisco Linksys",
    "00:1a:2b": "Cisco Linksys",
    "00:18:39": "Netgear",
    "00:1f:33": "Netgear",
    "20:4e:7f": "Netgear",
    "28:c6:8f": "Netgear",
    "84:1b:5e": "Netgear",
    "9c:d3:6d": "Netgear",
    "c4:04:15": "Netgear",
    "e0:91:f5": "Netgear",
    "00:03:7f": "Atheros",
    "00:13:ef": "Intel",
    "00:1e:67": "Intel",
    "00:21:6a": "Intel",
    "00:27:10": "Intel",
    "34:13:e8": "Intel",
    "40:9f:38": "Intel",
    "5c:f9:dd": "Intel",
    "8c:70:5a": "Intel",
    "00:21:cc": "Apple",
    "00:23:df": "Apple",
    "00:25:00": "Apple",
    "00:26:08": "Apple",
    "28:cf:e9": "Apple",
    "3c:07:54": "Apple",
    "40:6c:8f": "Apple",
    "60:33:4b": "Apple",
    "78:4f:43": "Apple",
    "a4:b1:97": "Apple",
    "ac:bc:32": "Apple",
    "bc:67:78": "Apple",
    "f0:24:75": "Apple",
    "00:00:0c": "Cisco",
    "00:1e:8c": "Hewlett Packard",
    "3c:d9:2b": "Hewlett Packard",
    "6c:3b:e5": "Hewlett Packard",
    "78:ac:44": "Hewlett Packard",
    "9c:8e:99": "Hewlett Packard",
    "00:80:48": "Epson",
    "00:00:48": "Epson",
    "00:13:10": "Brother",
    "00:80:77": "Brother",
    "00:26:37": "Brother",
    "00:17:fa": "Samsung",
    "00:21:19": "Samsung",
    "24:4b:fe": "Samsung",
    "34:23:ba": "Samsung",
    "50:85:69": "Samsung",
    "88:32:9b": "Samsung",
    "f4:7b:5e": "Samsung",
    "28:6c:07": "Xiaomi",
    "64:09:80": "Xiaomi",
    "78:11:dc": "Xiaomi",
    "f0:b4:29": "Xiaomi",
    "00:1e:10": "Huawei",
    "00:25:68": "Huawei",
    "00:e0:fc": "Huawei",
    "4c:54:99": "Huawei",
    "c8:d1:5e": "Huawei",
}

def lookup_mac_vendor(mac):
    if not mac or mac == "unknown":
        return "Desconocido"
    clean_mac = mac.lower().replace("-", ":")
    prefix = ":".join(clean_mac.split(":")[:3])
    return OUI_DATABASE.get(prefix, "Desconocido / Otro")

def get_public_ip():
    try:
        resp = requests.get("https://api.ipify.org", timeout=1.5)
        if resp.status_code == 200:
            return resp.text.strip()
    except Exception:
        pass
    return "No disponible (Sin conexión WAN)"


# ---------------------------------------------------------------- multiplataforma
# Cada consulta al SO tiene un parser puro (texto -> datos) para probarse con
# fixtures, y un despachador por plataforma. Si una fuente no existe en el SO,
# se degrada a vacío y full_network_discovery lo declara en "notes".

def _run(args, timeout=3):
    """Ejecuta un comando de solo lectura. Devuelve stdout o None si falta/falla."""
    try:
        out = subprocess.check_output(args, stderr=subprocess.DEVNULL, timeout=timeout)
        return out.decode("utf-8", errors="ignore")
    except Exception:
        return None


def _prefix_to_netmask(prefix):
    try:
        return str(ipaddress.ip_network(f"0.0.0.0/{int(prefix)}").netmask)
    except Exception:
        return "255.255.255.255"


def _parse_ip_route(text):
    """Salida de `ip route` (Linux)."""
    gateways, routes = [], []
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "default" and "via" in parts:
            gw = parts[parts.index("via") + 1]
            iface = parts[parts.index("dev") + 1] if "dev" in parts else "?"
            routes.append({"destination": "0.0.0.0", "netmask": "0.0.0.0",
                           "gateway": gw, "interface": iface})
            if gw not in [g["gateway"] for g in gateways]:
                gateways.append({"gateway": gw, "interface": iface})
        elif re.match(r"^\d{1,3}(\.\d{1,3}){3}/\d{1,2}$", parts[0]):
            dest, prefix = parts[0].split("/")
            gw = parts[parts.index("via") + 1] if "via" in parts else "On-link"
            iface = parts[parts.index("dev") + 1] if "dev" in parts else "?"
            routes.append({"destination": dest, "netmask": _prefix_to_netmask(prefix),
                           "gateway": gw, "interface": iface})
    return {"gateways": gateways, "routes": routes}


def _parse_netstat_inet(text):
    """Salida de `netstat -rn -f inet` (macOS)."""
    gateways, routes = [], []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        dest, gw, iface = parts[0], parts[1], parts[3]
        if dest == "default" and re.match(r"^\d{1,3}(\.\d{1,3}){3}$", gw):
            routes.append({"destination": "0.0.0.0", "netmask": "0.0.0.0",
                           "gateway": gw, "interface": iface})
            if gw not in [g["gateway"] for g in gateways]:
                gateways.append({"gateway": gw, "interface": iface})
        elif "/" in dest:
            ip_part, prefix = dest.split("/")
            if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ip_part):
                gw_ok = gw if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", gw) else "On-link"
                routes.append({"destination": ip_part, "netmask": _prefix_to_netmask(prefix),
                               "gateway": gw_ok, "interface": iface})
    return {"gateways": gateways, "routes": routes}


def _parse_ip_neigh(text):
    """Salida de `ip neigh` (Linux): vecinos con MAC conocida."""
    devices = []
    for line in text.splitlines():
        parts = line.split()
        if "lladdr" not in parts or len(parts) < 5:
            continue
        ip = parts[0]
        mac = parts[parts.index("lladdr") + 1]
        iface = parts[parts.index("dev") + 1] if "dev" in parts else "?"
        state = parts[-1] if parts else ""
        if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ip):
            continue
        if not re.match(r"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$", mac):
            continue
        devices.append({
            "ip": ip, "mac": mac.lower(), "type": "dynamic",
            "interface_ip": iface, "vendor": lookup_mac_vendor(mac),
            "status": f"Online (ip neigh: {state})"
        })
    return devices


def _parse_arp_a_unix(text):
    """Salida de `arp -a` formato BSD/macOS: 'host (IP) at MAC on IFACE'.
    macOS imprime las MAC sin relleno de ceros (0:80:48:...): se normalizan."""
    devices = []
    patron = re.compile(r"\((\d{1,3}(?:\.\d{1,3}){3})\) at ([0-9a-fA-F]{1,2}(?::[0-9a-fA-F]{1,2}){5}) on (\S+)")
    for match in patron.finditer(text):
        ip, mac, iface = match.groups()
        mac = ":".join(p.zfill(2) for p in mac.split(":"))
        devices.append({
            "ip": ip, "mac": mac.lower(), "type": "dynamic",
            "interface_ip": iface, "vendor": lookup_mac_vendor(mac),
            "status": "Online (ARP)"
        })
    return devices


def _parse_nmcli_wifi(text):
    """Salida de `nmcli -t -f ACTIVE,SSID,SIGNAL dev wifi`: 'yes:MiRed:80'."""
    for line in text.splitlines():
        parts = line.split(":")
        if len(parts) >= 3 and parts[0].lower() in ("yes", "si", "sí"):
            return {"ssid": parts[1] or "N/A", "signal": parts[2] + "%" if parts[2] else "N/A"}
    return None


def _parse_ssid_lines(text):
    """Salidas tipo 'SSID: valor' (wdutil de macOS, airport -I)."""
    ssid, signal = None, "N/A"
    for line in text.splitlines():
        limpia = line.strip()
        if limpia.startswith("SSID:") and not limpia.startswith("BSSID:"):
            ssid = limpia.split(":", 1)[1].strip()
        elif "agrCtlRSSI:" in limpia:
            signal = limpia.split(":", 1)[1].strip() + " dBm"
    if ssid and ssid != "<redacted>":
        return {"ssid": ssid, "signal": signal}
    return None

def get_wifi_ssid():
    system = platform.system()
    if system == "Windows":
        try:
            output = subprocess.check_output("netsh wlan show interfaces", shell=True, stderr=subprocess.DEVNULL, timeout=2).decode('utf-8', errors='ignore')
            ssid = "Red Cableada / Sin Wi-Fi"
            signal = "N/A"
            for line in output.split('\n'):
                if "SSID" in line and "BSSID" not in line:
                    parts = line.split(":")
                    if len(parts) > 1:
                        ssid = parts[1].strip()
                elif "Signal" in line or "Señal" in line:
                    parts = line.split(":")
                    if len(parts) > 1:
                        signal = parts[1].strip()
            return {"ssid": ssid, "signal": signal}
        except Exception:
            return {"ssid": "N/A (Red cableada o sin WLAN)", "signal": "N/A"}
    if system == "Linux":
        out = _run(["nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL", "dev", "wifi"])
        if out:
            parsed = _parse_nmcli_wifi(out)
            if parsed:
                return parsed
        out = _run(["iwgetid", "-r"])
        if out and out.strip():
            return {"ssid": out.strip(), "signal": "N/A"}
        return {"ssid": "N/A (sin nmcli/iwgetid o sin WLAN en este Linux)", "signal": "N/A"}
    if system == "Darwin":
        out = _run(["wdutil", "info"], timeout=4)
        if out:
            parsed = _parse_ssid_lines(out)
            if parsed:
                return parsed
        airport = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
        out = _run([airport, "-I"])
        if out:
            parsed = _parse_ssid_lines(out)
            if parsed:
                return parsed
        return {"ssid": "N/A (sin wdutil/airport o sin WLAN en este macOS)", "signal": "N/A"}
    return {"ssid": f"N/A (sistema {system} no soportado)", "signal": "N/A"}

def get_gateways_and_routes():
    system = platform.system()
    if system == "Linux":
        out = _run(["ip", "route"])
        if out is not None:
            return _parse_ip_route(out)
        return {"gateways": [], "routes": []}
    if system == "Darwin":
        out = _run(["netstat", "-rn", "-f", "inet"])
        if out is not None:
            return _parse_netstat_inet(out)
        return {"gateways": [], "routes": []}
    # Windows: `route print`
    gateways = []
    routes = []
    try:
        output = subprocess.check_output("route print", shell=True, stderr=subprocess.DEVNULL, timeout=2).decode('utf-8', errors='ignore')
        for line in output.split('\n'):
            line_str = line.strip()
            if not line_str:
                continue
            parts = line_str.split()
            if len(parts) >= 4 and re.match(r"^\d{1,3}(\.\d{1,3}){3}$", parts[0]):
                routes.append({
                    "destination": parts[0],
                    "netmask": parts[1],
                    "gateway": parts[2],
                    "interface": parts[3]
                })
                if parts[2] != "On-link" and parts[2] not in [g["gateway"] for g in gateways]:
                    gateways.append({
                        "gateway": parts[2],
                        "interface": parts[3]
                    })
    except Exception:
        pass
    return {"gateways": gateways, "routes": routes}

def get_arp_table():
    system = platform.system()
    if system == "Linux":
        out = _run(["ip", "neigh"])
        if out is not None:
            return _parse_ip_neigh(out)
        return []
    if system == "Darwin":
        out = _run(["arp", "-a"])
        if out is not None:
            return _parse_arp_a_unix(out)
        return []
    # Windows: `arp -a` con encabezados 'Interface:'
    arp_devices = []
    try:
        output = subprocess.check_output("arp -a", shell=True, stderr=subprocess.DEVNULL, timeout=2).decode('utf-8', errors='ignore')
        current_interface = "Desconocida"
        for line in output.split('\n'):
            line = line.strip()
            if not line:
                continue
            if "Interface:" in line or "Interfaz:" in line:
                parts = line.split(":")
                if len(parts) > 1:
                    current_interface = parts[1].strip().split()[0]
                continue
            parts = line.split()
            if len(parts) >= 3:
                ip = parts[0]
                mac = parts[1]
                mtype = parts[2]
                if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ip) and re.match(r"^([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}$", mac):
                    arp_devices.append({
                        "ip": ip,
                        "mac": mac.lower().replace("-", ":"),
                        "type": mtype,
                        "interface_ip": current_interface,
                        "vendor": lookup_mac_vendor(mac),
                        "status": "Online (ARP)"
                    })
    except Exception:
        pass
    return arp_devices

def ping_sweep_ip(ip_str, timeout=0.3):
    """Prueba conexión TCP rápida en puertos comunes para descubrir hosts activos."""
    for port in (80, 443):
        try:
            # Timeout por socket: no mutar el timeout global del proceso
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            result = s.connect_ex((ip_str, port))
            s.close()
            if result == 0:
                return ip_str
        except Exception:
            pass
    return None

def scan_subnet_concurrently(subnet_str, max_threads=64):
    """ Barre una subred completa en paralelo utilizando hilos para alta velocidad. """
    active_ips = []
    try:
        net = ipaddress.ip_network(subnet_str, strict=False)
        # Limitar a subredes razonables para evitar barridos masivos de /8 públicos
        if net.num_addresses > 4096:
            return active_ips
        
        hosts = [str(ip) for ip in net.hosts()]
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
            results = executor.map(ping_sweep_ip, hosts)
            for ip in results:
                if ip:
                    active_ips.append(ip)
    except Exception:
        pass
    return active_ips

def get_nmap_path():
    # 1. Check system PATH
    path = shutil.which("nmap")
    if path:
        return path
    # 2. Check portable local paths
    local_paths = [
        os.path.abspath("tools/nmap/nmap.exe"),
        os.path.abspath("nmap.exe"),
        "C:\\Program Files\\Nmap\\nmap.exe",
        "C:\\Program Files (x86)\\Nmap\\nmap.exe"
    ]
    for p in local_paths:
        if os.path.exists(p):
            return p
    return None

def run_nmap_scan(subnet_str):
    """ Ejecuta nmap (sistema o portable) para descubrimiento avanzado de la subred. """
    nmap_path = get_nmap_path()
    if not nmap_path:
        return []
    
    discovered = []
    try:
        cmd = [nmap_path, "-sn", subnet_str]
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=15).decode('utf-8', errors='ignore')
        
        current_ip = None
        for line in output.split('\n'):
            if "Nmap scan report for" in line:
                match = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})", line)
                if match:
                    current_ip = match.group(1)
            elif "MAC Address:" in line and current_ip:
                mac_match = re.search(r"([0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2})", line)
                vendor_match = re.search(r"\((.*?)\)", line)
                mac = mac_match.group(1) if mac_match else "unknown"
                vendor = vendor_match.group(1) if vendor_match else lookup_mac_vendor(mac)
                discovered.append({
                    "ip": current_ip,
                    "mac": mac.lower().replace("-", ":"),
                    "type": "dynamic",
                    "interface_ip": "Nmap Scan",
                    "vendor": vendor,
                    "status": "Online (Nmap)"
                })
                current_ip = None
    except Exception:
        pass
    return discovered

def full_network_discovery(include_public_ip=False):
    """Descubrimiento de red local.

    include_public_ip: consultar la IP pública a un servicio externo.
    Por defecto es False: la herramienta no habla con internet salvo que el
    operador lo pida explícitamente (opción --wan).
    """
    wifi_info = get_wifi_ssid()
    public_ip = get_public_ip() if include_public_ip else "No consultada (usa --wan para incluirla)"
    routes_data = get_gateways_and_routes()
    arp_devices = get_arp_table()

    # Declarar qué fuentes no estaban disponibles en este SO: un informe
    # degradado sin aviso es peor que un informe honesto.
    notes = []
    system = platform.system()
    if system != "Windows":
        if not routes_data["gateways"]:
            notes.append(f"Sin gateway detectado en {system}: se intentó '{'ip route' if system == 'Linux' else 'netstat -rn'}'; puede no haber red o faltar la herramienta.")
        if not arp_devices:
            notes.append(f"Tabla de vecinos vacía en {system}: se intentó '{'ip neigh' if system == 'Linux' else 'arp -a'}'; el descubrimiento dependerá del barrido por puertos.")
        if str(wifi_info.get("ssid", "")).startswith("N/A"):
            notes.append(f"SSID Wi-Fi no obtenido en {system}: faltan las herramientas del SO (nmcli/iwgetid o wdutil/airport) o no hay WLAN.")
    if not include_public_ip:
        notes.append("IP pública no consultada: la herramienta no habla con internet salvo que se use --wan.")

    # Recopilar todas las subredes alcanzables (multi-segmento)
    subnets_to_scan = set()
    for interface in psutil.net_if_addrs().values():
        for addr in interface:
            if addr.family == socket.AF_INET:
                ip = addr.address
                netmask = addr.netmask
                if ip and netmask and not ip.startswith("127."):
                    try:
                        iface = ipaddress.ip_interface(f"{ip}/{netmask}")
                        subnets_to_scan.add(str(iface.network))
                    except Exception:
                        pass

    for route in routes_data["routes"]:
        dest = route["destination"]
        mask = route["netmask"]
        if dest != "0.0.0.0" and mask != "255.255.255.255" and dest != "127.0.0.1":
            try:
                net = ipaddress.ip_network(f"{dest}/{mask}", strict=False)
                # Solo subredes locales / privadas o menores a /16
                if net.is_private or net.prefixlen >= 16:
                    subnets_to_scan.add(str(net))
            except Exception:
                pass

    # Intentar escaneo con Nmap si está disponible, o barrido concurrente multipasos
    nmap_devices = []
    nmap_bin = get_nmap_path()
    has_nmap = nmap_bin is not None
    
    device_map = {d["ip"]: d for d in arp_devices}

    for subnet in subnets_to_scan:
        if has_nmap:
            nmap_results = run_nmap_scan(subnet)
            for nd in nmap_results:
                if nd["ip"] not in device_map:
                    device_map[nd["ip"]] = nd
            # Con nmap activo el barrido TCP es redundante en la misma subred:
            # nmap -sn descubre por ARP sin necesitar puertos abiertos.
            continue

        # Barrido concurrente solo cuando no hay nmap disponible
        active_ips = scan_subnet_concurrently(subnet)
        for ip in active_ips:
            if ip not in device_map:
                device_map[ip] = {
                    "ip": ip,
                    "mac": "unknown",
                    "type": "dynamic",
                    "interface_ip": subnet,
                    "vendor": "Desconocido",
                    "status": "Online (Active Sweep)"
                }

    # Asegurar que gateways estén incluidos
    for gw in routes_data["gateways"]:
        gw_ip = gw["gateway"]
        if gw_ip and gw_ip != "0.0.0.0" and gw_ip not in device_map:
            device_map[gw_ip] = {
                "ip": gw_ip,
                "mac": "unknown",
                "type": "gateway",
                "interface_ip": gw["interface"],
                "vendor": "Router / Gateway",
                "status": "Online (Gateway)"
            }

    all_devices = list(device_map.values())

    return {
        "public_ip": public_ip,
        "wifi": wifi_info,
        "gateways": routes_data["gateways"],
        "routes": routes_data["routes"],
        "subnets_scanned": list(subnets_to_scan),
        "nmap_available": has_nmap,
        "devices": all_devices,
        "notes": notes
    }

if __name__ == "__main__":
    import json
    print(json.dumps(full_network_discovery(), indent=2))
