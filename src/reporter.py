import datetime
import html


def esc(value):
    """Escapa valores interpolados en el HTML (hostnames y datos de red no son confiables)."""
    if value is None:
        return "N/A"
    return html.escape(str(value))


CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; background: #070d1d; color: #e2e8f0; padding: 24px 16px; }
.wrap { max-width: 1100px; margin: 0 auto; }
.card { background: #0f172a; border: 1px solid #1e293b; border-radius: 16px; padding: 20px; margin-bottom: 20px; }
h1 { font-size: 24px; color: #fff; }
h2 { font-size: 17px; color: #fff; margin-bottom: 10px; }
.sub { color: #94a3b8; font-size: 13px; margin-bottom: 12px; }
.header-top { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 16px; align-items: flex-start; }
.badges { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
.badge { font-size: 12px; padding: 4px 10px; border-radius: 999px; border: 1px solid #334155; background: #1e293b; color: #cbd5e1; }
.badge.ok { color: #34d399; border-color: #065f46; }
.badge.warn { color: #fbbf24; border-color: #92400e; }
.btn { background: #2563eb; color: #fff; border: 0; border-radius: 10px; padding: 9px 16px; font-size: 13px; cursor: pointer; }
.btn:hover { background: #3b82f6; }
.metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }
.metric { background: #0f172a; border: 1px solid #1e293b; border-left: 4px solid #3b82f6; border-radius: 12px; padding: 14px 16px; }
.metric.green { border-left-color: #10b981; } .metric.amber { border-left-color: #f59e0b; } .metric.purple { border-left-color: #a855f7; }
.metric .k { font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: #94a3b8; }
.metric .v { font-size: 22px; font-weight: 700; color: #fff; margin-top: 4px; word-break: break-word; }
.metric .v.small { font-size: 15px; }
ul.obs { margin-left: 18px; } ul.obs li { font-size: 13px; color: #cbd5e1; margin-bottom: 6px; }
/* Topología inferida: cajas y conectores, sin solapes */
.topo { display: flex; flex-direction: column; align-items: center; gap: 0; }
.node { border: 1px solid #334155; border-radius: 12px; padding: 10px 18px; text-align: center; background: #1e293b; }
.node .t { font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: #94a3b8; }
.node .n { font-size: 14px; font-weight: 600; color: #fff; word-break: break-word; }
.node.wan { border-color: #0ea5e9; } .node.gw { border-color: #a855f7; }
.connector { width: 2px; height: 22px; background: #334155; }
.groups { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; width: 100%; margin-top: 8px; }
.group { border: 1px solid #1e293b; border-radius: 12px; padding: 12px; background: #0b1226; }
.group .gt { font-size: 13px; font-weight: 600; color: #fff; margin-bottom: 8px; }
.chip { display: inline-block; font-size: 12px; background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 3px 8px; margin: 2px; color: #cbd5e1; word-break: break-word; }
.chip .ip { color: #7dd3fc; font-family: Consolas, monospace; }
/* Barras de clasificación (sin JS) */
.bar-row { display: grid; grid-template-columns: minmax(140px, 220px) 1fr 48px; gap: 10px; align-items: center; margin-bottom: 8px; font-size: 13px; }
.bar-track { background: #1e293b; border-radius: 6px; height: 14px; overflow: hidden; }
.bar-fill { background: #3b82f6; height: 100%; border-radius: 6px; }
.bar-row:nth-child(4n+2) .bar-fill { background: #10b981; }
.bar-row:nth-child(4n+3) .bar-fill { background: #f59e0b; }
.bar-row:nth-child(4n+4) .bar-fill { background: #a855f7; }
.bar-count { text-align: right; color: #cbd5e1; font-family: Consolas, monospace; }
/* Iconos SVG en línea (sin fuentes emoji externas) */
.ic { width: 18px; height: 18px; vertical-align: -3px; color: #7dd3fc; margin-right: 6px; }
h1 .ic { width: 26px; height: 26px; vertical-align: -5px; }
/* Móvil: nombre en su propia fila y barra a ancho completo */
@media (max-width: 560px) {
  .bar-row { grid-template-columns: 1fr 48px; gap: 6px 10px; }
  .bar-row > span:first-child { grid-column: 1 / -1; }
}
/* Hardware */
.spec-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; }
.spec { background: #0b1226; border: 1px solid #1e293b; border-radius: 12px; padding: 12px 14px; }
.spec .k { font-size: 11px; color: #94a3b8; margin-bottom: 4px; }
.spec .v { font-size: 14px; font-weight: 600; color: #fff; word-break: break-word; }
.spec .d { font-size: 12px; color: #94a3b8; margin-top: 4px; }
.disk-track { background: #1e293b; height: 6px; border-radius: 4px; margin-top: 6px; overflow: hidden; }
.disk-fill { background: #3b82f6; height: 100%; }
/* Tabla */
.toolbar { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 12px; }
.toolbar input, .toolbar select { background: #0b1226; border: 1px solid #334155; border-radius: 10px; color: #fff; padding: 8px 12px; font-size: 13px; }
.toolbar input { flex: 1; min-width: 180px; }
.table-scroll { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: #94a3b8; padding: 10px 12px; border-bottom: 1px solid #1e293b; background: #0b1226; }
td { padding: 10px 12px; border-bottom: 1px solid #16203a; vertical-align: top; }
tr.device-row:hover td { background: #16203a; }
.mono { font-family: Consolas, monospace; }
.ip { color: #7dd3fc; } .mac { color: #64748b; font-size: 12px; }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #34d399; margin-right: 6px; }
.type-badge { display: inline-block; font-size: 11px; font-weight: 600; padding: 3px 9px; border-radius: 999px; border: 1px solid #334155; background: #1e293b; color: #cbd5e1; }
.type-badge.router { color: #c4b5fd; border-color: #6d28d9; } .type-badge.printer { color: #fcd34d; border-color: #92400e; }
.type-badge.mobile { color: #6ee7b7; border-color: #065f46; } .type-badge.nas { color: #f9a8d4; border-color: #9d174d; }
footer { text-align: center; color: #475569; font-size: 12px; padding: 16px 0; }
@media print { body { background: #fff; color: #111; } .card, .metric, .node, .spec, .group { background: #fff; border-color: #ccc; } .btn, .toolbar { display: none; } }
"""


def type_badge_class(dev_type):
    t = dev_type.lower()
    if "router" in t or "gateway" in t:
        return "router"
    if "printer" in t:
        return "printer"
    if "mobile" in t:
        return "mobile"
    if "nas" in t or "server" in t:
        return "nas"
    return ""


def generate_html_report(system_specs, network_data, output_path="network_report.html", scan_duration=None):
    scan_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    devices = network_data.get("devices", [])
    gateways = network_data.get("gateways", [])
    wifi = network_data.get("wifi", {})
    public_ip = network_data.get("public_ip", "N/A")
    subnets = network_data.get("subnets_scanned", [])
    nmap_available = network_data.get("nmap_available", False)

    local_hostname = system_specs.get('hostname', 'Desconocido')
    # Claves reales producidas por src/hardware.get_system_specs()
    os_info = system_specs.get('os', 'Desconocido')
    cpu_model = system_specs.get('processor') or 'N/A'
    cpu_cores_physical = system_specs.get('cpu_physical_cores', 'N/A')
    cpu_cores_logical = system_specs.get('cpu_logical_cores', 'N/A')
    cpu_usage = system_specs.get('cpu_usage_percent')
    cpu_usage_txt = f"{cpu_usage}" if cpu_usage is not None else 'N/A'
    ram_total = system_specs.get('ram_total_gb', 'N/A')
    ram_available = system_specs.get('ram_available_gb', 'N/A')
    ram_percent = system_specs.get('ram_percent', 'N/A')
    disks = system_specs.get('disks', [])

    primary_gateway = gateways[0] if gateways else {"gateway": "No detectado", "hostname": "N/A"}

    # Observaciones accionables para el lector del informe
    observations = []
    no_mac = [d for d in devices if d.get("mac", "unknown") == "unknown"]
    if no_mac:
        observations.append(f"{len(no_mac)} dispositivo(s) detectado(s) solo por puerto abierto, sin MAC: no se pudo identificar fabricante ni tipo. Si nmap está disponible, un nuevo escaneo puede identificarlos.")
    unknown_vendor = [d for d in devices if "desconocido" in str(d.get("vendor", "")).lower() and d.get("mac", "unknown") != "unknown"]
    if unknown_vendor:
        observations.append(f"{len(unknown_vendor)} dispositivo(s) con fabricante fuera de la base OUI local: conviene revisarlos a mano en la tabla.")
    if not gateways:
        observations.append("No se detectó gateway: revisa la tabla de rutas del equipo o si hay conectividad.")
    if not nmap_available:
        observations.append("nmap no está instalado: el descubrimiento se hizo solo por tabla ARP y puertos 80/443, así que pueden faltar dispositivos que no respondan en esos puertos. Instalar nmap mejora la cobertura.")
    if not devices:
        observations.append("No se detectaron dispositivos con este método; eso no significa que la red esté vacía: revisa cobertura (nmap) y permisos.")
    if not observations:
        observations.append("Sin observaciones: todos los dispositivos detectados tienen MAC y fabricante identificados.")
    observations_html = "\n".join(f"                <li>{esc(o)}</li>" for o in observations)

    # Clasificación: barras CSS (sin dependencias)
    type_counts = {}
    for d in devices:
        dt = d.get("device_type", "Unknown")
        type_counts[dt] = type_counts.get(dt, 0) + 1
    chart_labels = list(type_counts.keys())
    max_count = max(type_counts.values()) if type_counts else 1
    bars_html = ""
    for label, count in sorted(type_counts.items(), key=lambda kv: -kv[1]):
        pct = max(4, round(100 * count / max_count))
        bars_html += f"""                <div class="bar-row">
                    <span>{esc(label)}</span>
                    <div class="bar-track"><div class="bar-fill" style="width: {pct}%"></div></div>
                    <span class="bar-count">{count}</span>
                </div>
"""

    # Topología inferida (estática): WAN -> Gateway -> grupos por tipo
    groups_html = ""
    for label, count in sorted(type_counts.items(), key=lambda kv: -kv[1]):
        chips = ""
        for d in devices:
            if d.get("device_type", "Unknown") != label:
                continue
            host = d.get("hostname", "Desconocido")
            ip = d.get("ip", "N/A")
            name = host if host and host != "Desconocido" else "sin nombre"
            chips += f'<span class="chip">{esc(name)} <span class="ip">{esc(ip)}</span></span> '
        groups_html += f"""                <div class="group">
                    <div class="gt">{esc(label)} ({count})</div>
                    <div>{chips}</div>
                </div>
"""

    duration_txt = f" · Escaneo de {scan_duration:.1f} s" if scan_duration is not None else ""

    disks_html = ""
    for disk in disks:
        disks_html += f"""                    <div class="spec">
                        <div class="k">{esc(disk.get('device'))} ({esc(disk.get('mountpoint'))})</div>
                        <div class="d">Total: {esc(disk.get('total_gb'))} GB | Libre: <span style="color:#34d399">{esc(disk.get('free_gb'))} GB</span></div>
                        <div class="disk-track"><div class="disk-fill" style="width: {disk.get('percent', 0)}%"></div></div>
                    </div>
"""

    subnets_html = ""
    for sub in subnets:
        subnets_html += f'<span class="chip"><span class="ip">{esc(sub)}</span> activa</span> '

    filter_options = "".join(f'<option value="{esc(t)}">{esc(t)}</option>' for t in chart_labels)

    rows_html = ""
    for dev in devices:
        dev_ip = dev.get("ip", "N/A")
        dev_mac = dev.get("mac", "N/A")
        dev_host = dev.get("hostname", "Desconocido")
        dev_type = dev.get("device_type", "Desconocido")
        dev_vendor = dev.get("vendor", "Desconocido")
        dev_status = dev.get("status", "Online")
        badge = type_badge_class(dev_type)
        rows_html += f"""                    <tr class="device-row" data-type="{esc(dev_type)}">
                        <td><span class="dot"></span>{esc(dev_host)}</td>
                        <td class="mono ip">{esc(dev_ip)}</td>
                        <td class="mono mac">{esc(dev_mac)}</td>
                        <td>{esc(dev_vendor)}</td>
                        <td><span class="type-badge {badge}">{esc(dev_type)}</span></td>
                        <td><span class="badge">{esc(dev_status)}</span></td>
                    </tr>
"""

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NetworkMapperTool - Informe de Red</title>
    <style>{CSS}</style>
</head>
<body>
<div class="wrap">

    <header class="card">
        <div class="header-top">
            <div>
                <h1><svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3c2.5 2.6 3.9 5.7 3.9 9s-1.4 6.4-3.9 9c-2.5-2.6-3.9-5.7-3.9-9S9.5 5.6 12 3z"/></svg> NetworkMapperTool NOC <span class="badge">v1.2.0</span></h1>
                <p class="sub" style="margin-top:6px">Informe de descubrimiento de red e inventario de hardware · {scan_time}{duration_txt}</p>
            </div>
            <div class="badges">
                <span class="badge">IP pública: <strong class="mono" style="color:#34d399">{esc(public_ip)}</strong></span>
                <span class="badge {'ok' if nmap_available else 'warn'}">nmap: {'activo' if nmap_available else 'no instalado (respaldo nativo)'}</span>
                <button class="btn" onclick="window.print()">Exportar / PDF</button>
            </div>
        </div>
    </header>

    <section class="metrics">
        <div class="metric"><div class="k">Dispositivos detectados</div><div class="v">{len(devices)}</div></div>
        <div class="metric green"><div class="k">Subredes analizadas</div><div class="v">{len(subnets)}</div></div>
        <div class="metric amber"><div class="k">Red Wi-Fi actual</div><div class="v small">{esc(wifi.get('ssid', 'N/A'))}</div></div>
        <div class="metric purple"><div class="k">Anfitrión local</div><div class="v small">{esc(local_hostname)}</div></div>
    </section>

    <section class="card" style="margin-top:20px">
        <h2><svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 9h6M9 13h6M9 17h4"/></svg> Observaciones</h2>
        <ul class="obs">
{observations_html}
        </ul>
    </section>

    <section class="card">
        <h2><svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="5" r="2.2"/><circle cx="5" cy="18" r="2.2"/><circle cx="19" cy="18" r="2.2"/><path d="M10.8 6.8 6.3 16.1M13.2 6.8l4.5 9.3M7.3 18h9.4"/></svg> Mapa de la red (inferido)</h2>
        <p class="sub">Mapa inferido a partir del gateway y los dispositivos detectados: no representa la topología física real (switches, cableado, VLANs).</p>
        <div class="topo">
            <div class="node wan"><div class="t">Internet / WAN</div><div class="n mono">{esc(public_ip)}</div></div>
            <div class="connector"></div>
            <div class="node gw"><div class="t">Gateway / Router</div><div class="n mono">{esc(primary_gateway.get('gateway', 'No detectado'))}</div><div class="t">{esc(primary_gateway.get('hostname', ''))}</div></div>
            <div class="connector"></div>
            <div class="groups">
{groups_html if groups_html else '                <p class="sub">Sin dispositivos detectados para mostrar.</p>'}
            </div>
        </div>
    </section>

    <section class="card">
        <h2><svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20v-7M10 20V4M16 20v-10"/><path d="M2 20h20"/></svg> Clasificación de dispositivos</h2>
        <p class="sub">Cantidad de dispositivos detectados por tipo.</p>
{bars_html if bars_html else '        <p class="sub">Sin datos.</p>'}
    </section>

    <section class="card">
        <h2><svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="12" rx="1.5"/><path d="M9 20h6M12 16v4"/></svg> Inventario de hardware local</h2>
        <p class="sub">{esc(os_info)}</p>
        <div class="spec-grid">
            <div class="spec">
                <div class="k">Procesador</div>
                <div class="v">{esc(cpu_model)}</div>
                <div class="d">Núcleos: {cpu_cores_physical}F / {cpu_cores_logical}L | Carga: {cpu_usage_txt}%</div>
            </div>
            <div class="spec">
                <div class="k">Memoria RAM</div>
                <div class="v">{ram_total} GB</div>
                <div class="d">Libre: {ram_available} GB | Uso: {ram_percent}%</div>
            </div>
{disks_html}
        </div>
    </section>

    <section class="card">
        <h2><svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="1.6" fill="currentColor" stroke="none"/><path d="M8.5 8.5a5 5 0 0 0 0 7M15.5 8.5a5 5 0 0 1 0 7M6 6a9 9 0 0 0 0 12M18 6a9 9 0 0 1 0 12"/></svg> Subredes analizadas</h2>
        <div>{subnets_html if subnets_html else '<span class="sub">Ninguna detectada.</span>'}</div>
    </section>

    <section class="card">
        <h2><svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M8 6h12M8 12h12M8 18h12"/><circle cx="4" cy="6" r="1.2" fill="currentColor" stroke="none"/><circle cx="4" cy="12" r="1.2" fill="currentColor" stroke="none"/><circle cx="4" cy="18" r="1.2" fill="currentColor" stroke="none"/></svg> Inventario de dispositivos detectados</h2>
        <p class="sub">Los que respondieron al descubrimiento; pueden faltar dispositivos (ver Observaciones).</p>
        <div class="toolbar">
            <input type="text" id="searchInput" placeholder="Buscar por nombre, IP, MAC o fabricante...">
            <select id="typeFilter">
                <option value="">Todos los tipos</option>
{filter_options}
            </select>
        </div>
        <div class="table-scroll">
            <table>
                <thead>
                    <tr><th>Dispositivo / Host</th><th>IP</th><th>MAC</th><th>Fabricante</th><th>Clasificación</th><th>Estado / Origen</th></tr>
                </thead>
                <tbody>
{rows_html if rows_html else '                    <tr><td colspan="6" class="sub">Sin dispositivos detectados.</td></tr>'}
                </tbody>
            </table>
        </div>
    </section>

    <footer>NetworkMapperTool v1.2.0 · Informe autocontenido, funciona sin conexión</footer>
</div>
<script>
(function () {{
    var searchInput = document.getElementById('searchInput');
    var typeFilter = document.getElementById('typeFilter');
    var rows = document.querySelectorAll('.device-row');
    function filterTable() {{
        var query = searchInput.value.toLowerCase();
        var selectedType = typeFilter.value.toLowerCase();
        rows.forEach(function (row) {{
            var text = row.innerText.toLowerCase();
            var type = (row.getAttribute('data-type') || '').toLowerCase();
            var show = text.indexOf(query) !== -1 && (!selectedType || type.indexOf(selectedType) !== -1);
            row.style.display = show ? '' : 'none';
        }});
    }}
    searchInput.addEventListener('input', filterTable);
    typeFilter.addEventListener('change', filterTable);
}})();
</script>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return output_path
