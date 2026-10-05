import socket

def resolve_hostname(ip):
    try:
        hostname, _, _ = socket.gethostbyaddr(ip)
        return hostname
    except Exception:
        return "Desconocido"

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

def enhance_device_list(discovery_result):
    gateways = discovery_result.get("gateways", [])
    devices = discovery_result.get("devices", [])
    
    for gw in gateways:
        gw_ip = gw.get("gateway", "")
        gw["hostname"] = resolve_hostname(gw_ip)
        gw["device_type"] = "ISP Router / Gateway"

    enhanced = []
    for dev in devices:
        dev_copy = dict(dev)
        ip = dev_copy.get("ip", "")
        dev_copy["hostname"] = resolve_hostname(ip)
        dev_copy["device_type"] = classify_device(dev_copy, gateways)
        enhanced.append(dev_copy)
    
    discovery_result["devices"] = enhanced
    discovery_result["gateways"] = gateways
    return discovery_result
