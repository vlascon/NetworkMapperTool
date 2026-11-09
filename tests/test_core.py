"""Pruebas con fixtures locales: ninguna toca la red ni el hardware real."""
import time

import pytest

from src import classifier, network_discovery
from src.classifier import classify_device, enhance_device_list, resolve_hostnames_parallel
from src.network_discovery import lookup_mac_vendor, ping_sweep_ip
from src.reporter import generate_html_report


# ---------------------------------------------------------------- vendors

def test_lookup_mac_vendor_conocido():
    assert lookup_mac_vendor("1c:3b:f3:aa:bb:cc") == "TP-Link"


def test_lookup_mac_vendor_formato_guiones():
    assert lookup_mac_vendor("1C-3B-F3-AA-BB-CC") == "TP-Link"


def test_lookup_mac_vendor_desconocido():
    assert lookup_mac_vendor("11:22:33:44:55:66") == "Desconocido / Otro"


def test_lookup_mac_vendor_vacio():
    assert lookup_mac_vendor("") == "Desconocido"
    assert lookup_mac_vendor("unknown") == "Desconocido"


# ---------------------------------------------------------------- clasificación

GATEWAYS = [{"gateway": "192.168.1.1"}]


def dev(ip, vendor="", mac="unknown"):
    return {"ip": ip, "vendor": vendor, "mac": mac}


def test_classify_gateway_por_ip():
    assert classify_device(dev("192.168.1.1", "Cualquiera"), GATEWAYS) == "ISP Router / Gateway"


def test_classify_impresora():
    assert classify_device(dev("192.168.1.20", "Hewlett Packard"), GATEWAYS) == "Printer"


def test_classify_apple():
    assert classify_device(dev("192.168.1.21", "Apple"), GATEWAYS) == "Computer / Apple Device"


def test_classify_synology_es_nas():
    assert classify_device(dev("192.168.1.22", "Synology"), GATEWAYS) == "NAS / Server / Virtual"


def test_classify_sin_mac():
    assert classify_device(dev("192.168.1.23", ""), GATEWAYS) == "Active Host (No MAC)"


def test_classify_desconocido_con_mac():
    d = dev("192.168.1.24", "Fabricante Raro", "aa:bb:cc:dd:ee:ff")
    assert classify_device(d, GATEWAYS) == "Computer / Unknown Device"


# ---------------------------------------------------------------- DNS paralelo

def fake_discovery(n=24):
    return {
        "gateways": [{"gateway": "192.168.1.1"}],
        "devices": [dev(f"192.168.1.{i + 10}", "Xiaomi") for i in range(n)],
    }


def test_enhance_sin_dns_no_llama_resolver(monkeypatch):
    def boom(ip):
        raise AssertionError("no debió resolverse DNS con resolve=False")
    monkeypatch.setattr(classifier.socket, "gethostbyaddr", boom)
    result = enhance_device_list(fake_discovery(), resolve=False)
    assert all(d["hostname"] == "Desconocido" for d in result["devices"])


def test_enhance_dns_paralelo_es_mas_rapido_que_secuencial(monkeypatch):
    """24 resoluciones de 50 ms: secuencial costaría ~1.2 s; en paralelo debe ser mucho menos."""
    def lento(ip):
        time.sleep(0.05)
        return (f"host-{ip}", [], [ip])
    monkeypatch.setattr(classifier.socket, "gethostbyaddr", lento)
    inicio = time.time()
    result = enhance_device_list(fake_discovery(24), resolve=True, max_workers=32)
    duracion = time.time() - inicio
    assert duracion < 0.6, f"DNS paralelo tardó {duracion:.2f}s (secuencial sería ~1.2s)"
    assert result["devices"][0]["hostname"].startswith("host-")


def test_resolver_deduplica_ips(monkeypatch):
    llamadas = []
    def cuenta(ip):
        llamadas.append(ip)
        return ("h", [], [ip])
    monkeypatch.setattr(classifier.socket, "gethostbyaddr", cuenta)
    resolve_hostnames_parallel(["10.0.0.1", "10.0.0.1", "10.0.0.2"])
    assert sorted(llamadas) == ["10.0.0.1", "10.0.0.2"]


def test_resolver_tolerante_a_fallos(monkeypatch):
    def falla(ip):
        raise OSError("sin DNS")
    monkeypatch.setattr(classifier.socket, "gethostbyaddr", falla)
    assert resolve_hostnames_parallel(["10.0.0.9"]) == {"10.0.0.9": "Desconocido"}


# ---------------------------------------------------------------- barrido TCP

