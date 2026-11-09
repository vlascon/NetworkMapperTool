"""Levantamiento equipo por equipo: empresas, levantamientos fechados y
registros de equipos, guardados localmente (offline-first).

Modelo:
    datos/<empresa>/lev_<id>.json   -> un levantamiento por archivo

Reglas de honestidad del modelo:
- El enlace (Wi-Fi/cable) solo se marca como verificado para el PC donde
  corre la colecta; nunca se infiere el medio de OTROS equipos.
- No hay deduplicación silenciosa: merge_equipo exige una decisión del
  operador cuando la coincidencia es ambigua.
- La escritura es atómica (archivo temporal + renombrado) para no corromper
  el levantamiento si el pendrive se retira a la mitad.
- El cifrado de estos archivos queda como capa separada, pendiente de
  aprobación: este módulo guarda en claro y no oculta ese hecho.
"""

import datetime
import platform
import json
import os
import re
import uuid

SCHEMA_VERSION = 1
MAX_IMPORT_BYTES = 5 * 1024 * 1024  # 5 MB: un levantamiento real pesa KB

ESTADOS = ("abierto", "finalizado")


def ahora_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def slugify(nombre):
    slug = re.sub(r"[^\w\-]", "_", nombre.strip(), flags=re.UNICODE)
    return slug[:60] or "sin_nombre"


def ruta_empresa(data_dir, empresa):
    return os.path.join(data_dir, slugify(empresa))


def ruta_levantamiento(data_dir, lev):
    return os.path.join(ruta_empresa(data_dir, lev["empresa"]),
                        f"{lev['levantamiento_id']}.json")


# ---------------------------------------------------------------- creación

def crear_levantamiento(empresa, sede=None):
    return {
        "schema_version": SCHEMA_VERSION,
        "levantamiento_id": f"lev-{uuid.uuid4().hex[:12]}",
        "empresa": empresa.strip(),
        "sede": (sede or "").strip(),
        "creado_en": ahora_iso(),
        "actualizado_en": ahora_iso(),
        "estado": "abierto",
        "equipos": [],
    }


def listar_empresas(data_dir):
    if not os.path.isdir(data_dir):
        return []
    return sorted(d for d in os.listdir(data_dir)
                  if os.path.isdir(os.path.join(data_dir, d)))


def listar_levantamientos(data_dir, empresa):
    carpeta = ruta_empresa(data_dir, empresa)
    if not os.path.isdir(carpeta):
        return []
    resultado = []
    for nombre in sorted(os.listdir(carpeta)):
        if not nombre.endswith(".json"):
            continue
        try:
            with open(os.path.join(carpeta, nombre), encoding="utf-8") as fh:
                lev = json.load(fh)
            if isinstance(lev, dict) and lev.get("levantamiento_id"):
                resultado.append(lev)
        except Exception:
            continue  # archivo corrupto: se ignora al listar, no al importar
    return resultado


# ---------------------------------------------------------------- guardado

def guardar_levantamiento(lev, data_dir):
    """Escritura atómica: temporal en la misma carpeta + renombrado."""
    lev["actualizado_en"] = ahora_iso()
    carpeta = ruta_empresa(data_dir, lev["empresa"])
    os.makedirs(carpeta, exist_ok=True)
    destino = ruta_levantamiento(data_dir, lev)
    temporal = destino + ".tmp"
    with open(temporal, "w", encoding="utf-8") as fh:
        json.dump(lev, fh, ensure_ascii=False, indent=2)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(temporal, destino)
    return destino


def finalizar_levantamiento(lev):
    lev["estado"] = "finalizado"
    return lev


# ---------------------------------------------------------------- equipos

def _normalizar_mac(mac):
    return (mac or "").lower().replace("-", ":")


def macs_de_equipo(equipo):
    macs = set()
    for iface in equipo.get("interfaces", []):
        mac = _normalizar_mac(iface.get("mac"))
        if mac and mac not in ("unknown", "00:00:00:00:00:00"):
            macs.add(mac)
    return macs


