import os
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

def get_wifi_ssid():
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

def get_gateways_and_routes():
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

def ping_sweep_ip(ip_str):
    """Realiza un ping rápido por socket o ping ICMP para descubrir hosts activos."""
    try:
        # Prueba rápida de conexión TCP en puertos comunes o socket connect
        socket.setdefaulttimeout(0.3)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = s.connect_ex((ip_str, 80))
        s.close()
        if result == 0:
            return ip_str
        
        # Fallback a puerto 443 o 135
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result2 = s.connect_ex((ip_str, 443))
        s.close()
        if result2 == 0:
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

def full_network_discovery():
    wifi_info = get_wifi_ssid()
    public_ip = get_public_ip()
    routes_data = get_gateways_and_routes()
    arp_devices = get_arp_table()

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
        
        # Barrido concurrente complementario en subredes locales
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
        "devices": all_devices
    }

if __name__ == "__main__":
    import json
    print(json.dumps(full_network_discovery(), indent=2))
