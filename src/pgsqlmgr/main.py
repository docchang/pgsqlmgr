"""Main CLI entry point for PostgreSQL Manager."""

from datetime import datetime
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from . import __version__
from .config import (
    DEFAULT_CONFIG_FILE,
    HostType,
    create_sample_config,
    get_host_config,
    load_config,
    validate_config_file,
)
from .config import list_hosts as get_host_list
from .db import DatabaseManager, PostgreSQLManager
from .listing import (
    PostgreSQLLister,
    display_databases,
    display_table_preview,
    display_tables,
    display_users,
)
from .sync import DatabaseSyncManager

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
    version: bool | None = typer.Option(
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
    config_path: str | None = typer.Option(
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
    config_path: str | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file"
    ),
    detailed: bool = typer.Option(
        False,
        "--detailed",
        "-d",
        help="Show detailed information including OS and PostgreSQL status"
    )
) -> None:
    """List all configured PostgreSQL hosts with optional detailed information."""
    try:
        path = Path(config_path) if config_path else None
        hosts = get_host_list(path)

        if not hosts:
            console.print("[yellow]No hosts configured[/yellow]")
            console.print("Run [bold]pgsqlmgr init-config[/bold] to create a sample configuration")
            return

        if detailed:
            table = Table(title="Configured Hosts (Detailed)")
            table.add_column("Host Name", style="cyan", no_wrap=True)
            table.add_column("Type", style="magenta")
            table.add_column("Connection", style="green")
            table.add_column("OS Info", style="blue")
            table.add_column("PostgreSQL", style="yellow", max_width=40)
            table.add_column("Description", style="white")
        else:
            table = Table(title="Configured Hosts")
            table.add_column("Host Name", style="cyan", no_wrap=True)
            table.add_column("Type", style="magenta")
            table.add_column("Connection", style="green")
            table.add_column("Description", style="white")

        config = load_config(path)
        for host_name in hosts:
            host_config = config.hosts[host_name]
            
            # Basic connection information
            if host_config.type == HostType.LOCAL:
                connection = f"{host_config.host}:{host_config.port}"
            elif host_config.type == HostType.SSH:
                connection = f"ssh {host_config.ssh_config} → {host_config.host}:{host_config.port}"
            else:
                connection = host_config.provider if hasattr(host_config, 'provider') else "unknown"

            description = host_config.description or ""
            
            if detailed:
                # Get OS information and PostgreSQL status
                console.print(f"[dim]Checking {host_name}...[/dim]", end="")
                
                os_info = "Unknown"
                pg_status = "Unknown"
                
                try:
                    pg_manager = PostgreSQLManager(host_config)
                    
                    # Get OS information for SSH hosts
                    if host_config.type == HostType.SSH:
                        try:
                            # Use subprocess timeout for cross-platform compatibility
                            os_result = pg_manager._detect_ssh_os()
                            if os_result:
                                os_type, os_version = os_result
                                os_info = f"{os_type.title()} {os_version}"
                            else:
                                os_info = "Detection failed"
                        except Exception:
                            os_info = "Unreachable"
                    elif host_config.type == HostType.LOCAL:
                        import platform
                        os_info = f"{platform.system()} {platform.release()}"
                    else:
                        os_info = "Cloud"
                    
                    # Check PostgreSQL installation
                    try:
                        is_installed, status_msg, version_info = pg_manager.check_postgresql_installation()
                        
                        if is_installed and version_info:
                            # Parse and format PostgreSQL version information
                            version_info = version_info.strip()
                            
                            # Extract just the version number
                            import re
                            
                            # Match different version formats and extract just the version number
                            # Examples: 
                            # "psql (PostgreSQL) 16.9 (Ubuntu 16.9-0ubuntu0.24.04.1)" -> "v16.9"
                            # "psql (PostgreSQL) 15.4" -> "v15.4" 
                            # "PostgreSQL 16.9" -> "v16.9"
                            patterns = [
                                r'psql \(PostgreSQL\) (\d+\.?\d*(?:\.\d+)?)',  # psql output format
                                r'PostgreSQL (\d+\.?\d*(?:\.\d+)?)',           # Direct PostgreSQL format
                                r'(\d+\.?\d*(?:\.\d+)?)',                      # Just version number
                            ]
                            
                            version_display = None
                            for pattern in patterns:
                                match = re.search(pattern, version_info, re.IGNORECASE)
                                if match:
                                    version_num = match.group(1)
                                    version_display = f"v{version_num}"
                                    break
                            
                            if not version_display:
                                # Fallback: show "Installed" if we can't parse version
                                version_display = "Installed"
                            
                            pg_status = f"✅ {version_display}"
                        elif is_installed:
                            pg_status = "✅ Installed"
                        else:
                            pg_status = "❌ Not installed"
                    except Exception:
                        if os_info == "Unreachable":
                            pg_status = "Unreachable"
                        else:
                            pg_status = "Check failed"
                        
                except Exception as e:
                    if host_config.type == HostType.LOCAL:
                        import platform
                        os_info = f"{platform.system()} {platform.release()}"
                    else:
                        os_info = "Check failed"
                    pg_status = "Check failed"
                
                console.print("\r" + " " * 50 + "\r", end="")  # Clear the checking message
                
                table.add_row(host_name, host_config.type.value, connection, os_info, pg_status, description)
            else:
                table.add_row(host_name, host_config.type.value, connection, description)

        console.print(table)
        
        if not detailed:
            console.print()
            console.print("[dim]💡 Use --detailed or -d to see OS and PostgreSQL installation status[/dim]")

    except FileNotFoundError:
        console.print("[red]❌ Configuration file not found[/red]")
        console.print("Run [bold]pgsqlmgr init-config[/bold] to create a configuration file")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error loading configuration: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def show_config(
    host: str,
    config_path: str | None = typer.Option(
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
        config_text += f"[bold]Type:[/bold] {host_config.type.value}\n"

        if host_config.type == HostType.LOCAL:
            config_text += f"[bold]Host:[/bold] {host_config.host}\n"
            config_text += f"[bold]Port:[/bold] {host_config.port}\n"
            config_text += f"[bold]Superuser:[/bold] {host_config.superuser}\n"
            config_text += f"[bold]Password:[/bold] {'***' if host_config.password else 'Not set'}\n"

        elif host_config.type == HostType.SSH:
            config_text += f"[bold]SSH Config:[/bold] {host_config.ssh_config}\n"
            config_text += f"[bold]SSH Command:[/bold] ssh {host_config.ssh_config}\n"
            config_text += f"[bold]PG Host:[/bold] {host_config.host}\n"
            config_text += f"[bold]PG Port:[/bold] {host_config.port}\n"
            config_text += f"[bold]PG Superuser:[/bold] {host_config.superuser}\n"
            config_text += f"[bold]PG Password:[/bold] {'***' if host_config.password else 'Not set'}\n"

        elif host_config.type == HostType.CLOUD:
            config_text += f"[bold]Provider:[/bold] {host_config.provider}\n"
            if host_config.connection_string:
                config_text += "[bold]Connection String:[/bold] ***\n"
            else:
                config_text += f"[bold]Host:[/bold] {host_config.host}\n"
                config_text += f"[bold]Port:[/bold] {host_config.port}\n"
                config_text += f"[bold]Superuser:[/bold] {host_config.superuser}\n"
                config_text += f"[bold]Password:[/bold] {'***' if host_config.password else 'Not set'}\n"

        if host_config.description:
            config_text += f"[bold]Description:[/bold] {host_config.description}\n"

        console.print(Panel(config_text, title=f"Configuration for '{host}'", border_style="blue"))

    except KeyError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)
    except FileNotFoundError:
        console.print("[red]❌ Configuration file not found[/red]")
        console.print("Run [bold]pgsqlmgr init-config[/bold] to create a configuration file")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error loading configuration: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def check_install(
    host: str,
    config_path: str | None = typer.Option(
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
            console.print("[blue]🔍 Checking PostgreSQL service status...[/blue]")
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
        console.print("Run [bold]pgsqlmgr init-config[/bold] to create a configuration file")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error checking installation: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def install(
    host: str,
    config_path: str | None = typer.Option(
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
            console.print("[blue]🔍 Verifying installation...[/blue]")
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
        console.print("Run [bold]pgsqlmgr init-config[/bold] to create a configuration file")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error during installation: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def uninstall(
    host: str,
    config_path: str | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force uninstallation without confirmation prompt"
    ),
    backup_data: bool = typer.Option(
        False,
        "--backup-data",
        "-b",
        help="Create backup of all databases before uninstalling"
    ),
    backup_path: str | None = typer.Option(
        None,
        "--backup-path",
        help="Path to save database backups (default: current directory)"
    )
) -> None:
    """Uninstall PostgreSQL from a host.
    
    This will completely remove PostgreSQL and all its data.
    Use --backup-data to save all databases before uninstalling.
    """
    try:
        path = Path(config_path) if config_path else None
        host_config = get_host_config(host, path)

        console.print(f"[red]🗑️  PostgreSQL Uninstallation Request[/red]")
        console.print(f"[blue]   Host: {host}[/blue]")

        # Create PostgreSQL manager
        pg_manager = PostgreSQLManager(host_config)

        # Check if PostgreSQL is installed
        is_installed, status_msg, version_info = pg_manager.check_postgresql_installation()
        
        if not is_installed:
            console.print(Panel(
                f"ℹ️  PostgreSQL is not installed on '{host}'\n{status_msg}",
                title="Nothing to Uninstall",
                title_align="left",
                style="blue"
            ))
            return

        console.print(f"[blue]   Version: {version_info}[/blue]")

        # Backup databases if requested
        if backup_data:
            console.print("[blue]💾 Creating backup of all databases...[/blue]")
            backup_success = pg_manager.backup_all_databases(backup_path)
            
            if not backup_success and not force:
                console.print("[red]❌ Backup failed. Use --force to continue without backup[/red]")
                raise typer.Exit(1)

        # Confirmation prompt (unless --force is used)
        if not force:
            console.print(f"\n[bold red]⚠️  WARNING: This will completely remove PostgreSQL from '{host}'![/bold red]")
            console.print("[red]• All PostgreSQL services will be stopped[/red]")
            console.print("[red]• All PostgreSQL software will be uninstalled[/red]")
            console.print("[red]• All databases and data will be permanently deleted[/red]")
            console.print("[red]• This action cannot be undone![/red]")
            
            if backup_data:
                console.print("[green]💾 Database backups will be preserved[/green]")

            confirm = typer.confirm(
                f"\nAre you sure you want to completely uninstall PostgreSQL from '{host}'?",
                default=False
            )

            if not confirm:
                console.print("[yellow]❌ PostgreSQL uninstallation cancelled[/yellow]")
                return

        # Perform the uninstallation
        console.print(f"\n[red]🗑️  Uninstalling PostgreSQL from '{host}'...[/red]")

        success, message = pg_manager.uninstall_postgresql()

        if success:
            console.print(Panel(
                f"✅ {message}",
                title=f"Uninstallation Complete: {host}",
                title_align="left",
                style="green"
            ))

            # Verify uninstallation
            console.print("[blue]🔍 Verifying uninstallation...[/blue]")
            is_still_installed, verify_msg, _ = pg_manager.check_postgresql_installation()

            if not is_still_installed:
                console.print("[green]✅ Verification successful: PostgreSQL completely removed[/green]")
            else:
                console.print(f"[yellow]⚠️  Uninstallation completed but some components may remain: {verify_msg}[/yellow]")
        else:
            console.print(Panel(
                f"❌ {message}",
                title=f"Uninstallation Failed: {host}",
                title_align="left",
                style="red"
            ))
            raise typer.Exit(1)

    except KeyError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)
    except FileNotFoundError:
        console.print("[red]❌ Configuration file not found[/red]")
        console.print("Run [bold]pgsqlmgr init-config[/bold] to create a configuration file")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error during uninstallation: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def update(
    host: str,
    config_path: str | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force update without confirmation prompt"
    ),
    backup_data: bool = typer.Option(
        False,
        "--backup-data",
        "-b",
        help="Create backup of all databases before updating"
    ),
    backup_path: str | None = typer.Option(
        None,
        "--backup-path",
        help="Path to save database backups (default: current directory)"
    )
) -> None:
    """Update PostgreSQL to the latest version on a host.
    
    This will upgrade PostgreSQL while preserving data.
    Use --backup-data to save all databases before updating.
    """
    try:
        path = Path(config_path) if config_path else None
        host_config = get_host_config(host, path)

        console.print(f"[blue]🔄 PostgreSQL Update Request[/blue]")
        console.print(f"[blue]   Host: {host}[/blue]")

        # Create PostgreSQL manager
        pg_manager = PostgreSQLManager(host_config)

        # Check if PostgreSQL is installed
        is_installed, status_msg, version_info = pg_manager.check_postgresql_installation()
        
        if not is_installed:
            console.print(Panel(
                f"ℹ️  PostgreSQL is not installed on '{host}'\n{status_msg}",
                title="Nothing to Update",
                title_align="left",
                style="blue"
            ))
            console.print(f"[yellow]💡 To install PostgreSQL, run: [bold]pgsqlmgr install {host}[/bold][/yellow]")
            return

        console.print(f"[blue]   Current Version: {version_info}[/blue]")

        # Check if update is available
        update_available, update_info = pg_manager.check_update_available()
        
        if not update_available:
            console.print(Panel(
                f"✅ PostgreSQL is already up to date\n{update_info}",
                title="No Update Available",
                title_align="left",
                style="green"
            ))
            return

        console.print(f"[green]📦 Update Available: {update_info}[/green]")

        # Backup databases if requested
        if backup_data:
            console.print("[blue]💾 Creating backup of all databases...[/blue]")
            backup_success = pg_manager.backup_all_databases(backup_path)
            
            if not backup_success and not force:
                console.print("[red]❌ Backup failed. Use --force to continue without backup[/red]")
                raise typer.Exit(1)

        # Confirmation prompt (unless --force is used)
        if not force:
            console.print(f"\n[bold blue]🔄 Ready to update PostgreSQL on '{host}'[/bold blue]")
            console.print("[blue]• PostgreSQL will be updated to the latest version[/blue]")
            console.print("[blue]• Service will be restarted[/blue]")
            console.print("[blue]• All data will be preserved[/blue]")
            
            if backup_data:
                console.print("[green]💾 Database backups will be created[/green]")

            confirm = typer.confirm(
                f"\nProceed with PostgreSQL update on '{host}'?",
                default=True
            )

            if not confirm:
                console.print("[yellow]❌ PostgreSQL update cancelled[/yellow]")
                return

        # Perform the update
        console.print(f"\n[blue]🔄 Updating PostgreSQL on '{host}'...[/blue]")

        success, message = pg_manager.update_postgresql()

        if success:
            console.print(Panel(
                f"✅ {message}",
                title=f"Update Complete: {host}",
                title_align="left",
                style="green"
            ))

            # Verify update
            console.print("[blue]🔍 Verifying update...[/blue]")
            is_installed, verify_msg, new_version = pg_manager.check_postgresql_installation()

            if is_installed and new_version:
                console.print(f"[green]✅ Update successful: {new_version}[/green]")
            else:
                console.print(f"[yellow]⚠️  Update completed but verification failed: {verify_msg}[/yellow]")
        else:
            console.print(Panel(
                f"❌ {message}",
                title=f"Update Failed: {host}",
                title_align="left",
                style="red"
            ))
            raise typer.Exit(1)

    except KeyError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)
    except FileNotFoundError:
        console.print("[red]❌ Configuration file not found[/red]")
        console.print("Run [bold]pgsqlmgr init-config[/bold] to create a configuration file")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error during update: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def start_service(
    host: str,
    config_path: str | None = typer.Option(
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
        console.print("Run [bold]pgsqlmgr init-config[/bold] to create a configuration file")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error starting service: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def sync_db(
    source_host: str,
    database_name: str,
    destination_host: str,
    config_path: str | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file"
    ),
    drop_existing: bool = typer.Option(
        False,
        "--drop-existing",
        help="Drop existing database at destination before sync"
    ),
    data_only: bool = typer.Option(
        False,
        "--data-only",
        help="Sync only data (no schema)"
    ),
    schema_only: bool = typer.Option(
        False,
        "--schema-only",
        help="Sync only schema (no data)"
    ),
    auto_install: bool = typer.Option(
        False,
        "--auto-install",
        help="Automatically install PostgreSQL if missing on destination"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be done without executing"
    )
) -> None:
    """Sync a database between two hosts."""
    try:
        # Validate mutually exclusive options
        if data_only and schema_only:
            console.print("[red]❌ --data-only and --schema-only are mutually exclusive[/red]")
            raise typer.Exit(1)

        path = Path(config_path) if config_path else None

        # Get source and destination configurations
        source_config = get_host_config(source_host, path)
        dest_config = get_host_config(destination_host, path)

        if dry_run:
            console.print("[blue]🔍 Dry run: Database sync simulation[/blue]")
            console.print(f"[blue]   Source: {source_host} → Database: {database_name}[/blue]")
            console.print(f"[blue]   Destination: {destination_host}[/blue]")

            options = []
            if drop_existing:
                options.append("Drop existing database")
            if data_only:
                options.append("Data only")
            elif schema_only:
                options.append("Schema only")
            else:
                options.append("Full sync (schema + data)")

            if auto_install:
                options.append("Auto-install PostgreSQL if missing")

            console.print(f"[blue]   Options: {', '.join(options)}[/blue]")
            console.print("[yellow]💡 Remove --dry-run to execute the sync[/yellow]")
            return

        # Create sync manager
        sync_manager = DatabaseSyncManager(source_config, dest_config)

        # Check if source and destination are the same
        if source_host == destination_host:
            console.print("[red]❌ Source and destination hosts cannot be the same[/red]")
            raise typer.Exit(1)

        # Perform the sync
        console.print("[blue]🚀 Starting database synchronization...[/blue]")

        success, message = sync_manager.sync_database(
            database_name=database_name,
            drop_existing=drop_existing,
            data_only=data_only,
            schema_only=schema_only,
            auto_install=auto_install
        )

        if success:
            console.print(f"[green]✅ {message}[/green]")
        else:
            console.print(Panel(
                f"❌ {message}",
                title="Sync Failed",
                style="red"
            ))
            raise typer.Exit(1)

    except KeyError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)
    except FileNotFoundError:
        console.print("[red]❌ Configuration file not found[/red]")
        console.print("Run [bold]pgsqlmgr init-config[/bold] to create a configuration file")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error during sync: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def delete_db(
    host: str = typer.Argument(..., help="Host name from configuration"),
    database: str = typer.Argument(..., help="Database name to delete"),
    config_path: str | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force deletion without confirmation prompt"
    ),
    backup: bool = typer.Option(
        False,
        "--backup",
        "-b",
        help="Create backup before deletion"
    ),
    backup_path: str | None = typer.Option(
        None,
        "--backup-path",
        help="Path to save backup file (default: current directory)"
    )
) -> None:
    """Delete a database from a host.

    This command will permanently delete the specified database.
    Use --backup to create a backup before deletion.
    Use --force to skip confirmation prompts.
    """
    try:
        path = Path(config_path) if config_path else None
        host_config = get_host_config(host, path)

        # Create database manager
        db_manager = DatabaseManager(host_config)

        console.print("[red]🗑️  Database Deletion Request[/red]")
        console.print(f"[blue]   Host: {host}[/blue]")
        console.print(f"[blue]   Database: {database}[/blue]")

        # Get database information for confirmation
        console.print("[blue]🔍 Gathering database information...[/blue]")
        db_info = db_manager.get_database_info(database)

        if not db_info.get("exists", False):
            if "error" in db_info:
                console.print(f"[yellow]⚠️  Warning: Could not verify database existence: {db_info['error']}[/yellow]")
            else:
                console.print(f"[yellow]⚠️  Database '{database}' does not exist on host '{host}'[/yellow]")
                console.print("[green]✅ Nothing to delete[/green]")
                return

        # Display database information
        if db_info.get("exists"):
            console.print("\n[bold cyan]📊 Database Information:[/bold cyan]")

            info_table = Table(show_header=False, box=None, padding=(0, 2))
            info_table.add_column("Property", style="cyan")
            info_table.add_column("Value", style="white")

            info_table.add_row("Name", db_info.get("name", "Unknown"))
            info_table.add_row("Owner", db_info.get("owner", "Unknown"))
            info_table.add_row("Size", db_info.get("size", "Unknown"))
            info_table.add_row("Encoding", db_info.get("encoding", "Unknown"))
            info_table.add_row("Active Connections", db_info.get("active_connections", "Unknown"))

            console.print(info_table)

        # Create backup if requested
        backup_file = None
        if backup:
            console.print("\n[blue]💾 Creating backup before deletion...[/blue]")

            # Determine backup file path
            if backup_path:
                backup_dir = Path(backup_path)
                if backup_dir.is_dir():
                    backup_file = backup_dir / f"{database}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
                else:
                    backup_file = Path(backup_path)
            else:
                backup_file = Path(f"{database}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql")

            # Create backup using sync functionality (reuse existing dump logic)
            from .sync import DatabaseSyncManager
            sync_manager = DatabaseSyncManager(host_config, host_config)  # Same source and dest for backup

            try:
                success, message = sync_manager._create_dump(database, backup_file)
                if success:
                    console.print(f"[green]✅ Backup created: {backup_file}[/green]")
                else:
                    console.print(f"[red]❌ Backup failed: {message}[/red]")
                    if not force:
                        console.print("[red]Aborting deletion due to backup failure[/red]")
                        raise typer.Exit(1)
                    else:
                        console.print("[yellow]⚠️  Continuing with deletion despite backup failure (--force used)[/yellow]")
            except Exception as e:
                console.print(f"[red]❌ Backup error: {e}[/red]")
                if not force:
                    console.print("[red]Aborting deletion due to backup error[/red]")
                    raise typer.Exit(1)
                else:
                    console.print("[yellow]⚠️  Continuing with deletion despite backup error (--force used)[/yellow]")

        # Confirmation prompt (unless --force is used)
        if not force:
            console.print(f"\n[bold red]⚠️  WARNING: This will permanently delete database '{database}' from host '{host}'![/bold red]")
            if backup_file:
                console.print(f"[green]💾 Backup saved to: {backup_file}[/green]")
            console.print("[red]This action cannot be undone![/red]")

            confirm = typer.confirm(
                f"\nAre you sure you want to delete database '{database}'?",
                default=False
            )

            if not confirm:
                console.print("[yellow]❌ Database deletion cancelled[/yellow]")
                return

        # Perform the deletion
        console.print(f"\n[red]🗑️  Deleting database '{database}'...[/red]")

        success, message = db_manager.drop_database(database, force=True)

        if success:
            console.print(Panel(
                f"✅ Database '{database}' deleted successfully!",
                title="Deletion Complete",
                style="green"
            ))

            if backup_file and backup_file.exists():
                console.print(f"[blue]💾 Backup available at: {backup_file}[/blue]")
        else:
            console.print(Panel(
                f"❌ Failed to delete database: {message}",
                title="Deletion Failed",
                style="red"
            ))
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def generate_pgpass() -> None:
    """Generate .pgpass file from configuration."""
    console.print("[yellow]⚠️  Not implemented yet[/yellow]")
    console.print("This command will generate .pgpass entries from your configuration")


