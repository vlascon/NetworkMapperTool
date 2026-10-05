import datetime
import json

def generate_html_report(system_specs, network_data, output_path="network_report.html"):
    scan_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    devices = network_data.get("devices", [])
    gateways = network_data.get("gateways", [])
    wifi = network_data.get("wifi", {})
    public_ip = network_data.get("public_ip", "N/A")
    subnets = network_data.get("subnets_scanned", [])
    routes = network_data.get("routes", [])

    local_hostname = system_specs.get('hostname', 'Desconocido')
    primary_gateway = gateways[0] if gateways else {"gateway": "No detectado", "hostname": "N/A", "device_type": "ISP Router / Gateway"}

    # Count device types
    type_counts = {}
    for d in devices:
        dt = d.get("device_type", "Unknown")
        type_counts[dt] = type_counts.get(dt, 0) + 1

    # Build Mermaid diagram lines
    mermaid_lines = ["graph TD"]
    mermaid_lines.append(f'    Internet["🌐 Internet / WAN<br>IP: {public_ip}<br>Tipo: Red WAN<br>Host: Cloud/Public"]')
    
    gw_ip = primary_gateway.get('gateway', 'N/A')
    gw_host = primary_gateway.get('hostname', 'Desconocido')
    mermaid_lines.append(f'    Gateway["🛜 Router / Gateway LAN<br>IP: {gw_ip}<br>Host: {gw_host}<br>Tipo: ISP Router / Gateway"] --> Internet')
    
    local_ip = "127.0.0.1"
    for iface in system_specs.get('network_interfaces', []):
        for addr in iface.get('ip_addresses', []):
            if not addr.get('ip', '').startswith('127.'):
                local_ip = addr.get('ip')
                break
        if local_ip != "127.0.0.1":
            break

    mermaid_lines.append(f'    LocalHost["💻 Computador Anfitrión<br>IP: {local_ip}<br>Host: {local_hostname}<br>Tipo: Computador Local"] --> Gateway')

    for idx, dev in enumerate(devices[:20]):
        dev_ip = dev.get('ip', 'N/A')
        dev_host = dev.get('hostname', 'Desconocido')
        dev_type = dev.get('device_type', 'Dispositivo')
        dev_id = f"dev_{idx}"
        mermaid_lines.append(f'    {dev_id}["🖥️ {dev_type}<br>IP: {dev_ip}<br>Host: {dev_host}<br>Tipo: {dev_type}"] --> Gateway')

    mermaid_chart = "\n".join(mermaid_lines)

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Informe Completo de Topología de Red e Inventario</title>
    <script src="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body {{ background-color: #f3f4f6; font-family: system-ui, -apple-system, sans-serif; }}
        .card {{ background: white; border-radius: 0.75rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }}
    </style>
    <script>
        document.addEventListener("DOMContentLoaded", function() {{
            mermaid.initialize({{ startOnLoad: true, theme: 'neutral' }});
        }});
    </script>