def buscar_candidatos(lev, equipo):
    """Coincidencias posibles por MAC o hostname. Nunca fusiona por sí solo."""
    macs_nuevas = macs_de_equipo(equipo)
    host_nuevo = (equipo.get("hostname") or "").lower()
    candidatos = []
    for existente in lev.get("equipos", []):
        motivos = []
        if macs_nuevas & macs_de_equipo(existente):
            motivos.append("MAC coincidente")
        if host_nuevo and host_nuevo == (existente.get("hostname") or "").lower():
            motivos.append("mismo hostname")
        if motivos:
            candidatos.append({"equipo": existente, "motivos": motivos})
    return candidatos


def merge_equipo(lev, equipo, confirmar):
    """Agrega o actualiza un equipo en el levantamiento.

    confirmar: callable(candidatos) -> equipo_id a actualizar, o None para
    registrar como equipo nuevo. Se invoca SIEMPRE que hay candidatos: la
    deduplicación nunca es silenciosa.
    """
    if not equipo.get("equipo_id"):
        equipo["equipo_id"] = f"eq-{uuid.uuid4().hex[:12]}"
    for i, existente in enumerate(lev.get("equipos", [])):
        if existente.get("equipo_id") == equipo["equipo_id"]:
            lev["equipos"][i] = equipo
            return "actualizado"
    candidatos = buscar_candidatos(lev, equipo)
    if candidatos:
        elegido = confirmar(candidatos)
        if elegido:
            for i, existente in enumerate(lev["equipos"]):
                if existente.get("equipo_id") == elegido:
                    equipo["equipo_id"] = elegido
                    lev["equipos"][i] = equipo
                    return "actualizado"
    lev.setdefault("equipos", []).append(equipo)
    return "nuevo"


# ---------------------------------------------------------------- colecta

def _tipo_enlace_principal(nombre_iface, system, net_stats):
    """Determina el medio del enlace principal SOLO para este PC.

    Verificado localmente; nunca se usa para adivinar el medio de otros
    equipos. Devuelve 'wifi', 'cable' o 'desconocido'.
    """
    if not nombre_iface:
        return "desconocido"
    if system == "Linux":
        # /sys/class/net/<iface>/wireless existe solo en interfaces Wi-Fi
        if os.path.isdir(f"/sys/class/net/{nombre_iface}/wireless"):
            return "wifi"
        return "cable"
    if system == "Darwin":
        out = _run_local(["networksetup", "-listallhardwareports"])
        if out:
            actual = None
            for linea in out.splitlines():
                if linea.startswith("Hardware Port:"):
                    actual = linea.split(":", 1)[1].strip()
                elif linea.startswith("Device:"):
                    dev = linea.split(":", 1)[1].strip()
                    if dev == nombre_iface and actual:
                        return "wifi" if "wi-fi" in actual.lower() or "airport" in actual.lower() else "cable"
        return "desconocido"
    if system == "Windows":
        out = _run_local_shell("netsh wlan show interfaces")
        if out and nombre_iface.lower() in out.lower():
            return "wifi"
        # Si hay salida WLAN pero no es esta interfaz, es cable
        return "cable" if out is not None else "desconocido"
    return "desconocido"


def _run_local(args, timeout=3):
    import subprocess
    try:
        return subprocess.check_output(args, stderr=subprocess.DEVNULL,
                                       timeout=timeout).decode("utf-8", errors="ignore")
    except Exception:
        return None


def _run_local_shell(cmd, timeout=3):
    import subprocess
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL,
                                       timeout=timeout).decode("utf-8", errors="ignore")
    except Exception:
        return None


