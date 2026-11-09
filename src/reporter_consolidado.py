"""Informe consolidado de un levantamiento (HTML autocontenido, sin CDN).

Reglas de honestidad obligatorias:
- La conexion (Wi-Fi/cable) es VERIFICADA solo en el PC donde se recolecto
  cada equipo; se muestra con esa etiqueta, nunca como topologia general.
- La agrupacion por gateway/SSID es EVIDENCIA INFERIDA, no prueba de que
  los equipos compartan el mismo segmento fisico.
- Los datos en desarrollo van en claro; se declara en el propio informe.
"""
from datetime import datetime


def esc(texto):
    if texto is None:
        return ""
    return (
        str(texto)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _fmt_fecha(iso):
    if not iso:
        return "desconocido"
    try:
        return datetime.fromisoformat(str(iso).replace("Z", "+00:00")).strftime(
            "%Y-%m-%d %H:%M"
        )
    except ValueError:
        return str(iso)


def _mac_principal(eq):
    conexion = eq.get("conexion") or {}
    principal = conexion.get("interfaz_principal")
    interfaces = eq.get("interfaces") or []
    for it in interfaces:
        if principal and it.get("nombre") == principal:
            return it.get("mac") or "—"
    for it in interfaces:
        if it.get("activa") and it.get("mac") and it["mac"] != "unknown":
            return it["mac"]
    return "—"


def _fila_equipo(eq):
    conexion = eq.get("conexion") or {}
    wifi = conexion.get("wifi") or {}
    tipo = conexion.get("tipo")
    if conexion.get("tipo_verificado") and tipo in ("wifi", "ethernet"):
        etiqueta = "Wi-Fi" if tipo == "wifi" else "Cable"
        conexion_html = f'{etiqueta} <span class="badge ok">verificado en ese PC</span>'
    else:
        conexion_html = 'Desconocido <span class="badge warn">no verificado</span>'
    return (
        "<tr>"
        f"<td>{esc(eq.get('hostname'))}</td>"
        f"<td>{esc(eq.get('so') or 'desconocido')}</td>"
        f"<td>{conexion_html}</td>"
        f"<td>{esc(wifi.get('ssid') or '—')}</td>"
        f"<td>{esc(conexion.get('gateway') or '—')}</td>"
        f"<td>{esc(_mac_principal(eq))}</td>"
        f"<td>{esc(_fmt_fecha(eq.get('recolectado_en')))}</td>"
        "</tr>"
    )


def generate_consolidated_report(lev, output_path):
    empresa = esc(lev.get("empresa") or "Sin empresa")
    estado = esc(lev.get("estado") or "abierto")
    sede = esc(lev.get("sede") or "")
    equipos = list(lev.get("equipos") or [])
    generado = datetime.now().strftime("%Y-%m-%d %H:%M")

    filas = "".join(_fila_equipo(eq) for eq in equipos) or (
        '<tr><td colspan="7" class="muted">Sin equipos recolectados aun.</td></tr>'
    )

    # Agrupacion inferida por (gateway, ssid) declarada como evidencia.
    grupos = {}
    for eq in equipos:
        conexion = eq.get("conexion") or {}
        wifi = conexion.get("wifi") or {}
        clave = (conexion.get("gateway") or "sin gateway", wifi.get("ssid") or "")
        grupos.setdefault(clave, []).append(eq.get("hostname") or "?")
    bloques_grupos = []
    for (gw, ssid), hosts in sorted(grupos.items()):
        etiqueta = esc(gw) + (f' · SSID "{esc(ssid)}"' if ssid else "")
        chips = "".join(f'<span class="chip">{esc(h)}</span>' for h in hosts)
        bloques_grupos.append(
            f'<div class="grupo"><div class="grupo-titulo">{etiqueta}'
            f' <span class="badge warn">agrupacion inferida</span></div>'
            f'<div class="chips">{chips}</div></div>'
        )
    seccion_grupos = "".join(bloques_grupos) or (
        '<p class="muted">Sin datos suficientes para agrupar.</p>'
    )

    css = """
:root{--bg:#0f172a;--card:#1e293b;--text:#e2e8f0;--muted:#94a3b8;
--accent:#38bdf8;--ok:#4ade80;--warn:#fbbf24;--border:#334155}
*{margin:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);
font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;padding:1rem}
.wrap{max-width:960px;margin:auto}
header h1{font-size:1.4rem;color:var(--accent)}
header .sub{color:var(--muted);font-size:.85rem;margin-top:.3rem}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;
padding:1.2rem;margin-top:1rem}
h2{font-size:1.05rem;color:var(--accent);margin-bottom:.8rem}
table{width:100%;border-collapse:collapse;font-size:.88rem}
th,td{padding:.5rem .6rem;text-align:left;border-bottom:1px solid var(--border)}
th{color:var(--muted);font-weight:600}
.badge{display:inline-block;padding:.1rem .5rem;border-radius:999px;
font-size:.7rem;margin-left:.3rem}
.badge.ok{background:rgba(74,222,128,.15);color:var(--ok)}
.badge.warn{background:rgba(251,191,36,.15);color:var(--warn)}
.chip{display:inline-block;background:var(--bg);border:1px solid var(--border);
border-radius:8px;padding:.15rem .55rem;font-size:.78rem;margin:.15rem}
.grupo{margin-bottom:.8rem}
.grupo-titulo{font-size:.9rem;margin-bottom:.3rem}
.muted{color:var(--muted)}
ul.notas{padding-left:1.2rem;font-size:.88rem;color:var(--muted)}
ul.notas li{margin:.35rem 0}
"""

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Levantamiento {empresa}</title>
<style>{css}</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>Levantamiento — {empresa}</h1>
  <div class="sub">
    {('Sede: ' + sede + ' · ') if sede else ''}Estado: {estado} ·
    Equipos: {len(equipos)} · Generado: {esc(generado)}
  </div>
</header>
<div class="card">
  <h2>Equipos recolectados</h2>
  <table>
    <thead><tr>
      <th>Hostname</th><th>SO</th><th>Conexion</th><th>Wi-Fi SSID</th>
      <th>Gateway</th><th>MAC</th><th>Recolectado</th>
    </tr></thead>
    <tbody>{filas}</tbody>
  </table>
</div>
<div class="card">
  <h2>Agrupacion por red (inferida)</h2>
  {seccion_grupos}
</div>
<div class="card">
  <h2>Notas y limites</h2>
  <ul class="notas">
    <li>La conexion (Wi-Fi/cable) es verificada solo en el PC donde se
    recolecto cada equipo; no es una topologia de la red completa.</li>
    <li>La agrupacion por gateway/SSID es evidencia inferida: no demuestra
    que los equipos compartan el mismo segmento fisico (pueden existir
    VLANs o SSID repetidos entre sedes).</li>
    <li>Cada equipo se capturo en su propia fecha; los datos pueden
    corresponder a momentos distintos.</li>
    <li>Los datos de este levantamiento aun se almacenan en claro (etapa de
    desarrollo); el cifrado esta pendiente de decision.</li>
  </ul>
</div>
</div>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return output_path