</head>
<body class="text-gray-800 antialiased">
    <div class="max-w-7xl mx-auto px-4 py-8">
        
        <!-- Header -->
        <div class="bg-gradient-to-r from-blue-700 to-indigo-800 text-white p-8 rounded-2xl shadow-lg mb-8">
            <div class="flex flex-col md:flex-row justify-between items-start md:items-center">
                <div>
                    <h1 class="text-3xl font-extrabold tracking-tight mb-2"><i class="fas fa-network-wired mr-3"></i>Mapa de Red e Inventario de Hardware</h1>
                    <p class="text-blue-200 text-sm">Generado el {scan_time} | Host Anfitrión: <span class="font-semibold text-white">{local_hostname}</span></p>
                </div>
                <div class="mt-4 md:mt-0 bg-blue-900 bg-opacity-60 px-4 py-3 rounded-xl border border-blue-500 text-right">
                    <p class="text-xs text-blue-300">IP Pública (WAN) | Tipo: Router WAN | Host: Internet</p>
                    <p class="text-xl font-bold font-mono text-green-300">{public_ip}</p>
                </div>
            </div>
        </div>

        <!-- Summary Cards -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div class="card p-6 border-l-4 border-blue-600">
                <div class="flex justify-between items-center">
                    <div>
                        <p class="text-xs text-gray-500 font-semibold uppercase">Dispositivos en Red</p>
                        <p class="text-2xl font-bold mt-1">{len(devices)}</p>
                    </div>
                    <div class="bg-blue-100 p-3 rounded-full text-blue-600"><i class="fas fa-laptop-house text-xl"></i></div>
                </div>
            </div>
            <div class="card p-6 border-l-4 border-green-600">
                <div class="flex justify-between items-center">
                    <div>
                        <p class="text-xs text-gray-500 font-semibold uppercase">Gateway / Router LAN</p>
                        <p class="text-base font-bold mt-1 font-mono">{primary_gateway.get('gateway')}</p>
                        <p class="text-xs text-gray-500 mt-0.5">Tipo: ISP Router / Gateway<br>Host: {primary_gateway.get('hostname', 'Desconocido')}</p>
                    </div>
                    <div class="bg-green-100 p-3 rounded-full text-green-600"><i class="fas fa-router text-xl"></i></div>
                </div>
            </div>
            <div class="card p-6 border-l-4 border-indigo-600">
                <div class="flex justify-between items-center">
                    <div>
                        <p class="text-xs text-gray-500 font-semibold uppercase">Wi-Fi SSID</p>
                        <p class="text-lg font-bold mt-1 truncate max-w-xs">{wifi.get('ssid', 'N/A')}</p>
                    </div>
                    <div class="bg-indigo-100 p-3 rounded-full text-indigo-600"><i class="fas fa-wifi text-xl"></i></div>
                </div>
            </div>
            <div class="card p-6 border-l-4 border-purple-600">
                <div class="flex justify-between items-center">
                    <div>
                        <p class="text-xs text-gray-500 font-semibold uppercase">Segmentos Subred</p>
                        <p class="text-2xl font-bold mt-1">{len(subnets)}</p>
                    </div>
                    <div class="bg-purple-100 p-3 rounded-full text-purple-600"><i class="fas fa-sitemap text-xl"></i></div>
                </div>
            </div>
        </div>

        <!-- Section: Network Topology Diagram -->
        <div class="card p-8 mb-8">
            <h2 class="text-2xl font-bold mb-4 text-gray-900 border-b pb-3 flex items-center">
                <i class="fas fa-project-diagram text-blue-600 mr-3"></i> 0. Diagrama de Topología de Red
            </h2>
            <p class="text-sm text-gray-600 mb-4">Representación visual interactiva de la red (permite hacer zoom con botones o rueda del ratón y arrastrar para mover):</p>
            
            <div class="flex flex-wrap items-center justify-between bg-gray-100 p-3 rounded-lg mb-4 border">
                <div class="space-x-2 mb-2 sm:mb-0">
                    <button onclick="zoomIn()" class="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-semibold shadow transition"><i class="fas fa-search-plus mr-1"></i> Acercar (+)</button>
                    <button onclick="zoomOut()" class="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-semibold shadow transition"><i class="fas fa-search-minus mr-1"></i> Alejar (-)</button>
                    <button onclick="resetZoom()" class="px-3 py-1.5 bg-gray-600 hover:bg-gray-700 text-white rounded text-xs font-semibold shadow transition"><i class="fas fa-redo mr-1"></i> Restablecer</button>
                </div>
                <span class="text-xs text-gray-500 font-mono">Zoom actual: <span id="zoomLevel">100%</span></span>
            </div>

            <div id="diagramContainer" class="bg-gray-50 p-6 rounded-xl border overflow-auto relative shadow-inner" style="height: 650px; cursor: grab;">
                <div id="mermaidInner" style="transform-origin: top left; transition: transform 0.1s ease; display: inline-block; min-width: 100%;">
                    <div class="mermaid">
{mermaid_chart}
                    </div>
                </div>
            </div>
        </div>

        <script>
            let scale = 1;
            const inner = document.getElementById("mermaidInner");
            const container = document.getElementById("diagramContainer");
            const zoomLabel = document.getElementById("zoomLevel");

            function updateZoom() {
                inner.style.transform = `scale(${scale})`;
                zoomLabel.innerText = Math.round(scale * 100) + '%';
            }

            function zoomIn() {
                scale = Math.min(3.0, scale + 0.15);
                updateZoom();
            }

            function zoomOut() {
                scale = Math.max(0.3, scale - 0.15);
                updateZoom();
            }

            function resetZoom() {
                scale = 1;
                updateZoom();
            }

            // Allow dragging to pan
            let isDragging = false;
            let startX, startY, scrollLeft, scrollTop;

            container.addEventListener('mousedown', (e) => {
                isDragging = true;
                container.style.cursor = 'grabbing';
                startX = e.pageX - container.offsetLeft;
                startY = e.pageY - container.offsetTop;
                scrollLeft = container.scrollLeft;
                scrollTop = container.scrollTop;
            });

            container.addEventListener('mouseleave', () => {
                isDragging = false;
                container.style.cursor = 'grab';
            });

            container.addEventListener('mouseup', () => {
                isDragging = false;
                container.style.cursor = 'grab';
            });

            container.addEventListener('mousemove', (e) => {
                if (!isDragging) return;
                e.preventDefault();
                const x = e.pageX - container.offsetLeft;
                const y = e.pageY - container.offsetTop;
                const walkX = (x - startX);
                const walkY = (y - startY);
                container.scrollLeft = scrollLeft - walkX;
                container.scrollTop = scrollTop - walkY;
            });

            // Mouse wheel zoom
            container.addEventListener('wheel', (e) => {
                e.preventDefault();
                if (e.deltaY < 0) {
                    zoomIn();
                } else {
                    zoomOut();
                }
            }, { passive: false });
        </script>

        <!-- Section 1: Local Computer Inventory -->
        <div class="card p-8 mb-8">
            <h2 class="text-2xl font-bold mb-6 text-gray-900 border-b pb-3 flex items-center">
                <i class="fas fa-desktop text-blue-600 mr-3"></i> 1. Inventario del Computador (Anfitrión)
            </h2>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                <div class="bg-gray-50 p-4 rounded-xl border">
                    <p class="text-xs text-gray-500 font-medium">Nombre de Host / FQDN</p>
                    <p class="text-base font-bold text-gray-800 mt-1">{local_hostname}</p>
                    <p class="text-xs text-gray-400 font-mono mt-0.5">{system_specs.get('fqdn')}</p>
                </div>
                <div class="bg-gray-50 p-4 rounded-xl border">
                    <p class="text-xs text-gray-500 font-medium">Marca y Modelo (Hardware)</p>
                    <p class="text-base font-bold text-gray-800 mt-1">{system_specs.get('brand')} {system_specs.get('model')}</p>
                </div>
                <div class="bg-gray-50 p-4 rounded-xl border">
                    <p class="text-xs text-gray-500 font-medium">Sistema Operativo</p>
                    <p class="text-base font-bold text-gray-800 mt-1">{system_specs.get('os')}</p>
                    <p class="text-xs text-gray-500 mt-0.5">Arquitectura: {system_specs.get('architecture')}</p>
                </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                <div class="bg-gray-50 p-4 rounded-xl border">
                    <p class="text-xs text-gray-500 font-medium">Procesador (CPU)</p>
                    <p class="text-sm font-bold text-gray-800 mt-1">{system_specs.get('processor') or 'Desconocido'}</p>
                    <p class="text-xs text-gray-500 mt-1">Núcleos Físicos: {system_specs.get('cpu_physical_cores')} | Lógicos: {system_specs.get('cpu_logical_cores')}</p>
                </div>
                <div class="bg-gray-50 p-4 rounded-xl border">
                    <p class="text-xs text-gray-500 font-medium">Memoria RAM</p>
                    <p class="text-lg font-bold text-gray-800 mt-1">{system_specs.get('ram_total_gb')} GB Total</p>
                    <p class="text-xs text-gray-500 mt-1">Disponible: {system_specs.get('ram_available_gb')} GB ({system_specs.get('ram_percent')}% en uso)</p>
                </div>
                <div class="bg-gray-50 p-4 rounded-xl border">
                    <p class="text-xs text-gray-500 font-medium">Servidores DNS</p>
                    <div class="mt-1 font-mono text-sm text-gray-800">
                        {"<br>".join(system_specs.get('dns_servers', ['No detectados']))}
                    </div>
                </div>
            </div>

            <!-- Disks -->
            <h3 class="text-lg font-semibold mb-3 text-gray-800"><i class="fas fa-hdd text-gray-500 mr-2"></i> Unidades de Almacenamiento</h3>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
