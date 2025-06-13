"""Main CLI entry point for PostgreSQL Manager."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typing import Optional
from pathlib import Path

from . import __version__
from .config import (
    load_config,
    create_sample_config,
    get_host_config,
    list_hosts as get_host_list,
    DEFAULT_CONFIG_FILE,
)

# Initialize console for rich output
console = Console()

# Create the main Typer app
app = typer.Typer(
    name="pgsqlmgr",
    help="PostgreSQL Manager - Manage PostgreSQL instances across local and remote environments",
    add_completion=False,
    rich_markup_mode="rich",
)


def version_callback(value: bool) -> None:
    """Show version information."""
    if value:
        console.print(
            Panel.fit(
                f"[bold blue]PostgreSQL Manager[/bold blue]\n"
                f"Version: [green]{__version__}[/green]\n"
                f"Author: Dominic Chang",
                title="Version Info",
                border_style="blue",
            )
        )
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version information and exit",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """
    PostgreSQL Manager - A CLI tool for managing PostgreSQL instances.
    
    Manage PostgreSQL instances across local and remote (SSH) environments
    with seamless database synchronization capabilities.
    """
    pass


@app.command()
def init_config(
    config_path: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to create configuration file"
    )
) -> None:
    """Initialize a sample configuration file."""
    try:
        path = Path(config_path) if config_path else DEFAULT_CONFIG_FILE
        create_sample_config(path)
        console.print(f"[green]✅ Configuration initialized at: {path}[/green]")
        console.print(f"[yellow]⚠️  Please edit {path} to match your setup[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Error creating configuration: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def list_hosts(
    config_path: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file"
    )
) -> None:
    """List all configured PostgreSQL hosts."""
    try:
        path = Path(config_path) if config_path else None
        hosts = get_host_list(path)
        
        if not hosts:
            console.print("[yellow]No hosts configured[/yellow]")
            console.print(f"Run [bold]pgsqlmgr init-config[/bold] to create a sample configuration")
            return
        
        table = Table(title="Configured Hosts")
        table.add_column("Host Name", style="cyan", no_wrap=True)
        table.add_column("Type", style="magenta")
        table.add_column("Connection", style="green")
        table.add_column("Description", style="white")
        
        config = load_config(path)
        for host_name in hosts:
            host_config = config.hosts[host_name]
            if host_config.type == "local":
                connection = f"{host_config.host}:{host_config.port}"
            elif host_config.type == "ssh":
                connection = f"ssh {host_config.ssh_config} → {host_config.host}:{host_config.port}"
            else:
                connection = host_config.provider if hasattr(host_config, 'provider') else "unknown"
            
            description = host_config.description or ""
            table.add_row(host_name, host_config.type, connection, description)
        
        console.print(table)
        
    except FileNotFoundError:
        console.print("[red]❌ Configuration file not found[/red]")
        console.print(f"Run [bold]pgsqlmgr init-config[/bold] to create a configuration file")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error loading configuration: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def show_config(
    host: str,
    config_path: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file"
    )
) -> None:
    """Show configuration for a specific host."""
    try:
        path = Path(config_path) if config_path else None
        host_config = get_host_config(host, path)
        
        # Create a panel with host configuration
        config_text = f"[bold]Host:[/bold] {host}\n"
        config_text += f"[bold]Type:[/bold] {host_config.type}\n"
        
        if host_config.type == "local":
            config_text += f"[bold]Host:[/bold] {host_config.host}\n"
            config_text += f"[bold]Port:[/bold] {host_config.port}\n"
            config_text += f"[bold]User:[/bold] {host_config.user}\n"
            config_text += f"[bold]Password:[/bold] {'***' if host_config.password else 'Not set'}\n"
            
        elif host_config.type == "ssh":
            config_text += f"[bold]SSH Config:[/bold] {host_config.ssh_config}\n"
            config_text += f"[bold]SSH Command:[/bold] ssh {host_config.ssh_config}\n"
            config_text += f"[bold]PG Host:[/bold] {host_config.host}\n"
            config_text += f"[bold]PG Port:[/bold] {host_config.port}\n"
            config_text += f"[bold]PG User:[/bold] {host_config.user}\n"
            config_text += f"[bold]PG Password:[/bold] {'***' if host_config.password else 'Not set'}\n"
            
        elif host_config.type == "cloud":
            config_text += f"[bold]Provider:[/bold] {host_config.provider}\n"
            config_text += f"[bold]Connection String:[/bold] {'***' if host_config.connection_string else 'Not set'}\n"
        
        if host_config.description:
            config_text += f"[bold]Description:[/bold] {host_config.description}\n"
        
        console.print(Panel(config_text, title=f"Configuration for '{host}'", border_style="blue"))
        
    except KeyError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)
    except FileNotFoundError:
        console.print("[red]❌ Configuration file not found[/red]")
        console.print(f"Run [bold]pgsqlmgr init-config[/bold] to create a configuration file")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error loading configuration: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def check_install(host: str) -> None:
    """Check PostgreSQL installation on a host."""
    console.print(f"[yellow]⚠️  Not implemented yet[/yellow]")
    console.print(f"This command will check PostgreSQL installation on: [blue]{host}[/blue]")


@app.command()
def install(host: str) -> None:
    """Install PostgreSQL on a host."""
    console.print(f"[yellow]⚠️  Not implemented yet[/yellow]")
    console.print(f"This command will install PostgreSQL on: [blue]{host}[/blue]")


@app.command()
def sync_db(
    source_host: str,
    database: str, 
    destination_host: str
) -> None:
    """Sync a database between two hosts."""
    console.print(f"[yellow]⚠️  Not implemented yet[/yellow]")
    console.print(
        f"This command will sync database [blue]{database}[/blue] "
        f"from [blue]{source_host}[/blue] to [blue]{destination_host}[/blue]"
    )


@app.command()
def delete_db(host: str, database: str) -> None:
    """Delete a database from a host."""
    console.print(f"[yellow]⚠️  Not implemented yet[/yellow]")
    console.print(f"This command will delete database [blue]{database}[/blue] from [blue]{host}[/blue]")


@app.command()
def generate_pgpass() -> None:
    """Generate .pgpass file from configuration."""
    console.print("[yellow]⚠️  Not implemented yet[/yellow]")
    console.print("This command will generate .pgpass entries from your configuration")


if __name__ == "__main__":
    app() 