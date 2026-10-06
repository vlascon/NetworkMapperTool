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
    nmap_available = network_data.get("nmap_available", False)

    local_hostname = system_specs.get('hostname', 'Desconocido')
    os_info = system_specs.get('os_info', 'Windows')
    cpu_info = system_specs.get('cpu_info', {})
    ram_info = system_specs.get('ram_info', {})
    disks = system_specs.get('disks', [])
    interfaces = system_specs.get('network_interfaces', [])

    primary_gateway = gateways[0] if gateways else {"gateway": "No detectado", "hostname": "N/A", "device_type": "ISP Router / Gateway"}

    # Count device types
    type_counts = {}
    for d in devices:
        dt = d.get("device_type", "Unknown")
        type_counts[dt] = type_counts.get(dt, 0) + 1

    chart_labels = list(type_counts.keys())
    chart_data = list(type_counts.values())

    # Build Mermaid diagram lines
    mermaid_lines = ["graph TD"]
    mermaid_lines.append(f'    Internet["🌐 Internet / WAN<br>IP: {public_ip}<br>Tipo: Red WAN"]')
    
    gw_ip = primary_gateway.get('gateway', 'N/A')
    gw_host = primary_gateway.get('hostname', 'Desconocido')
    mermaid_lines.append(f'    Gateway["🛜 Router / Gateway LAN<br>IP: {gw_ip}<br>Host: {gw_host}"] --> Internet')
    
    local_ip = "127.0.0.1"
    for iface in interfaces:
        for addr in iface.get('ip_addresses', []):
            if not addr.get('ip', '').startswith('127.'):
                local_ip = addr.get('ip')
                break
        if local_ip != "127.0.0.1":
            break

    mermaid_lines.append(f'    LocalHost["💻 Computador Anfitrión<br>IP: {local_ip}<br>Host: {local_hostname}"] --> Gateway')

    for idx, dev in enumerate(devices[:35]):
        dev_ip = dev.get('ip', 'N/A')
        dev_host = dev.get('hostname', 'Desconocido')
        dev_type = dev.get('device_type', 'Dispositivo')
        dev_id = f"dev_{idx}"
        mermaid_lines.append(f'    {dev_id}["🖥️ {dev_type}<br>IP: {dev_ip}<br>Host: {dev_host}"] --> Gateway')

    mermaid_chart = "\n".join(mermaid_lines)

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NetworkMapperTool - Informe de Red e Inventario</title>
    <script src="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        body {{ font-family: 'Inter', sans-serif; background-color: #0f172a; color: #f8fafc; }}
        .card-glass {{ background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.1); }}
        .table-row-hover:hover {{ background-color: rgba(51, 65, 85, 0.5); }}
    </style>
    <script>
        document.addEventListener("DOMContentLoaded", function() {{
            mermaid.initialize({{ startOnLoad: true, theme: 'dark' }});

            // Chart.js Device Types Breakdown
            const ctx = document.getElementById('deviceChart').getContext('2d');
            new Chart(ctx, {{
                type: 'doughnut',
                data: {{
                    labels: {json.dumps(chart_labels)},
                    datasets: [{{
                        data: {json.dumps(chart_data)},
                        backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6'],
                        borderWidth: 0
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ position: 'bottom', labels: {{ color: '#cbd5e1', font: {{ size: 12 }} }} }}
                    }}
                }}
            }});

            // Real-time Search Filter
            const searchInput = document.getElementById('searchInput');
            const typeFilter = document.getElementById('typeFilter');
            const rows = document.querySelectorAll('.device-row');

            function filterTable() {{
                const query = searchInput.value.toLowerCase();
                const selectedType = typeFilter.value.toLowerCase();

                rows.forEach(row => {{
                    const text = row.innerText.toLowerCase();
                    const type = row.getAttribute('data-type').toLowerCase();
                    const matchesQuery = text.includes(query);
                    const matchesType = !selectedType || type.includes(selectedType);

                    if (matchesQuery && matchesType) {{
                        row.style.display = '';
                    }} else {{
                        row.style.display = 'none';
                    }}
                }});
            }}

            searchInput.addEventListener('input', filterTable);
            typeFilter.addEventListener('change', filterTable);
        }});
    </script>