"""
    for disk in system_specs.get("disks", []):
        html_content += f"""
                <div class="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
                    <div class="flex justify-between items-center mb-2">
                        <span class="font-bold font-mono text-blue-600">{disk.get('mountpoint')}</span>
                        <span class="text-xs bg-gray-100 px-2 py-1 rounded text-gray-600">{disk.get('fstype')}</span>
                    </div>
                    <p class="text-sm text-gray-700">Total: <span class="font-semibold">{disk.get('total_gb')} GB</span></p>
                    <p class="text-sm text-gray-700">Libre: <span class="font-semibold text-green-600">{disk.get('free_gb')} GB</span></p>
                    <div class="w-full bg-gray-200 rounded-full h-2.5 mt-3">
                        <div class="bg-blue-600 h-2.5 rounded-full" style="width: {disk.get('percent')}%"></div>
                    </div>
                    <p class="text-xs text-right text-gray-500 mt-1">{disk.get('percent')}% usado</p>
                </div>
"""

    html_content += f"""
            </div>

            <!-- Network Interfaces -->
            <h3 class="text-lg font-semibold mb-3 text-gray-800"><i class="fas fa-network-wired text-gray-500 mr-2"></i> Interfaces de Red Locales</h3>
            <div class="overflow-x-auto">
                <table class="min-w-full divide-y divide-gray-200 text-sm">
                    <thead class="bg-gray-50">
                        <tr>
                            <th class="px-6 py-3 text-left font-medium text-gray-500 uppercase">Interfaz</th>
                            <th class="px-6 py-3 text-left font-medium text-gray-500 uppercase">Estado</th>
                            <th class="px-6 py-3 text-left font-medium text-gray-500 uppercase">Dirección MAC</th>
                            <th class="px-6 py-3 text-left font-medium text-gray-500 uppercase">Direcciones IP / Host / Tipo</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-200 bg-white">
