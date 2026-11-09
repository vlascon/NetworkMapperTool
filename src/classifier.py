import queue
import socket
import threading


def resolve_hostname(ip):
    try:
        hostname, _, _ = socket.gethostbyaddr(ip)
        return hostname
    except Exception:
        return "Desconocido"


def resolve_hostnames_parallel(ips, max_workers=32, timeout=8.0):
    """Resuelve hostnames en paralelo, una sola consulta DNS por IP única.

    La resolución inversa de DNS es la parte más lenta de la clasificación:
    cada consulta puede tardar segundos si no hay respuesta. Resolver en
    paralelo y sin duplicados evita multiplicar esa espera por dispositivo.
    El conjunto completo tiene una espera máxima (`timeout`): las consultas
    que no respondan a tiempo quedan como "Desconocido" y el escaneo sigue.
    """
    unique_ips = []
    seen = set()
    for ip in ips:
        if ip and ip not in seen:
            seen.add(ip)
            unique_ips.append(ip)

    if not unique_ips:
        return {}

    work = queue.Queue()
    for ip in unique_ips:
        work.put(ip)
    results = {}
    lock = threading.Lock()
    stop = threading.Event()
    done = threading.Event()
    remaining = len(unique_ips)

    def worker():
        nonlocal remaining
        while not stop.is_set():
            try:
                ip = work.get_nowait()
            except queue.Empty:
                return
            host = resolve_hostname(ip)
            with lock:
                results[ip] = host
                remaining -= 1
                if remaining == 0:
                    done.set()

    # Hilos daemon a propósito: si el resolver del sistema se bloquea más
    # allá de `timeout`, el hilo queda abandonado pero NO impide que el
    # proceso termine. Un ThreadPoolExecutor no sirve aquí: su atexit
    # espera a todos sus hilos y colgaría la salida del programa.
    for _ in range(min(max_workers, len(unique_ips))):
        threading.Thread(target=worker, daemon=True).start()
    done.wait(timeout)
    stop.set()
    with lock:
        hostnames = dict(results)
    for ip in unique_ips:
        hostnames.setdefault(ip, "Desconocido")
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
