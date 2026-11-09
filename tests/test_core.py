"""Pruebas con fixtures locales: ninguna toca la red ni el hardware real."""
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

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


def test_resolver_tiene_espera_maxima(monkeypatch):
    """Un resolver colgado no puede congelar el escaneo: espera acotada y sigue."""
    def cuelgue(ip):
        time.sleep(4)  # resolver que no responde a tiempo
        return ("tarde", [], [ip])
    monkeypatch.setattr(classifier.socket, "gethostbyaddr", cuelgue)
    inicio = time.time()
    resultado = resolve_hostnames_parallel(["10.0.0.1", "10.0.0.2"], timeout=1.0)
    duracion = time.time() - inicio
    assert duracion < 3.0, f"la espera no estuvo acotada: {duracion:.2f}s"
    assert resultado == {"10.0.0.1": "Desconocido", "10.0.0.2": "Desconocido"}


def test_resolver_bloqueado_no_cuelga_el_proceso():
    """Proceso completo: un resolver colgado para siempre no puede impedir
    que el programa termine (no basta con que la función retorne)."""
    script = textwrap.dedent(
        """
        import socket, sys, time
        from src import classifier

        def cuelgue_eterno(ip):
            time.sleep(120)
            return ("nunca", [], [ip])

        socket.gethostbyaddr = cuelgue_eterno
        t0 = time.monotonic()
        res = classifier.resolve_hostnames_parallel(
            ["10.9.9.1", "10.9.9.2"], max_workers=4, timeout=1.0)
        el = time.monotonic() - t0
        assert el < 5, f"la funcion no retorno a tiempo: {el:.2f}s"
        assert res == {"10.9.9.1": "Desconocido", "10.9.9.2": "Desconocido"}, res
        print("FUNCOk", round(el, 2))
        """
    )
    # timeout=25: si el proceso se cuelga por hilos del resolver, falla aquí.
    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, timeout=25, cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, (
        f"el proceso no termino limpio: rc={proc.returncode} stderr={proc.stderr}"
    )
    assert "FUNCOk" in proc.stdout


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
    assert "32.0 GB" in informe
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


def test_informe_incluye_todos_los_dispositivos(tmp_path):
    net = dict(NET)
    net["devices"] = [dict(NET["devices"][0], ip=f"192.168.1.{i}") for i in range(10, 55)]
    out = tmp_path / "i3.html"
    generate_html_report(SPECS, net, output_path=str(out))
    contenido = out.read_text(encoding="utf-8")
    for i in range(10, 55):
        assert f"192.168.1.{i}" in contenido


def test_informe_es_autocontenido_sin_cdn(informe):
    # El informe no debe depender de recursos externos: tiene que funcionar offline
    for dominio in ("cdn.", "unpkg.com", "googleapis.com", "cdnjs", "jsdelivr"):
        assert dominio not in informe, f"dependencia externa: {dominio}"


def test_informe_topologia_marcada_como_inferida(informe):
    assert "inferido" in informe.lower()
    assert "no representa la topología física real" in informe


# ---------------------------------------------------------------- multiplataforma

IP_ROUTE_LINUX = """default via 192.168.1.1 dev wlan0 proto dhcp src 192.168.1.50 metric 600
192.168.1.0/24 dev wlan0 proto kernel scope link src 192.168.1.50 metric 600
10.8.0.0/24 via 192.168.1.254 dev wlan0
"""

NETSTAT_MACOS = """Routing tables

Internet:
Destination        Gateway            Flags               Netif Expire
default            192.168.1.1        UGScg                 en0
127                127.0.0.1          UCS                   lo0
192.168.1.0/24     link#8             UCS                   en0      !
192.168.1.50       link#8             UHLWIi                en0   1187
"""

IP_NEIGH_LINUX = """192.168.1.1 dev wlan0 lladdr 1c:3b:f3:aa:bb:cc REACHABLE
192.168.1.9 dev wlan0  FAILED
192.168.1.20 dev wlan0 lladdr 00:80:48:11:22:33 STALE
"""

ARP_A_MACOS = """? (192.168.1.1) at 1c:3b:f3:aa:bb:cc on en0 ifscope [ethernet]
? (192.168.1.9) at (incomplete) on en0 ifscope [ethernet]
? (192.168.1.20) at 0:80:48:11:22:33 on en0 ifscope [ethernet]
"""

NMCLI_WIFI = """no:RedVecina:42
yes:MiWifi:78
"""


