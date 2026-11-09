import argparse
import os
import sys
import time
import webbrowser
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.prompt import Confirm, Prompt

from src.hardware import get_system_specs
from src.network_discovery import full_network_discovery
from src.classifier import enhance_device_list
from src.reporter import generate_html_report
from src import levantamiento as lv

console = Console()

DEFAULT_OUTPUT = "Mapa_Red_Inventario.html"
DEFAULT_DATA_DIR = os.path.abspath("datos")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="NetworkMapperTool",
        description="Auditoría de red local: descubrimiento multi-segmento, inventario de hardware e informe HTML."
    )
    parser.add_argument("modo", nargs="?", choices=["escanear", "levantamiento"],
                        help="escanear: descubrir la red desde este PC; levantamiento: construir la red equipo por equipo. Sin argumento se pregunta.")
    parser.add_argument("--output", "-o", default=DEFAULT_OUTPUT,
                        help=f"Ruta del informe HTML (por defecto: {DEFAULT_OUTPUT})")
    parser.add_argument("--no-open", action="store_true",
                        help="No abrir el informe en el navegador al terminar")
    parser.add_argument("--no-dns", action="store_true",
                        help="Omitir resolución de nombres DNS (más rápido, hostnames 'Desconocido')")
    parser.add_argument("--threads", type=int, default=64,
                        help="Hilos para el barrido de subred (por defecto: 64)")
    parser.add_argument("--wan", action="store_true",
                        help="Consultar la IP pública a un servicio externo (por defecto la herramienta no habla con internet)")
    parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR,
                        help="Carpeta de levantamientos (por defecto: ./datos; apunta al pendrive si lo usas)")
    return parser.parse_args(argv)


def _elegir_modo():
    console.print("\n[bold]¿Qué quieres hacer?[/bold]")
    console.print("  [cyan]1[/cyan]) Escanear la red desde este computador (descubrimiento)")
    console.print("  [cyan]2[/cyan]) Levantamiento equipo por equipo (empresa/proyecto, offline)")
    op = Prompt.ask("Elige", choices=["1", "2"], default="1")
    return "escanear" if op == "1" else "levantamiento"


def flujo_levantamiento(data_dir):
    """Colecta este PC dentro de un levantamiento de empresa, offline.

    Los datos se guardan en claro en data_dir (típicamente el pendrive):
    el cifrado es una capa separada pendiente de aprobación del usuario.
    """
    console.print(Panel.fit(
        "[bold cyan]Levantamiento equipo por equipo[/bold cyan]\n"
        "[dim]Los datos se guardan localmente; no se usa internet.[/dim]",
        border_style="cyan"
    ))

    # 1. Empresa/proyecto
    empresas = lv.listar_empresas(data_dir)
    if empresas:
        console.print("\n[bold]Empresas/proyectos existentes:[/bold]")
        for i, nombre in enumerate(empresas, 1):
            console.print(f"  [cyan]{i}[/cyan]) {nombre}")
        console.print("  [cyan]N[/cyan]) Nueva empresa/proyecto")
        eleccion = Prompt.ask("Elige", default="N")
        if eleccion.strip().upper() == "N" or not eleccion.isdigit() or not (1 <= int(eleccion) <= len(empresas)):
            empresa = Prompt.ask("Nombre de la empresa/proyecto").strip()
        else:
            empresa = empresas[int(eleccion) - 1]
    else:
        empresa = Prompt.ask("Nombre de la empresa/proyecto").strip()
    if not empresa:
        console.print("[red]Se necesita un nombre de empresa.[/red]")
        return None

    # 2. Levantamiento abierto o nuevo
    abiertos = [l for l in lv.listar_levantamientos(data_dir, empresa) if l.get("estado") == "abierto"]
    if abiertos:
        console.print("\n[bold]Levantamientos abiertos:[/bold]")
        for i, l in enumerate(abiertos, 1):
            sede = f" · {l.get('sede')}" if l.get('sede') else ""
            console.print(f"  [cyan]{i}[/cyan]) {l['levantamiento_id']} · creado {l['creado_en'][:10]}{sede} · {len(l.get('equipos', []))} equipo(s)")
        console.print("  [cyan]N[/cyan]) Nuevo levantamiento independiente")
        eleccion = Prompt.ask("Elige", default="N")
        if eleccion.strip().upper() == "N" or not eleccion.isdigit() or not (1 <= int(eleccion) <= len(abiertos)):
            sede = Prompt.ask("Sede o etiqueta (opcional)", default="")
            lev = lv.crear_levantamiento(empresa, sede=sede)
        else:
            lev = abiertos[int(eleccion) - 1]
    else:
        sede = Prompt.ask("Sede o etiqueta (opcional)", default="")
        lev = lv.crear_levantamiento(empresa, sede=sede)

    # 3. Colecta de este PC
    console.print("\n[yellow]Recolectando información de este computador (sin escanear la red)...[/yellow]")
    equipo = lv.recolectar_equipo()
    c = equipo["conexion"]
    console.print(f"  Equipo: [bold]{equipo['hostname']}[/bold] · {equipo['so']}")
    console.print(f"  Conexión: {c['tipo']} (verificada: {'sí' if c['tipo_verificado'] else 'no'}) · Wi-Fi: {c['wifi'].get('ssid', 'N/A')} · Gateway: {c.get('gateway') or 'no detectado'}")

    # 4. Deduplicación con confirmación del operador (nunca silenciosa)
    def confirmar(candidatos):
        console.print("\n[yellow]Este equipo podría ya estar en el levantamiento:[/yellow]")
        for i, cand in enumerate(candidatos, 1):
            e = cand["equipo"]
            console.print(f"  [cyan]{i}[/cyan]) {e.get('hostname')} ({e.get('equipo_id')}) · {', '.join(cand['motivos'])} · recolectado {e.get('recolectado_en', '?')[:16]}")
        console.print("  [cyan]N[/cyan]) Es un equipo distinto: registrar como nuevo")
        eleccion = Prompt.ask("¿Es alguno de estos?", default="N")
        if eleccion.strip().upper() == "N" or not eleccion.isdigit() or not (1 <= int(eleccion) <= len(candidatos)):
            return None
        return candidatos[int(eleccion) - 1]["equipo"]["equipo_id"]

    resultado = lv.merge_equipo(lev, equipo, confirmar)
    destino = lv.guardar_levantamiento(lev, data_dir)
    verbo = "actualizado en" if resultado == "actualizado" else "agregado a"
    console.print(f"\n[green]✓ Equipo {verbo} el levantamiento.[/green]")
    console.print(f"[bold white]📁 Guardado en:[/bold white] [underline cyan]{destino}[/underline cyan]")
    console.print(f"[dim]Equipos en el levantamiento: {len(lev['equipos'])}[/dim]")

    # 5. Cierre opcional
    if Confirm.ask("\n¿Finalizar el levantamiento? (puedes seguir agregando equipos después si no lo cierras)", default=False):
        lv.finalizar_levantamiento(lev)
        lv.guardar_levantamiento(lev, data_dir)
        console.print("[green]✓ Levantamiento finalizado.[/green] El informe consolidado de equipos es la siguiente etapa de desarrollo.")
    return destino


