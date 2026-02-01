import typer
import os
import json
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from sisrua_sdk.client import SisRuaClient

app = typer.Typer(help="sisRUA Internal CLI Tool")
console = Console()

def get_client() -> SisRuaClient:
    url = os.environ.get("SISRUA_URL", "http://localhost:8000/api/v1")
    token = os.environ.get("SISRUA_TOKEN", "dev-token-123")
    return SisRuaClient(base_url=url, token=token)

# --- JOB COMMANDS ---
job_app = typer.Typer(help="Manage processing jobs.")
app.add_typer(job_app, name="job")

@job_app.command("create")
def create_job(
    kind: str = typer.Option(..., help="Job kind: 'osm' or 'geojson'"),
    lat: float = typer.Option(None, help="Latitude (for OSM)"),
    lon: float = typer.Option(None, help="Longitude (for OSM)"),
    radius: float = typer.Option(None, help="Radius in meters (for OSM)"),
    wait: bool = typer.Option(False, help="Wait for completion")
):
    """Create a new processing job."""
    client = get_client()
    try:
        console.print(f"[bold blue]Creating job...[/bold blue] ({kind})")
        job = client.create_job(kind=kind, latitude=lat, longitude=lon, radius=radius)
        
        console.print(f"[green]Job initiated:[/green] {job.job_id}")
        
        if wait:
            console.print("[yellow]Waiting for job completion...[/yellow]")
            job = client.wait_for_job(job.job_id)
            if job.status == "completed":
                console.print(Panel(json.dumps(job.result, indent=2), title=f"Job Result ({job.status})", border_style="green"))
            else:
                console.print(Panel(str(job.error), title=f"Job Failed ({job.status})", border_style="red"))
        else:
            table = Table("ID", "Status", "Progress")
            table.add_row(job.job_id, job.status, str(job.progress))
            console.print(table)
            
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")

@job_app.command("status")
def get_status(job_id: str):
    """Get the status of an existing job."""
    client = get_client()
    try:
        job = client.get_job_status(job_id)
        table = Table("Field", "Value")
        table.add_row("ID", job.job_id)
        table.add_row("Status", f"[bold]{job.status}[/bold]")
        table.add_row("Progress", f"{job.progress*100:.1f}%")
        table.add_row("Message", job.message or "")
        console.print(Panel(table, title="Job Status"))
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")

# --- ELEVATION COMMANDS ---
elev_app = typer.Typer(help="Query elevation data.")
app.add_typer(elev_app, name="elevation")

@elev_app.command("get")
def get_elevation(
    lat: float = typer.Option(..., help="Latitude"),
    lon: float = typer.Option(..., help="Longitude")
):
    """Query SRTM elevation for a single point."""
    client = get_client()
    try:
        z = client.get_elevation(lat, lon)
        if z is not None:
            console.print(f"[bold green]Elevation:[/bold green] {z:.2f} meters")
        else:
            console.print("[yellow]No data found.[/yellow]")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")

if __name__ == "__main__":
    app()