class FakeSocket:
    """Simula connect_ex: éxito solo en 10.0.0.5:80."""
    instances = []

    def __init__(self, *args, **kwargs):
        self.timeout = None
        FakeSocket.instances.append(self)

    def settimeout(self, t):
        self.timeout = t

    def connect_ex(self, addr):
        ip, port = addr
        return 0 if (ip, port) == ("10.0.0.5", 80) else 1

    def close(self):
        pass


def test_ping_sweep_usa_timeout_por_socket(monkeypatch):
    def boom(*a):
        raise AssertionError("no debe mutarse el timeout global")
    monkeypatch.setattr(network_discovery.socket, "setdefaulttimeout", boom)
    FakeSocket.instances = []
    monkeypatch.setattr(network_discovery.socket, "socket", FakeSocket)
    assert ping_sweep_ip("10.0.0.5") == "10.0.0.5"
    assert ping_sweep_ip("10.0.0.6") is None
    assert all(s.timeout == 0.3 for s in FakeSocket.instances)


# ---------------------------------------------------------------- informe

SPECS = {
    "hostname": "PC-PRUEBA",
    "os": "Windows 11 (10.0.22631)",
    "processor": "AMD Ryzen 7 5800X",
    "cpu_physical_cores": 8,
    "cpu_logical_cores": 16,
    "cpu_usage_percent": 12.5,
    "ram_total_gb": 32.0,
    "ram_available_gb": 20.5,
    "ram_percent": 36.0,
    "disks": [{"device": "C:\\", "mountpoint": "C:\\", "fstype": "NTFS",
               "total_gb": 476.0, "used_gb": 200.0, "free_gb": 276.0, "percent": 42.0}],
    "network_interfaces": [{"interface": "Ethernet", "is_up": True, "speed": 1000,
                            "ip_addresses": [{"ip": "192.168.1.50", "netmask": "255.255.255.0", "broadcast": "192.168.1.255"}],
                            "mac_address": "1c:3b:f3:00:11:22"}],
}

NET = {
    "public_ip": "200.100.50.25",
    "wifi": {"ssid": "MiWifi", "signal": "80%"},
    "gateways": [{"gateway": "192.168.1.1", "hostname": "router.local", "device_type": "ISP Router / Gateway"}],
    "routes": [],
    "subnets_scanned": ["192.168.1.0/24"],
    "nmap_available": False,
    "devices": [
        {"ip": "192.168.1.20", "mac": "00:80:48:11:22:33", "vendor": "Epson",
         "hostname": "impresora.local", "device_type": "Printer", "status": "Online (ARP)"},
        {"ip": "192.168.1.66", "mac": "unknown", "vendor": "Desconocido",
         "hostname": "<script>alert(1)</script>", "device_type": "Active Host (No MAC)",
         "status": "Online (Active Sweep)"},
    ],
}


@pytest.fixture
def informe(tmp_path):
    out = tmp_path / "informe.html"
    generate_html_report(SPECS, NET, output_path=str(out), scan_duration=3.2)
    return out.read_text(encoding="utf-8")


def test_informe_muestra_hardware_real(informe):
    # Antes del arreglo el informe leía claves inexistentes y mostraba N/A
    assert "AMD Ryzen 7 5800X" in informe
    assert "32.0 GB Total" in informe
    assert "Windows 11" in informe
    assert "12.5%" in informe


def test_informe_escapa_hostname_hostil(informe):
    assert "<script>alert(1)</script>" not in informe
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in informe


def test_informe_tiene_observaciones(informe):
    assert "Observaciones" in informe
    assert "sin MAC" in informe  # detecta el dispositivo solo por puerto abierto
    assert "nmap no está instalado" in informe


def test_informe_muestra_duracion(informe):
    assert "3.2 s" in informe


def test_informe_cierra_script_en_json(tmp_path):
    net = dict(NET)
    net["devices"] = [dict(NET["devices"][1], hostname="x</script><script>bad()")]
    out = tmp_path / "i2.html"
    generate_html_report(SPECS, net, output_path=str(out))
    contenido = out.read_text(encoding="utf-8")
    assert "</script><script>bad()" not in contenido


def test_informe_avisa_truncamiento_topologia(tmp_path):
    net = dict(NET)
    net["devices"] = [dict(NET["devices"][0], ip=f"192.168.1.{i}") for i in range(10, 55)]
    out = tmp_path / "i3.html"
    generate_html_report(SPECS, net, output_path=str(out))
    contenido = out.read_text(encoding="utf-8")
    assert "muestra 40 de 45 dispositivos" in contenido