@app.command()
def validate_config(
    config_path: str | None = typer.Option(
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
                local_count = sum(1 for host in config.hosts.values() if host.type == HostType.LOCAL)
                ssh_count = sum(1 for host in config.hosts.values() if host.type == HostType.SSH)
                cloud_count = sum(1 for host in config.hosts.values() if host.type == HostType.CLOUD)

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

            console.print("\n[yellow]Fix these errors and run [bold]pgsqlmgr validate-config[/bold] again[/yellow]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]❌ Error validating configuration: {e}[/red]")
        raise typer.Exit(1)


@app.command("list-databases")
def list_databases(
    host: str = typer.Argument(..., help="Host name from configuration"),
    include_system: bool = typer.Option(False, "--include-system", "-s", help="Include system databases"),
    config_file: Path | None = typer.Option(None, "--config", "-c", help="Path to configuration file")
):
    """List databases on a PostgreSQL host."""
    try:
        host_config = get_host_config(host, config_file)
        lister = PostgreSQLLister(host_config)

        console.print(f"[blue]📊 Listing databases on {host}...[/blue]")

        success, databases, error = lister.list_databases(include_system)

        if success:
            display_databases(databases, host, include_system)
        else:
            console.print(f"[red]❌ Failed to list databases: {error}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@app.command("list-tables")
def list_tables(
    host: str = typer.Argument(..., help="Host name from configuration"),
    database: str | None = typer.Option(None, "--database", "-d", help="Specific database to list tables for"),
    include_system: bool = typer.Option(False, "--include-system", "-s", help="Include system tables"),
    preview: bool = typer.Option(False, "--preview", "-p", help="Show table content preview (10 records per table)"),
    config_file: Path | None = typer.Option(None, "--config", "-c", help="Path to configuration file")
):
    """List tables on a PostgreSQL host.

    Use --preview to show table content preview (10 records per table).
    """
    try:
        host_config = get_host_config(host, config_file)
        lister = PostgreSQLLister(host_config)

        if database:
            console.print(f"[blue]📋 Listing tables in database '{database}' on {host}...[/blue]")
            context = f"in database '{database}' on {host}"
        else:
            console.print(f"[blue]📋 Listing tables in all user databases on {host}...[/blue]")
            context = f"in all user databases on {host}"

        success, tables, error = lister.list_tables(database, include_system)

        if success:
            display_tables(tables, context)

            # Add table content previews if requested
            if preview:
                preview_limit = 10  # Fixed at 10 records
                console.print(f"\n[bold cyan]🔍 Table Content Previews (showing up to {preview_limit} records per table):[/bold cyan]")

                # Group tables by database if we're listing across multiple databases
                if database:
                    # Single database - preview all tables
                    _preview_tables_for_database(lister, tables, database, preview_limit)
                else:
                    # Multiple databases - group by database
                    tables_by_db = {}
                    for table in tables:
                        db_name = table.get('database', 'unknown')
                        if db_name not in tables_by_db:
                            tables_by_db[db_name] = []
                        tables_by_db[db_name].append(table)

                    for db_name, db_tables in tables_by_db.items():
                        console.print(f"\n[bold yellow]Database: {db_name}[/bold yellow]")
                        _preview_tables_for_database(lister, db_tables, db_name, preview_limit)
        else:
            console.print(f"[red]❌ Failed to list tables: {error}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


def _preview_tables_for_database(lister: PostgreSQLLister, tables: list[dict[str, Any]], database_name: str, limit: int):
    """Helper function to preview tables for a specific database."""
    for table in tables:
        table_name = table.get('table', 'unknown')
        schema_name = table.get('schema', 'public')

        console.print(f"\n[dim]Previewing {schema_name}.{table_name}...[/dim]")

        success, data_rows, columns, error = lister.preview_table_content(
            database_name, table_name, schema_name, limit
        )

        if success:
            if data_rows:
                display_table_preview(data_rows, columns, table_name, database_name, schema_name, limit)
            else:
                console.print(f"[yellow]  📭 Table {schema_name}.{table_name} is empty[/yellow]")
        else:
            console.print(f"[red]  ❌ Could not preview {schema_name}.{table_name}: {error}[/red]")


@app.command("list-users")
def list_users(
    host: str = typer.Argument(..., help="Host name from configuration"),
    config_file: Path | None = typer.Option(None, "--config", "-c", help="Path to configuration file")
):
    """List PostgreSQL users/roles on a host."""
    try:
        host_config = get_host_config(host, config_file)
        lister = PostgreSQLLister(host_config)

        console.print(f"[blue]👥 Listing users on {host}...[/blue]")

        success, users, error = lister.list_users()

        if success:
            display_users(users, host)
        else:
            console.print(f"[red]❌ Failed to list users: {error}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@app.command("preview-table")
def preview_table(
    host: str = typer.Argument(..., help="Host name from configuration"),
    database: str = typer.Argument(..., help="Database name"),
    table: str = typer.Argument(..., help="Table name to preview"),
    schema: str = typer.Option("public", "--schema", "-s", help="Schema name (default: public)"),
    config_file: Path | None = typer.Option(None, "--config", "-c", help="Path to configuration file")
):
    """Preview table content with sample data (10 records)."""
    try:
        host_config = get_host_config(host, config_file)
        lister = PostgreSQLLister(host_config)

        console.print(f"[blue]🔍 Previewing table '{schema}.{table}' in database '{database}' on {host}...[/blue]")

        limit = 10  # Fixed at 10 records
        success, data_rows, columns, error = lister.preview_table_content(database, table, schema, limit)

        if success:
            display_table_preview(data_rows, columns, table, database, schema, limit)
        else:
            console.print(f"[red]❌ Failed to preview table: {error}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