def recolectar_equipo():
    """Recolecta hardware y conexión del PC local. Sin escaneo de subred:
    el levantamiento se construye pasando PC por PC. Lee tabla de vecinos
    como evidencia pasiva (sin barrido activo)."""
    import psutil
    import socket as _socket
    from src.hardware import get_system_specs
    from src import network_discovery as nd

    specs = get_system_specs()
    wifi = nd.get_wifi_ssid()
    rutas = nd.get_gateways_and_routes()
    vecinos = nd.get_arp_table()

    interfaces = []
    stats = psutil.net_if_stats()
    for nombre, addrs in psutil.net_if_addrs().items():
        ipv4 = mac = None
        for addr in addrs:
            if addr.family == _socket.AF_INET:
                ipv4 = addr.address
            elif getattr(psutil, "AF_LINK", None) is not None and addr.family == psutil.AF_LINK:
                mac = addr.address
        st = stats.get(nombre)
        interfaces.append({
            "nombre": nombre,
            "ip": ipv4,
            "mac": (mac or "unknown").lower().replace("-", ":"),
            "activa": bool(st.isup) if st else None,
        })

    gateway = rutas["gateways"][0]["gateway"] if rutas["gateways"] else None
    iface_principal = rutas["gateways"][0]["interface"] if rutas["gateways"] else None
    system = platform.system()
    tipo_enlace = _tipo_enlace_principal(iface_principal, system, stats)

    return {
        "equipo_id": None,  # lo asigna merge_equipo o la colecta previa
        "hostname": specs.get("hostname") or _socket.gethostname(),
        "so": specs.get("os", "Desconocido"),
        "recolectado_en": ahora_iso(),
        "hardware": specs,
        "conexion": {
            "interfaz_principal": iface_principal,
            "tipo": tipo_enlace,          # verificado solo para ESTE PC
            "tipo_verificado": tipo_enlace != "desconocido",
            "wifi": wifi,
            "gateway": gateway,
        },
        "interfaces": interfaces,
        "vecinos": vecinos,               # evidencia pasiva, no topología
        "notas": [],
    }


# ---------------------------------------------------------------- importación

def validar_levantamiento_bytes(data):
    """Validación estricta de un archivo de levantamiento ajeno.

    Devuelve (lev_o_None, errores). Todo lo que entre al consolidador pasa
    por aquí: tamaño, JSON, versión de esquema, campos y tipos.
    """
    errores = []
    if len(data) > MAX_IMPORT_BYTES:
        return None, [f"archivo excede {MAX_IMPORT_BYTES} bytes"]
    try:
        lev = json.loads(data.decode("utf-8"))
    except Exception as exc:
        return None, [f"no es JSON válido: {exc}"]
    if not isinstance(lev, dict):
        return None, ["la raíz no es un objeto"]
    if lev.get("schema_version") != SCHEMA_VERSION:
        errores.append(f"schema_version {lev.get('schema_version')!r} no soportada")
    for campo in ("levantamiento_id", "empresa", "creado_en", "estado"):
        if not isinstance(lev.get(campo), str) or not lev.get(campo):
            errores.append(f"campo '{campo}' ausente o inválido")
    if lev.get("estado") not in ESTADOS:
        errores.append(f"estado {lev.get('estado')!r} inválido")
    equipos = lev.get("equipos")
    if not isinstance(equipos, list):
        errores.append("'equipos' no es una lista")
    else:
        for i, eq in enumerate(equipos):
            if not isinstance(eq, dict) or not isinstance(eq.get("equipo_id"), str):
                errores.append(f"equipo #{i} sin equipo_id válido")
    if errores:
        return None, errores
    return lev, []


def exportar_equipo(lev, equipo_id):
    """Extrae un equipo como archivo independiente para transporte."""
    for eq in lev.get("equipos", []):
        if eq.get("equipo_id") == equipo_id:
            return {
                "schema_version": SCHEMA_VERSION,
                "tipo": "equipo",
                "levantamiento_id": lev["levantamiento_id"],
                "empresa": lev["empresa"],
                "equipo": eq,
            }
    return None