</head>
<body class="min-h-screen py-8 px-4 sm:px-6 lg:px-8">
    <div class="max-w-7xl mx-auto space-y-8">
        
        <!-- Header -->
        <header class="card-glass rounded-3xl p-8 shadow-2xl relative overflow-hidden">
            <div class="absolute -right-10 -top-10 w-64 h-64 bg-blue-500 opacity-10 rounded-full blur-3xl"></div>
            <div class="flex flex-col md:flex-row justify-between items-start md:items-center relative z-10 gap-6">
                <div>
                    <div class="flex items-center space-x-3 mb-2">
                        <span class="bg-blue-600 text-white p-3 rounded-2xl shadow-lg"><i class="fas fa-network-wired text-2xl"></i></span>
                        <h1 class="text-3xl font-bold tracking-tight text-white">NetworkMapperTool</h1>
                        <span class="bg-blue-900 text-blue-300 text-xs px-3 py-1 rounded-full font-mono border border-blue-700">v1.0.0</span>
                    </div>
                    <p class="text-slate-400 text-sm">Escaneo multi-segmento y diagnóstico avanzado de red e inventario local.</p>
                </div>
                <div class="flex flex-wrap gap-4 items-center">
                    <div class="card-glass px-4 py-3 rounded-2xl border border-slate-700 text-right">
                        <p class="text-xs text-slate-400">IP Pública (WAN)</p>
                        <p class="text-lg font-bold font-mono text-emerald-400">{public_ip}</p>
                    </div>
                    <div class="card-glass px-4 py-3 rounded-2xl border border-slate-700 text-right">
                        <p class="text-xs text-slate-400">Nmap Engine</p>
                        <p class="text-sm font-bold font-mono {'text-emerald-400' if nmap_available else 'text-amber-400'}">{'Activo' if nmap_available else 'Fallback Nativo'}</p>
                    </div>
                    <button onclick="window.print()" class="bg-blue-600 hover:bg-blue-500 text-white px-5 py-3 rounded-2xl font-semibold shadow-lg transition flex items-center space-x-2">
                        <i class="fas fa-print"></i> <span>Imprimir / PDF</span>
                    </button>
                </div>
            </div>
        </header>

        <!-- Summary Cards Grid -->
        <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <div class="card-glass p-6 rounded-3xl border-l-4 border-blue-500 shadow-xl">
                <div class="flex justify-between items-center">
                    <div>
                        <p class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Dispositivos Detectados</p>
                        <p class="text-3xl font-extrabold text-white mt-1">{len(devices)}</p>
                    </div>
                    <div class="bg-blue-500 bg-opacity-20 p-4 rounded-2xl text-blue-400"><i class="fas fa-desktop text-2xl"></i></div>
                </div>
            </div>
            <div class="card-glass p-6 rounded-3xl border-l-4 border-emerald-500 shadow-xl">
                <div class="flex justify-between items-center">
                    <div>
                        <p class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Subredes Escaneadas</p>
                        <p class="text-3xl font-extrabold text-white mt-1">{len(subnets)}</p>
                    </div>
                    <div class="bg-emerald-500 bg-opacity-20 p-4 rounded-2xl text-emerald-400"><i class="fas fa-project-diagram text-2xl"></i></div>
                </div>
            </div>
            <div class="card-glass p-6 rounded-3xl border-l-4 border-amber-500 shadow-xl">
                <div class="flex justify-between items-center">
                    <div>
                        <p class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Wi-Fi SSID</p>
                        <p class="text-lg font-bold text-white mt-1 truncate max-w-[180px]">{wifi.get('ssid', 'N/A')}</p>
                    </div>
                    <div class="bg-amber-500 bg-opacity-20 p-4 rounded-2xl text-amber-400"><i class="fas fa-wifi text-2xl"></i></div>
                </div>
            </div>
            <div class="card-glass p-6 rounded-3xl border-l-4 border-purple-500 shadow-xl">
                <div class="flex justify-between items-center">
                    <div>
                        <p class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Anfitrión Local</p>
                        <p class="text-lg font-bold text-white mt-1 truncate max-w-[180px]">{local_hostname}</p>
                    </div>
                    <div class="bg-purple-500 bg-opacity-20 p-4 rounded-2xl text-purple-400"><i class="fas fa-server text-2xl"></i></div>
                </div>
            </div>
        </section>

        <!-- Main Content Grid: Chart & System Specs -->
        <section class="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <!-- Chart Breakdown -->
            <div class="card-glass p-6 rounded-3xl shadow-xl flex flex-col justify-between">
                <div>
                    <h3 class="text-lg font-bold text-white mb-4 flex items-center"><i class="fas fa-chart-pie mr-2 text-blue-400"></i> Clasificación de Dispositivos</h3>
                    <p class="text-xs text-slate-400 mb-6">Distribución por tipos identificados en el inventario.</p>
                </div>
                <div class="relative h-64 w-full">
                    <canvas id="deviceChart"></canvas>
                </div>
            </div>

            <!-- Host Hardware Specs -->
            <div class="card-glass p-6 rounded-3xl shadow-xl lg:col-span-2 flex flex-col justify-between">
                <div>
                    <h3 class="text-lg font-bold text-white mb-4 flex items-center"><i class="fas fa-microchip mr-2 text-emerald-400"></i> Inventario de Hardware Local ({os_info})</h3>
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
                        <div class="bg-slate-800 bg-opacity-50 p-4 rounded-2xl border border-slate-700">
                            <p class="text-xs text-slate-400 mb-1"><i class="fas fa-microchip mr-1"></i> CPU</p>
                            <p class="text-sm font-semibold text-white">{cpu_info.get('model', 'N/A')}</p>
                            <p class="text-xs text-slate-400 mt-2">Núcleos: <span class="text-white font-mono">{cpu_info.get('cores_physical', 'N/A')} Físicos / {cpu_info.get('cores_logical', 'N/A')} Lógicos</span> | Uso: <span class="text-emerald-400 font-mono">{cpu_info.get('usage_percent', 'N/A')}%</span></p>
                        </div>
                        <div class="bg-slate-800 bg-opacity-50 p-4 rounded-2xl border border-slate-700">
                            <p class="text-xs text-slate-400 mb-1"><i class="fas fa-memory mr-1"></i> Memoria RAM</p>
                            <p class="text-sm font-semibold text-white">{ram_info.get('total_gb', 'N/A')} GB Total</p>
                            <p class="text-xs text-slate-400 mt-2">Disponible: <span class="text-white font-mono">{ram_info.get('available_gb', 'N/A')} GB</span> | Uso: <span class="text-amber-400 font-mono">{ram_info.get('percent', 'N/A')}%</span></p>
                        </div>
                    </div>
                    <!-- Disks -->
                    <div>
                        <p class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Almacenamiento en Discos</p>
                        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
