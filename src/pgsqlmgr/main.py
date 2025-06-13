"""Main CLI entry point for PostgreSQL Manager."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from typing import Optional
from pathlib import Path

from . import __version__
from .config import (
    load_config,
    create_sample_config,
    get_host_config,
    list_hosts as get_host_list,
    DEFAULT_CONFIG_FILE,
    validate_config_file,
)
from .db import PostgreSQLManager

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
def check_install(
    host: str,
    config_path: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file"
    )
) -> None:
    """Check PostgreSQL installation on a host."""
    try:
        path = Path(config_path) if config_path else None
        host_config = get_host_config(host, path)
        
        console.print(f"[blue]🔍 Checking PostgreSQL installation on '{host}'...[/blue]")
        
        # Create PostgreSQL manager and check installation
        pg_manager = PostgreSQLManager(host_config)
        is_installed, status_msg, version_info = pg_manager.check_postgresql_installation()
        
        if is_installed:
            console.print(Panel(
                f"✅ {status_msg}\n[bold]Version:[/bold] {version_info}",
                title=f"Installation Status: {host}",
                title_align="left",
                style="green"
            ))
            
            # Also check service status
            console.print(f"[blue]🔍 Checking PostgreSQL service status...[/blue]")
            is_running, service_msg = pg_manager.check_service_status()
            
            if is_running:
                console.print(Panel(
                    f"✅ {service_msg}",
                    title="Service Status",
                    title_align="left",
                    style="green"
                ))
            else:
                console.print(Panel(
                    f"⚠️  {service_msg}",
                    title="Service Status",
                    title_align="left",
                    style="yellow"
                ))
                console.print(f"[yellow]💡 To start the service, run: [bold]pgsqlmgr start-service {host}[/bold][/yellow]")
        else:
            console.print(Panel(
                f"❌ {status_msg}",
                title=f"Installation Status: {host}",
                title_align="left",
                style="red"
            ))
            console.print(f"[yellow]💡 To install PostgreSQL, run: [bold]pgsqlmgr install {host}[/bold][/yellow]")
        
    except KeyError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)
    except FileNotFoundError:
        console.print("[red]❌ Configuration file not found[/red]")
        console.print(f"Run [bold]pgsqlmgr init-config[/bold] to create a configuration file")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error checking installation: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def install(
    host: str,
    config_path: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force installation even if PostgreSQL is already installed"
    )
) -> None:
    """Install PostgreSQL on a host."""
    try:
        path = Path(config_path) if config_path else None
        host_config = get_host_config(host, path)
        
        console.print(f"[blue]🔧 Installing PostgreSQL on '{host}'...[/blue]")
        
        # Create PostgreSQL manager
        pg_manager = PostgreSQLManager(host_config)
        
        # Check if already installed (unless force is used)
        if not force:
            is_installed, status_msg, version_info = pg_manager.check_postgresql_installation()
            if is_installed:
                console.print(Panel(
                    f"✅ PostgreSQL is already installed\n[bold]Version:[/bold] {version_info}",
                    title=f"Installation Status: {host}",
                    title_align="left",
                    style="green"
                ))
                console.print("[yellow]💡 Use --force to reinstall or run check-install to verify[/yellow]")
                return
        
        # Proceed with installation
        success, message = pg_manager.install_postgresql()
        
        if success:
            console.print(Panel(
                f"✅ {message}",
                title=f"Installation Complete: {host}",
                title_align="left",
                style="green"
            ))
            
            # Verify installation worked
            console.print(f"[blue]🔍 Verifying installation...[/blue]")
            is_installed, status_msg, version_info = pg_manager.check_postgresql_installation()
            
            if is_installed:
                console.print(f"[green]✅ Verification successful: {version_info}[/green]")
            else:
                console.print(f"[yellow]⚠️  Installation completed but verification failed: {status_msg}[/yellow]")
        else:
            console.print(Panel(
                f"❌ {message}",
                title=f"Installation Failed: {host}",
                title_align="left",
                style="red"
            ))
            raise typer.Exit(1)
        
    except KeyError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)
    except FileNotFoundError:
        console.print("[red]❌ Configuration file not found[/red]")
        console.print(f"Run [bold]pgsqlmgr init-config[/bold] to create a configuration file")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error during installation: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def start_service(
    host: str,
    config_path: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file"
    )
) -> None:
    """Start PostgreSQL service on a host."""
    try:
        path = Path(config_path) if config_path else None
        host_config = get_host_config(host, path)
        
        console.print(f"[blue]🚀 Starting PostgreSQL service on '{host}'...[/blue]")
        
        # Create PostgreSQL manager and start service
        pg_manager = PostgreSQLManager(host_config)
        success, message = pg_manager.start_service()
        
        if success:
            console.print(Panel(
                f"✅ {message}",
                title=f"Service Status: {host}",
                title_align="left",
                style="green"
            ))
        else:
            console.print(Panel(
                f"❌ {message}",
                title=f"Service Status: {host}",
                title_align="left",
                style="red"
            ))
            raise typer.Exit(1)
        
    except KeyError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)
    except FileNotFoundError:
        console.print("[red]❌ Configuration file not found[/red]")
        console.print(f"Run [bold]pgsqlmgr init-config[/bold] to create a configuration file")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error starting service: {e}[/red]")
        raise typer.Exit(1)


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


@app.command()
def validate_config(
    config_path: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file to validate"
    )
) -> None:
    """Validate configuration file without executing any operations."""
    try:
        path = Path(config_path) if config_path else None
        is_valid, errors = validate_config_file(path)
        
        config_file_path = path or DEFAULT_CONFIG_FILE
        
        if is_valid:
            console.print(Panel(
                Text("✅ Configuration is valid!", style="bold green"),
                title=f"Validation Result: {config_file_path}",
                title_align="left",
                style="green"
            ))
            
            # Show summary of valid configuration
            try:
                config = load_config(path)
                host_count = len(config.hosts)
                local_count = sum(1 for host in config.hosts.values() if host.type == "local")
                ssh_count = sum(1 for host in config.hosts.values() if host.type == "ssh")
                cloud_count = sum(1 for host in config.hosts.values() if host.type == "cloud")
                
                summary_text = f"Found {host_count} configured host(s):"
                if local_count > 0:
                    summary_text += f"\n  • {local_count} local host(s)"
                if ssh_count > 0:
                    summary_text += f"\n  • {ssh_count} SSH host(s)"
                if cloud_count > 0:
                    summary_text += f"\n  • {cloud_count} cloud host(s)"
                
                console.print(Panel(
                    summary_text,
                    title="Configuration Summary",
                    title_align="left",
                    style="blue"
                ))
                
            except Exception as e:
                console.print(f"[yellow]Note: Could not load config summary: {e}[/yellow]")
        else:
            console.print(Panel(
                Text("❌ Configuration validation failed!", style="bold red"),
                title=f"Validation Result: {config_file_path}",
                title_align="left",
                style="red"
            ))
            
            console.print("\n[bold red]Errors found:[/bold red]")
            for i, error in enumerate(errors, 1):
                console.print(f"  {i}. {error}")
            
            console.print(f"\n[yellow]Fix these errors and run [bold]pgsqlmgr validate-config[/bold] again[/yellow]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]❌ Error validating configuration: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app() 