"""
    for iface in system_specs.get("network_interfaces", []):
        status_badge = '<span class="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">Activo</span>' if iface.get('is_up') else '<span class="px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">Inactivo</span>'
        
        ips_detail = []
        for i in iface.get('ip_addresses', []):
            ips_detail.append(f"IP: <span class='font-bold'>{i.get('ip')}</span> (Máscara: {i.get('netmask')})<br><span class='text-xs text-indigo-600'>Tipo: Computador Anfitrión | Host: {local_hostname}</span>")
        ips_str = "<br><hr class='my-1'>".join(ips_detail) or "Sin IP IPv4"

        html_content += f"""
                        <tr>
                            <td class="px-6 py-4 font-medium text-gray-900">{iface.get('interface')}</td>
                            <td class="px-6 py-4">{status_badge}</td>
                            <td class="px-6 py-4 font-mono text-xs">{iface.get('mac_address') or 'N/A'}</td>
                            <td class="px-6 py-4 font-mono text-xs">{ips_str}</td>
                        </tr>
"""

    html_content += f"""
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Section 2: Network Overview & Segments -->
        <div class="card p-8 mb-8">
            <h2 class="text-2xl font-bold mb-6 text-gray-900 border-b pb-3 flex items-center">
                <i class="fas fa-globe text-green-600 mr-3"></i> 2. Topología y Segmentos de Red Detectados
            </h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div class="bg-gray-50 p-5 rounded-xl border">
                    <h3 class="font-bold text-gray-800 mb-2"><i class="fas fa-router text-blue-600 mr-2"></i> Routers / Gateways de Enlace</h3>
                    <ul class="space-y-2">
"""
    for gw in gateways:
        gw_gip = gw.get('gateway')
        gw_ghost = gw.get('hostname', 'Desconocido')
        gw_dtype = gw.get('device_type', 'ISP Router / Gateway')
        html_content += f"""
                        <li class="bg-white p-3 rounded border flex flex-col md:flex-row justify-between items-start md:items-center">
                            <div>
                                <span class="font-mono font-bold text-blue-700">IP: {gw_gip}</span><br>
                                <span class="text-xs text-gray-600">Host: {gw_ghost}</span>
                            </div>
                            <span class="text-xs bg-blue-50 text-blue-600 px-2 py-1 rounded mt-1 md:mt-0">Tipo: {gw_dtype} | Interfaz: {gw.get('interface')}</span>
                        </li>
"""
    html_content += f"""
                    </ul>
                </div>
                <div class="bg-gray-50 p-5 rounded-xl border">
                    <h3 class="font-bold text-gray-800 mb-2"><i class="fas fa-sitemap text-purple-600 mr-2"></i> Segmentos de Subred Escaneados</h3>
                    <ul class="space-y-2">
"""
    for sub in subnets:
        html_content += f"""
                        <li class="bg-white p-3 rounded border font-mono text-sm text-purple-700 font-semibold">
                            <i class="fas fa-network-wired mr-2 text-gray-400"></i>Subred: {sub}
                        </li>
"""
    html_content += f"""
                    </ul>
                </div>
            </div>

            <h3 class="text-lg font-semibold mb-3 text-gray-800"><i class="fas fa-route text-gray-500 mr-2"></i> Tabla de Rutas Activas</h3>
            <div class="overflow-x-auto max-h-60 overflow-y-auto">
                <table class="min-w-full divide-y divide-gray-200 text-xs">
                    <thead class="bg-gray-50 sticky top-0">
                        <tr>
                            <th class="px-4 py-2 text-left font-medium text-gray-500 uppercase">Destino</th>
                            <th class="px-4 py-2 text-left font-medium text-gray-500 uppercase">Máscara</th>
                            <th class="px-4 py-2 text-left font-medium text-gray-500 uppercase">Gateway (IP, Host, Tipo)</th>
                            <th class="px-4 py-2 text-left font-medium text-gray-500 uppercase">Interfaz</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-200 bg-white font-mono">