"""

    for disk in disks:
        html_content += f"""
                            <div class="bg-slate-800 bg-opacity-40 p-3 rounded-xl border border-slate-700">
                                <p class="text-xs font-bold text-white">{disk.get('device')} ({disk.get('mountpoint')})</p>
                                <p class="text-xs text-slate-400 mt-1">Total: {disk.get('total_gb')} GB | Libre: <span class="text-emerald-400">{disk.get('free_gb')} GB</span></p>
                                <div class="w-full bg-slate-700 h-1.5 rounded-full mt-2 overflow-hidden">
                                    <div class="bg-blue-500 h-full" style="width: {disk.get('percent', 0)}%"></div>
                                </div>
                            </div>
"""

    html_content += f"""
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- Devices Table Section -->
        <section class="card-glass rounded-3xl shadow-xl overflow-hidden">
            <div class="p-6 border-b border-slate-700 flex flex-col sm:flex-row justify-between items-center gap-4">
                <div>
                    <h3 class="text-xl font-bold text-white flex items-center"><i class="fas fa-list-ul mr-2 text-blue-400"></i> Dispositivos y Hosts Descubiertos</h3>
                    <p class="text-xs text-slate-400 mt-1">Inventario en tiempo real con filtrado instantáneo por IP, Hostname, MAC o Tipo.</p>
                </div>
                <div class="flex flex-wrap gap-3 w-full sm:w-auto">
                    <div class="relative flex-1 sm:w-64">
                        <span class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400"><i class="fas fa-search"></i></span>
                        <input type="text" id="searchInput" placeholder="Buscar dispositivo..." class="w-full pl-10 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-sm focus:outline-none focus:border-blue-500">
                    </div>
                    <select id="typeFilter" class="bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-white text-sm focus:outline-none focus:border-blue-500">
                        <option value="">Todos los Tipos</option>
"""

    for t in chart_labels:
        html_content += f'<option value="{t}">{t}</option>\n'

    html_content += f"""
                    </select>
                </div>
            </div>

            <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse">
                    <thead>
                        <tr class="bg-slate-800 bg-opacity-70 text-slate-400 text-xs uppercase tracking-wider border-b border-slate-700">
                            <th class="py-4 px-6">Dispositivo / Host</th>
                            <th class="py-4 px-6">Dirección IP</th>
                            <th class="py-4 px-6">Dirección MAC</th>
                            <th class="py-4 px-6">Fabricante (Vendor)</th>
                            <th class="py-4 px-6">Clasificación</th>
                            <th class="py-4 px-6">Estado / Origen</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-800 text-sm">