def test_parse_ip_route_linux():
    from src.network_discovery import _parse_ip_route
    datos = _parse_ip_route(IP_ROUTE_LINUX)
    assert datos["gateways"] == [{"gateway": "192.168.1.1", "interface": "wlan0"}]
    rutas = {(r["destination"], r["netmask"]): r for r in datos["routes"]}
    assert ("192.168.1.0", "255.255.255.0") in rutas
    assert rutas[("10.8.0.0", "255.255.255.0")]["gateway"] == "192.168.1.254"
    assert rutas[("192.168.1.0", "255.255.255.0")]["gateway"] == "On-link"


def test_parse_netstat_macos():
    from src.network_discovery import _parse_netstat_inet
    datos = _parse_netstat_inet(NETSTAT_MACOS)
    assert datos["gateways"] == [{"gateway": "192.168.1.1", "interface": "en0"}]
    # Solo rutas CIDR + default; la ruta de host /32 se ignora
    dests = {r["destination"] for r in datos["routes"]}
    assert "192.168.1.0" in dests and "192.168.1.50" not in dests


def test_parse_ip_neigh_linux():
    from src.network_discovery import _parse_ip_neigh
    devs = _parse_ip_neigh(IP_NEIGH_LINUX)
    assert len(devs) == 2  # la entrada FAILED sin lladdr se omite
    assert devs[0]["mac"] == "1c:3b:f3:aa:bb:cc"
    assert devs[0]["vendor"] == "TP-Link"


def test_parse_arp_a_macos():
    from src.network_discovery import _parse_arp_a_unix
    devs = _parse_arp_a_unix(ARP_A_MACOS)
    ips = {d["ip"] for d in devs}
    assert ips == {"192.168.1.1", "192.168.1.20"}  # incomplete se omite


def test_parse_nmcli_wifi():
    from src.network_discovery import _parse_nmcli_wifi
    assert _parse_nmcli_wifi(NMCLI_WIFI) == {"ssid": "MiWifi", "signal": "78%"}


def test_dispatch_linux_usa_ip_route(monkeypatch):
    monkeypatch.setattr(network_discovery.platform, "system", lambda: "Linux")
    llamados = []
    def falso_run(args, timeout=3):
        llamados.append(args)
        return IP_ROUTE_LINUX if args[0] == "ip" else None
    monkeypatch.setattr(network_discovery, "_run", falso_run)
    datos = network_discovery.get_gateways_and_routes()
    assert datos["gateways"][0]["gateway"] == "192.168.1.1"
    assert ["ip", "route"] in llamados


def test_dispatch_macos_arp(monkeypatch):
    monkeypatch.setattr(network_discovery.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(network_discovery, "_run", lambda args, timeout=3: ARP_A_MACOS)
    devs = network_discovery.get_arp_table()
    assert {d["ip"] for d in devs} == {"192.168.1.1", "192.168.1.20"}


def test_wan_opt_in_no_llama_internet(monkeypatch):
    def prohibido(*a, **k):
        raise AssertionError("sin --wan no debe hablarse con internet")
    monkeypatch.setattr(network_discovery.requests, "get", prohibido)
    monkeypatch.setattr(network_discovery.platform, "system", lambda: "Linux")
    monkeypatch.setattr(network_discovery, "_run", lambda args, timeout=3: IP_ROUTE_LINUX if args == ["ip", "route"] else (IP_NEIGH_LINUX if args == ["ip", "neigh"] else None))
    monkeypatch.setattr(network_discovery, "get_nmap_path", lambda: None)
    monkeypatch.setattr(network_discovery, "scan_subnet_concurrently", lambda *a, **k: [])
    datos = network_discovery.full_network_discovery(include_public_ip=False)
    assert datos["public_ip"] == "No consultada (usa --wan para incluirla)"
    assert any("--wan" in n for n in datos["notes"])


def test_notas_declaran_fuentes_ausentes(monkeypatch):
    monkeypatch.setattr(network_discovery.platform, "system", lambda: "Linux")
    monkeypatch.setattr(network_discovery, "_run", lambda args, timeout=3: None)  # sin herramientas
    monkeypatch.setattr(network_discovery, "get_nmap_path", lambda: None)
    monkeypatch.setattr(network_discovery, "scan_subnet_concurrently", lambda *a, **k: [])
    datos = network_discovery.full_network_discovery()
    assert any("gateway" in n.lower() for n in datos["notes"])
    assert any("vecinos" in n for n in datos["notes"])
    assert any("SSID" in n for n in datos["notes"])


def test_informe_muestra_notas_del_sistema(tmp_path):
    net = dict(NET)
    net["notes"] = ["Nota de prueba: fuente X no disponible en este SO."]
    out = tmp_path / "i4.html"
    generate_html_report(SPECS, net, output_path=str(out))
    assert "Nota de prueba: fuente X no disponible en este SO." in out.read_text(encoding="utf-8")
