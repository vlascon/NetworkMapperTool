import os
import sys
import time
import webbrowser
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.hardware import get_system_specs
from src.network_discovery import full_network_discovery
from src.classifier import enhance_device_list
from src.reporter import generate_html_report

console = Console()

def main():
    console.print(Panel.fit(
        "[bold cyan]Herramienta de Mapeo de Red e Inventario de Hardware[/bold cyan]\n"
        "[dim]Análisis avanzado de red, segmentos, marcas y especificaciones locales (Windows)[/dim]",
        border_style="cyan"
    ))

    start_time = time.time()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=False,
    ) as progress:
        
        task1 = progress.add_task("[yellow]Recopilando inventario de hardware local...", total=None)
        sys_specs = get_system_specs()
        progress.update(task1, completed=True)

        task2 = progress.add_task("[yellow]Ejecutando escaneo de red, rutas y segmentos...", total=None)
        net_data = full_network_discovery()
        progress.update(task2, completed=True)

        task3 = progress.add_task("[yellow]Clasificando dispositivos y generando informe HTML...", total=None)
        enhanced_net = enhance_device_list(net_data)
        output_filename = "Mapa_Red_Inventario.html"
        output_path = os.path.abspath(output_filename)
        generate_html_report(sys_specs, enhanced_net, output_path=output_path)
        progress.update(task3, completed=True)

    elapsed = time.time() - start_time

    console.print(f"\n[bold green]¡Escaneo completado con éxito en {elapsed:.2f} segundos![/bold green]")
    console.print(f"[bold white]Informe HTML generado en:[/bold white] [underline cyan]{output_path}[/underline cyan]\n")

    # Open report automatically
    try:
        webbrowser.open(f"file:///{output_path}")
    except Exception:
        pass

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[red]Proceso cancelado por el usuario.[/red]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]Error crítico:[/bold red] {e}")
        sys.exit(1)