"""

    for dev in devices:
        dev_ip = dev.get("ip", "N/A")
        dev_mac = dev.get("mac", "N/A")
        dev_host = dev.get("hostname", "Desconocido")
        dev_type = dev.get("device_type", "Desconocido")
        dev_vendor = dev.get("vendor", "Desconocido")
        dev_status = dev.get("status", "Online")
        
        badge_color = "bg-blue-900 text-blue-300 border-blue-700"
        if "Router" in dev_type or "Gateway" in dev_type:
            badge_color = "bg-purple-900 text-purple-300 border-purple-700"
        elif "Printer" in dev_type:
            badge_color = "bg-amber-900 text-amber-300 border-amber-700"
        elif "Mobile" in dev_type:
            badge_color = "bg-emerald-900 text-emerald-300 border-emerald-700"

        html_content += f"""
                        <tr class="table-row-hover device-row" data-type="{dev_type}">
                            <td class="py-4 px-6 font-medium text-white flex items-center space-x-3">
                                <span class="w-2.5 h-2.5 rounded-full bg-emerald-400 inline-block"></span>
                                <span>{dev_host}</span>
                            </td>
                            <td class="py-4 px-6 font-mono text-blue-300">{dev_ip}</td>
                            <td class="py-4 px-6 font-mono text-slate-400 text-xs">{dev_mac}</td>
                            <td class="py-4 px-6 text-slate-300">{dev_vendor}</td>
                            <td class="py-4 px-6">
                                <span class="px-3 py-1 rounded-full text-xs font-semibold border {badge_color}">{dev_type}</span>
                            </td>
                            <td class="py-4 px-6 text-xs text-slate-400">
                                <span class="bg-slate-800 px-2.5 py-1 rounded-lg border border-slate-700">{dev_status}</span>
                            </td>
                        </tr>
"""

    html_content += f"""
                    </tbody>
                </table>
            </div>
        </section>

        <!-- Network Topology & Subnets Section -->
        <section class="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <!-- Mermaid Topology -->
            <div class="card-glass p-6 rounded-3xl shadow-xl">
                <h3 class="text-lg font-bold text-white mb-2 flex items-center"><i class="fas fa-sitemap mr-2 text-indigo-400"></i> Topología de Red (Mermaid)</h3>
                <p class="text-xs text-slate-400 mb-6">Esquema jerárquico de conexión WAN, Gateway y dispositivos locales.</p>
                <div class="bg-slate-900 bg-opacity-70 p-4 rounded-2xl border border-slate-800 overflow-x-auto flex justify-center">
                    <div class="mermaid">
{mermaid_chart}
                    </div>
                </div>
            </div>

            <!-- Subnets & Routes -->
            <div class="card-glass p-6 rounded-3xl shadow-xl flex flex-col justify-between">
                <div>
                    <h3 class="text-lg font-bold text-white mb-2 flex items-center"><i class="fas fa-route mr-2 text-teal-400"></i> Subredes y Puertas de Enlace</h3>
                    <p class="text-xs text-slate-400 mb-4">Segmentos analizados en el descubrimiento multi-segmento.</p>
                    
                    <div class="space-y-3 mb-6">
"""

    for sub in subnets:
        html_content += f"""
                        <div class="bg-slate-800 bg-opacity-50 px-4 py-3 rounded-2xl border border-slate-700 flex justify-between items-center">
                            <span class="text-sm font-mono text-emerald-400"><i class="fas fa-network-wired mr-2"></i>{sub}</span>
                            <span class="text-xs bg-slate-900 text-slate-400 px-2.5 py-1 rounded-lg">Subred Activa</span>
                        </div>
"""

    html_content += f"""
                    </div>
                </div>
                <div class="text-xs text-slate-500 border-t border-slate-800 pt-4 flex justify-between items-center">
                    <span>Generado por NetworkMapperTool</span>
                    <span>{scan_time}</span>
                </div>
            </div>
        </section>

        <!-- Footer -->
        <footer class="text-center text-xs text-slate-500 py-6">
            <p>NetworkMapperTool &copy; 2026 - Auditoría y Mapeo de Redes de Alto Rendimiento</p>
        </footer>

    </div>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    return output_path