"""
    for r in routes[:30]: # limit table size
        r_gw = r.get('gateway')
        html_content += f"""
                        <tr>
                            <td class="px-4 py-2">{r.get('destination')}</td>
                            <td class="px-4 py-2">{r.get('netmask')}</td>
                            <td class="px-4 py-2 text-blue-600">IP: {r_gw}<br><span class="text-xs text-gray-500">Tipo: Gateway / Router | Host: Desconocido</span></td>
                            <td class="px-4 py-2">{r.get('interface')}</td>
                        </tr>
"""
    html_content += f"""
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Section 3: Discovered Devices Table -->
        <div class="card p-8 mb-8">
            <div class="flex flex-col md:flex-row justify-between items-center mb-6 border-b pb-3">
                <h2 class="text-2xl font-bold text-gray-900 flex items-center">
                    <i class="fas fa-laptop-code text-indigo-600 mr-3"></i> 3. Dispositivos Conectados Descubiertos ({len(devices)})
                </h2>
                <div class="mt-2 md:mt-0">
                    <input type="text" id="searchBox" placeholder="Filtrar por IP, Host, Marca..." class="px-4 py-2 border rounded-lg text-sm w-64 focus:outline-none focus:ring-2 focus:ring-indigo-500" onkeyup="filterTable()">
                </div>
            </div>

            <div class="overflow-x-auto">
                <table id="devicesTable" class="min-w-full divide-y divide-gray-200 text-sm">
                    <thead class="bg-gray-50">
                        <tr>
                            <th class="px-6 py-3 text-left font-medium text-gray-500 uppercase">Dirección IP, Host y Tipo</th>
                            <th class="px-6 py-3 text-left font-medium text-gray-500 uppercase">Dirección MAC</th>
                            <th class="px-6 py-3 text-left font-medium text-gray-500 uppercase">Fabricante / Marca (OUI)</th>
                            <th class="px-6 py-3 text-left font-medium text-gray-500 uppercase">Tipo de Dispositivo</th>
                            <th class="px-6 py-3 text-left font-medium text-gray-500 uppercase">Tipo ARP / Estado</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-200 bg-white">
"""
    for dev in devices:
        dt = dev.get('device_type', 'Unknown')
        dev_host = dev.get('hostname', 'Desconocido')
        badge_color = "bg-gray-100 text-gray-800"
        if "Router" in dt:
            badge_color = "bg-green-100 text-green-800 font-bold"
        elif "Printer" in dt:
            badge_color = "bg-yellow-100 text-yellow-800 font-bold"
        elif "Mobile" in dt:
            badge_color = "bg-purple-100 text-purple-800"
        elif "Computer" in dt:
            badge_color = "bg-blue-100 text-blue-800 font-bold"

        html_content += f"""
                        <tr class="hover:bg-gray-50">
                            <td class="px-6 py-4 font-mono text-gray-900">
                                <span class="font-bold">{dev.get('ip')}</span><br>
                                <span class="text-xs text-indigo-600 font-semibold">Host: {dev_host}</span><br>
                                <span class="text-xs text-gray-500">Tipo: {dt}</span>
                            </td>
                            <td class="px-6 py-4 font-mono text-xs text-gray-600">{dev.get('mac')}</td>
                            <td class="px-6 py-4 font-medium text-gray-800">{dev.get('vendor')}</td>
                            <td class="px-6 py-4"><span class="px-2 py-1 text-xs rounded-full {badge_color}">{dt}</span></td>
                            <td class="px-6 py-4 text-xs text-gray-500">{dev.get('type', 'Dinámico')}</td>
                        </tr>
"""

    html_content += f"""
                    </tbody>
                </table>
            </div>
        </div>

    </div>

    <script>
        function filterTable() {{
            const input = document.getElementById("searchBox");
            const filter = input.value.toLowerCase();
            const table = document.getElementById("devicesTable");
            const tr = table.getElementsByTagName("tr");

            for (let i = 1; i < tr.length; i++) {{
                let match = false;
                const td = tr[i].getElementsByTagName("td");
                for (let j = 0; j < td.length; j++) {{
                    if (td[j]) {{
                        if (td[j].innerText.toLowerCase().indexOf(filter) > -1) {{
                            match = true;
                            break;
                        }}
                    }}
                }}
                tr[i].style.display = match ? "" : "none";
            }}
        }}
    </script>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return output_path

if __name__ == "__main__":
    pass
