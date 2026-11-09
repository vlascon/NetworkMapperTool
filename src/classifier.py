import concurrent.futures
import socket


def resolve_hostname(ip):
    try:
        hostname, _, _ = socket.gethostbyaddr(ip)
        return hostname
    except Exception:
        return "Desconocido"


def resolve_hostnames_parallel(ips, max_workers=32):
    """Resuelve hostnames en paralelo, una sola consulta DNS por IP única.

    La resolución inversa de DNS es la parte más lenta de la clasificación:
    cada consulta puede tardar segundos si no hay respuesta. Resolver en
    paralelo y sin duplicados evita multiplicar esa espera por dispositivo.
    """
    unique_ips = []
    seen = set()
    for ip in ips:
        if ip and ip not in seen:
            seen.add(ip)
            unique_ips.append(ip)

    if not unique_ips:
        return {}

    hostnames = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(resolve_hostname, unique_ips)
        for ip, hostname in zip(unique_ips, results):
            hostnames[ip] = hostname
    return hostnames


def classify_device(device, gateways):
    ip = device.get("ip", "")
    vendor = device.get("vendor", "").lower()
    mac = device.get("mac", "")

    gateway_ips = [g["gateway"] for g in gateways]

    # 1. Router / Gateway check
    if ip in gateway_ips:
        return "ISP Router / Gateway"

    # 2. Printer check
    printer_keywords = ["brother", "hp", "hewlett packard", "epson", "canon", "xerox", "lexmark"]
    if any(kw in vendor for kw in printer_keywords):
        return "Printer"

    # 3. Mobile check
    mobile_keywords = ["apple", "samsung", "xiaomi", "huawei", "oneplus", "motorola", "google"]
    if any(kw in vendor for kw in mobile_keywords):
        if "apple" in vendor:
            return "Computer / Apple Device"
        return "Mobile Device"

    # 4. Networking equipment
    network_keywords = ["cisco", "netgear", "tp-link", "asus", "synology", "vmware", "microsoft"]
    if any(kw in vendor for kw in network_keywords):
        if "synology" in vendor or "vmware" in vendor:
            return "NAS / Server / Virtual"
        if "cisco" in vendor or "tp-link" in vendor or "netgear" in vendor:
            return "Router / Switch / AP"
        return "Computer / Hardware"

    if mac == "unknown":
        return "Active Host (No MAC)"

    return "Computer / Unknown Device"


def enhance_device_list(discovery_result, resolve=True, max_workers=32):
    """Clasifica dispositivos y resuelve hostnames.

    Con resolve=False no se hace ninguna consulta DNS (modo rápido).
    """
    gateways = discovery_result.get("gateways", [])
    devices = discovery_result.get("devices", [])

    if resolve:
        ips = [g.get("gateway", "") for g in gateways]
        ips += [d.get("ip", "") for d in devices]
        hostnames = resolve_hostnames_parallel(ips, max_workers=max_workers)
    else:
        hostnames = {}

    for gw in gateways:
        gw["hostname"] = hostnames.get(gw.get("gateway", ""), "Desconocido")
        gw["device_type"] = "ISP Router / Gateway"

    enhanced = []
    for dev in devices:
        dev_copy = dict(dev)
        ip = dev_copy.get("ip", "")
        dev_copy["hostname"] = hostnames.get(ip, "Desconocido")
        dev_copy["device_type"] = classify_device(dev_copy, gateways)
        enhanced.append(dev_copy)

    discovery_result["devices"] = enhanced
    discovery_result["gateways"] = gateways
    return discovery_result