def main(argv=None):
    args = parse_args(argv)
    modo = args.modo or _elegir_modo()

    if modo == "levantamiento":
        return flujo_levantamiento(args.data_dir)

    console.print(Panel.fit(
        "[bold cyan]🌐 NetworkMapperTool v1.2.0[/bold cyan]\n"
        "[dim]Auditoría avanzada de redes multi-segmento, Nmap y Dashboard NOC[/dim]",
        border_style="cyan"
    ))

    start_time = time.time()

    with Progress(
        SpinnerColumn("dots", style="cyan"),
        TextColumn("[bold progress.description]{task.description}"),
        TimeElapsedColumn(),
        transient=False,
        console=console
    ) as progress:

        # Task 1: Hardware (progreso real: la tarea dura lo que tarda get_system_specs)
        task1 = progress.add_task("[yellow]Recopilando inventario de hardware local...", total=None)
        sys_specs = get_system_specs()
        progress.update(task1, completed=1, total=1, description="[green]✓ Inventario de hardware completado")

        # Task 2: Network Discovery & Nmap
        task2 = progress.add_task("[yellow]Escaneando redes, rutas y segmentos (Multi-segmento / Nmap)...", total=None)
        net_data = full_network_discovery(include_public_ip=args.wan)
        progress.update(task2, completed=1, total=1, description="[green]✓ Escaneo de red y segmentos finalizado")

        # Task 3: Classification & HTML Report
        task3 = progress.add_task("[yellow]Clasificando dispositivos y generando Dashboard NOC HTML...", total=None)
        enhanced_net = enhance_device_list(net_data, resolve=not args.no_dns, max_workers=max(1, args.threads // 2))
        output_path = os.path.abspath(args.output)
        elapsed = time.time() - start_time
        generate_html_report(sys_specs, enhanced_net, output_path=output_path, scan_duration=elapsed)
        progress.update(task3, completed=1, total=1, description="[green]✓ Dashboard NOC HTML generado con éxito")

    console.print(f"\n[bold green]✨ ¡Escaneo completado con éxito en {elapsed:.2f} segundos![/bold green]")
    console.print(f"[bold white]📁 Informe interactivo guardado en:[/bold white] [underline cyan]{output_path}[/underline cyan]\n")

    if not args.no_open:
        try:
            webbrowser.open(f"file:///{output_path}")
        except Exception:
            pass

    return output_path


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[red]Proceso cancelado por el usuario.[/red]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]Error crítico:[/bold red] {e}")
        sys.exit(1)
