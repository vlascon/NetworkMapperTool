import os
import sys
import time
import webbrowser
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn

from src.hardware import get_system_specs
from src.network_discovery import full_network_discovery
from src.classifier import enhance_device_list
from src.reporter import generate_html_report

console = Console()

def main():
    console.print(Panel.fit(
        "[bold cyan]🌐 NetworkMapperTool v1.1.0[/bold cyan]\n"
        "[dim]Auditoría avanzada de redes multi-segmento, Nmap y Dashboard NOC[/dim]",
        border_style="cyan"
    ))

    start_time = time.time()

    with Progress(
        SpinnerColumn("dots", style="cyan"),
        TextColumn("[bold progress.description]{task.description}"),
        BarColumn(bar_width=30, complete_style="cyan", finished_style="green"),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        transient=False,
        console=console
    ) as progress:
        
        # Task 1: Hardware
        task1 = progress.add_task("[yellow]Recopilando inventario de hardware local...", total=100)
        for i in range(1, 4):
            time.sleep(0.15)
            progress.update(task1, advance=33)
        sys_specs = get_system_specs()
        progress.update(task1, completed=100, description="[green]✓ Inventario de hardware completado")

        # Task 2: Network Discovery & Nmap
        task2 = progress.add_task("[yellow]Escaneando redes, rutas y segmentos (Multi-segmento / Nmap)...", total=100)
        for i in range(1, 5):
            time.sleep(0.2)
            progress.update(task2, advance=20)
        net_data = full_network_discovery()
        progress.update(task2, completed=100, description="[green]✓ Escaneo de red y segmentos finalizado")

        # Task 3: Classification & HTML Report
        task3 = progress.add_task("[yellow]Clasificando dispositivos y generando Dashboard NOC HTML...", total=100)
        for i in range(1, 4):
            time.sleep(0.15)
            progress.update(task3, advance=33)
        enhanced_net = enhance_device_list(net_data)
        output_filename = "Mapa_Red_Inventario.html"
        output_path = os.path.abspath(output_filename)
        generate_html_report(sys_specs, enhanced_net, output_path=output_path)
        progress.update(task3, completed=100, description="[green]✓ Dashboard NOC HTML generado con éxito")

    elapsed = time.time() - start_time

    console.print(f"\n[bold green]✨ ¡Escaneo completado con éxito en {elapsed:.2f} segundos![/bold green]")
    console.print(f"[bold white]📁 Informe interactivo guardado en:[/bold white] [underline cyan]{output_path}[/underline cyan]\n")

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
