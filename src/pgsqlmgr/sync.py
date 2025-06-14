"""Database synchronization operations for PostgreSQL Manager."""

import os
import subprocess
import tempfile
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.prompt import Confirm

from .config import HostConfig, LocalHost, SSHHost
from .db import PostgreSQLManager
from .ssh import SSHManager

console = Console()


class DatabaseSyncManager:
    """Manage database synchronization between hosts."""

    def __init__(self, source_config: HostConfig, destination_config: HostConfig):
        """Initialize sync manager with source and destination configurations."""
        self.source_config = source_config
        self.destination_config = destination_config
        self.temp_dir = None

        # Initialize managers
        self.source_pg_manager = PostgreSQLManager(source_config)
        self.dest_pg_manager = PostgreSQLManager(destination_config)

        # Initialize SSH managers if needed
        self.source_ssh = None
        self.dest_ssh = None

        if isinstance(source_config, SSHHost):
            self.source_ssh = SSHManager(source_config)
        if isinstance(destination_config, SSHHost):
            self.dest_ssh = SSHManager(destination_config)

    def sync_database(
        self,
        database_name: str,
        drop_existing: bool = False,
        data_only: bool = False,
        schema_only: bool = False,
        auto_install: bool = False
    ) -> tuple[bool, str]:
        """
        Sync a database from source to destination.

        Args:
            database_name: Name of database to sync
            drop_existing: Whether to drop existing database at destination
            data_only: Sync only data (no schema)
            schema_only: Sync only schema (no data)
            auto_install: Automatically install PostgreSQL if missing

        Returns:
            Tuple of (success, message)
        """
        try:
            console.print(f"[blue]🔄 Starting database sync: {database_name}[/blue]")
            console.print(f"[blue]   Source: {self._get_host_description(self.source_config)}[/blue]")
            console.print(f"[blue]   Destination: {self._get_host_description(self.destination_config)}[/blue]")

            # Pre-flight checks: Ensure PostgreSQL is available on both hosts
            console.print("[blue]🔍 Pre-flight checks...[/blue]")

            # Check source PostgreSQL
            source_available, source_msg = self._check_postgresql_availability(self.source_config, "source")
            if not source_available:
                return False, f"Source PostgreSQL check failed: {source_msg}"

            # Check destination PostgreSQL
            dest_available, dest_msg = self._check_postgresql_availability(self.destination_config, "destination", auto_install)
            if not dest_available:
                return False, f"Destination PostgreSQL check failed: {dest_msg}"

            # Create temporary directory for dump files
            self.temp_dir = tempfile.mkdtemp(prefix="pgsqlmgr_sync_")
            dump_file = Path(self.temp_dir) / f"{database_name}.sql"

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeElapsedColumn(),
                console=console
            ) as progress:

                # Step 1: Create dump from source
                task1 = progress.add_task("Creating database dump...", total=100)
                success, message = self._create_dump(database_name, dump_file, data_only, schema_only)
                if not success:
                    return False, f"Dump creation failed: {message}"
                progress.update(task1, completed=100)

                # Step 2: Transfer dump file if needed
                if isinstance(self.source_config, SSHHost) or isinstance(self.destination_config, SSHHost):
                    task2 = progress.add_task("Transferring dump file...", total=100)
                    success, message = self._transfer_dump_file(dump_file)
                    if not success:
                        return False, f"File transfer failed: {message}"
                    progress.update(task2, completed=100)

                # Step 3: Restore to destination
                task3 = progress.add_task("Restoring database...", total=100)
                success, message = self._restore_dump(database_name, dump_file, drop_existing)
                if not success:
                    return False, f"Restore failed: {message}"
                progress.update(task3, completed=100)

            # Cleanup
            self._cleanup()

            console.print(Panel(
                f"✅ Database '{database_name}' synced successfully!",
                title="Sync Complete",
                style="green"
            ))

            return True, f"Database '{database_name}' synced successfully"

        except Exception as e:
            self._cleanup()
            return False, f"Sync failed with error: {e}"

    def _get_host_description(self, config: HostConfig) -> str:
        """Get a human-readable description of a host."""
        if isinstance(config, LocalHost):
            return f"local ({config.host}:{config.port})"
        elif isinstance(config, SSHHost):
            return f"{config.ssh_config} ({config.host}:{config.port})"
        else:
            return "unknown host type"

    def _create_dump(
        self,
        database_name: str,
        dump_file: Path,
        data_only: bool = False,
        schema_only: bool = False
    ) -> tuple[bool, str]:
        """Create a database dump from the source."""
        if isinstance(self.source_config, LocalHost):
            return self._create_local_dump(database_name, dump_file, data_only, schema_only)
        elif isinstance(self.source_config, SSHHost):
            return self._create_ssh_dump(database_name, dump_file, data_only, schema_only)
        else:
            return False, "Unsupported source host type"

    def _create_local_dump(
        self,
        database_name: str,
        dump_file: Path,
        data_only: bool = False,
        schema_only: bool = False
    ) -> tuple[bool, str]:
        """Create a database dump from local PostgreSQL."""
        try:
            # Build pg_dump command
            cmd = [
                "pg_dump",
                "--verbose",
                "--clean",
                "--no-owner",
                "--no-privileges",
                "--host", self.source_config.host,
                "--port", str(self.source_config.port),
                "--username", self.source_config.superuser,
                "--file", str(dump_file),
                database_name
            ]

            # Add data/schema options
            if data_only:
                cmd.append("--data-only")
            elif schema_only:
                cmd.append("--schema-only")

            # Set environment variables for password
            env = os.environ.copy()
            if self.source_config.password:
                env["PGPASSWORD"] = self.source_config.password

            # Execute pg_dump
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                return True, f"Database dump created: {dump_file}"
            else:
                return False, f"pg_dump failed: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, "Database dump timed out"
        except FileNotFoundError:
            return False, "pg_dump command not found. Ensure PostgreSQL client tools are installed."
        except Exception as e:
            return False, f"Error creating dump: {e}"

    def _create_ssh_dump(
        self,
        database_name: str,
        dump_file: Path,
        data_only: bool = False,
        schema_only: bool = False
    ) -> tuple[bool, str]:
        """Create a database dump from SSH host."""
        console.print(f"[blue]🔗 Creating dump via SSH: {self.source_config.ssh_config}[/blue]")

        try:
            # Build remote pg_dump command
            remote_dump_file = f"/tmp/pgsqlmgr_{database_name}_{os.getpid()}.sql"

            cmd_parts = [
                "sudo", "-u", self.source_config.superuser, "pg_dump",
                "--verbose",
                "--clean",
                "--no-owner",
                "--no-privileges",
                "--file", remote_dump_file,
                database_name
            ]

            # Add data/schema options
            if data_only:
                cmd_parts.append("--data-only")
            elif schema_only:
                cmd_parts.append("--schema-only")

            # Build SSH command
            ssh_cmd = [
                "ssh",
                self.source_config.ssh_config,
                " ".join(cmd_parts)
            ]

            console.print(f"[blue]   Executing: {' '.join(ssh_cmd)}[/blue]")

            # Execute SSH pg_dump
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode != 0:
                return False, f"SSH pg_dump failed: {result.stderr}"

            # Download the dump file
            scp_cmd = [
                "scp",
                f"{self.source_config.ssh_config}:{remote_dump_file}",
                str(dump_file)
            ]

            console.print(f"[blue]   Downloading dump: {' '.join(scp_cmd)}[/blue]")

            scp_result = subprocess.run(
                scp_cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout for file transfer
            )

            if scp_result.returncode != 0:
                return False, f"SCP download failed: {scp_result.stderr}"

            # Clean up remote dump file
            cleanup_cmd = [
                "ssh",
                self.source_config.ssh_config,
                f"rm -f {remote_dump_file}"
            ]
            subprocess.run(cleanup_cmd, capture_output=True, timeout=30)

            return True, f"SSH database dump created and downloaded: {dump_file}"

        except subprocess.TimeoutExpired:
            return False, "SSH database dump timed out"
        except Exception as e:
            return False, f"Error creating SSH dump: {e}"

    def _transfer_dump_file(self, dump_file: Path) -> tuple[bool, str]:
        """Transfer dump file between hosts if needed."""
        # For local-to-local sync, no transfer needed
        if isinstance(self.source_config, LocalHost) and isinstance(self.destination_config, LocalHost):
            return True, "No file transfer needed for local-to-local sync"

        console.print("[blue]📁 Transferring dump file...[/blue]")

        # If source is SSH, file is already local (downloaded in _create_ssh_dump)
        # If destination is SSH, need to upload
        if isinstance(self.destination_config, SSHHost):
            try:
                remote_dump_file = f"/tmp/pgsqlmgr_restore_{os.getpid()}.sql"

                scp_cmd = [
                    "scp",
                    str(dump_file),
                    f"{self.destination_config.ssh_config}:{remote_dump_file}"
                ]

                console.print(f"[blue]   Uploading dump: {' '.join(scp_cmd)}[/blue]")

                result = subprocess.run(
                    scp_cmd,
                    capture_output=True,
                    text=True,
                    timeout=120  # 2 minute timeout
                )

                if result.returncode != 0:
                    return False, f"SCP upload failed: {result.stderr}"

                # Update dump_file path to remote path for restore
                self._remote_dump_file = remote_dump_file

                return True, f"Dump file uploaded to {self.destination_config.ssh_config}"

            except subprocess.TimeoutExpired:
                return False, "File upload timed out"
            except Exception as e:
                return False, f"Error uploading file: {e}"

        return True, "File transfer handled by source SSH download"

    def _restore_dump(
        self,
        database_name: str,
        dump_file: Path,
        drop_existing: bool = False
    ) -> tuple[bool, str]:
        """Restore database dump to destination."""
        if isinstance(self.destination_config, LocalHost):
            return self._restore_local_dump(database_name, dump_file, drop_existing)
        elif isinstance(self.destination_config, SSHHost):
            return self._restore_ssh_dump(database_name, dump_file, drop_existing)
        else:
            return False, "Unsupported destination host type"

    def _restore_local_dump(
        self,
        database_name: str,
        dump_file: Path,
        drop_existing: bool = False
    ) -> tuple[bool, str]:
        """Restore database dump to local PostgreSQL."""
        try:
            # Set environment variables for password
            env = os.environ.copy()
            if self.destination_config.password:
                env["PGPASSWORD"] = self.destination_config.password

            # Drop existing database if requested
            if drop_existing:
                drop_cmd = [
                    "dropdb",
                    "--host", self.destination_config.host,
                    "--port", str(self.destination_config.port),
                    "--username", self.destination_config.superuser,
                    "--if-exists",
                    database_name
                ]

                subprocess.run(drop_cmd, env=env, capture_output=True, timeout=30)

            # Create database
            createdb_cmd = [
                "createdb",
                "--host", self.destination_config.host,
                "--port", str(self.destination_config.port),
                "--username", self.destination_config.superuser,
                database_name
            ]

            result = subprocess.run(
                createdb_cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0 and "already exists" not in result.stderr:
                return False, f"Failed to create database: {result.stderr}"

            # Restore from dump
            psql_cmd = [
                "psql",
                "--host", self.destination_config.host,
                "--port", str(self.destination_config.port),
                "--username", self.destination_config.superuser,
                "--dbname", database_name,
                "--file", str(dump_file),
                "--quiet"
            ]

            result = subprocess.run(
                psql_cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                return True, f"Database '{database_name}' restored successfully"
            else:
                return False, f"psql restore failed: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, "Database restore timed out"
        except FileNotFoundError as e:
            return False, f"PostgreSQL command not found: {e}"
        except Exception as e:
            return False, f"Error restoring dump: {e}"

    def _restore_ssh_dump(
        self,
        database_name: str,
        dump_file: Path,
        drop_existing: bool = False
    ) -> tuple[bool, str]:
        """Restore database dump to SSH host."""
        console.print(f"[blue]🔗 Restoring via SSH: {self.destination_config.ssh_config}[/blue]")

        try:
            # Use the remote dump file path if available
            remote_dump_file = getattr(self, '_remote_dump_file', f"/tmp/pgsqlmgr_restore_{os.getpid()}.sql")

            # Use sudo -u {user} for SSH connections (simpler and more reliable)
            # Drop existing database if requested
            if drop_existing:
                drop_cmd = [
                    "ssh",
                    self.destination_config.ssh_config,
                    f"sudo -u {self.destination_config.superuser} dropdb --if-exists {database_name}"
                ]

                subprocess.run(drop_cmd, capture_output=True, timeout=30)

            # Create database
            createdb_cmd = [
                "ssh",
                self.destination_config.ssh_config,
                f"sudo -u {self.destination_config.superuser} createdb {database_name}"
            ]

            console.print(f"[blue]   Creating database: {' '.join(createdb_cmd)}[/blue]")

            result = subprocess.run(
                createdb_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0 and "already exists" not in result.stderr:
                # Check if it's just a "database already exists" error, which is okay
                if "already exists" not in result.stderr.lower():
                    return False, f"Failed to create database: {result.stderr}"

            # Restore from dump
            psql_cmd = [
                "ssh",
                self.destination_config.ssh_config,
                f"sudo -u {self.destination_config.superuser} psql --dbname {database_name} --file {remote_dump_file} --quiet"
            ]

            console.print(f"[blue]   Restoring database: {' '.join(psql_cmd)}[/blue]")

            result = subprocess.run(
                psql_cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            # Clean up remote dump file
            cleanup_cmd = [
                "ssh",
                self.destination_config.ssh_config,
                f"rm -f {remote_dump_file}"
            ]
            subprocess.run(cleanup_cmd, capture_output=True, timeout=30)

            if result.returncode == 0:
                return True, f"Database '{database_name}' restored successfully via SSH"
            else:
                return False, f"SSH psql restore failed: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, "SSH database restore timed out (this may indicate authentication or connection issues)"
        except Exception as e:
            return False, f"Error restoring SSH dump: {e}"

    def _cleanup(self):
        """Clean up temporary files."""
        if self.temp_dir and Path(self.temp_dir).exists():
            import shutil
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                console.print(f"[yellow]⚠️  Warning: Could not clean up temporary directory: {e}[/yellow]")

    def list_databases(self, host_config: HostConfig) -> tuple[bool, list[str], str]:
        """
        List databases on a host.

        Returns:
            Tuple of (success, database_list, error_message)
        """
        if isinstance(host_config, LocalHost):
            return self._list_local_databases(host_config)
        elif isinstance(host_config, SSHHost):
            return self._list_ssh_databases(host_config)
        else:
            return False, [], "Unsupported host type"

    def _list_local_databases(self, host_config: LocalHost) -> tuple[bool, list[str], str]:
        """List databases on local PostgreSQL."""
        try:
            cmd = [
                "psql",
                "--host", host_config.host,
                "--port", str(host_config.port),
                "--username", host_config.superuser,
                "--list",
                "--tuples-only",
                "--no-align",
                "--field-separator=|"
            ]

            env = os.environ.copy()
            if host_config.password:
                env["PGPASSWORD"] = host_config.password

            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                # Parse database list
                databases = []
                for line in result.stdout.strip().split('\n'):
                    if line and '|' in line:
                        db_name = line.split('|')[0].strip()
                        # Skip template and system databases
                        if db_name and not db_name.startswith('template') and db_name != 'postgres':
                            databases.append(db_name)

                return True, databases, ""
            else:
                return False, [], f"Failed to list databases: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, [], "Database list operation timed out"
        except Exception as e:
            return False, [], f"Error listing databases: {e}"

    def _list_ssh_databases(self, host_config: SSHHost) -> tuple[bool, list[str], str]:
        """List databases on SSH host."""
        console.print(f"[blue]🔗 Listing databases via SSH: {host_config.ssh_config}[/blue]")

        try:
            # Use sudo -u {user} for SSH connections (simpler and more reliable)
            ssh_cmd = [
                "ssh",
                host_config.ssh_config,
                f"sudo -u {host_config.superuser} psql --list --tuples-only --no-align --field-separator='|'"
            ]

            console.print(f"[blue]   Executing: {' '.join(ssh_cmd)}[/blue]")

            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                # Parse database list
                databases = []
                for line in result.stdout.strip().split('\n'):
                    if line and '|' in line:
                        db_name = line.split('|')[0].strip()
                        # Skip template and system databases
                        if db_name and not db_name.startswith('template') and db_name != 'postgres':
                            databases.append(db_name)

                return True, databases, ""
            else:
                return False, [], f"Failed to list databases via SSH: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, [], "SSH database list operation timed out"
        except Exception as e:
            return False, [], f"Error listing databases via SSH: {e}"

    def _check_postgresql_availability(
        self,
        host_config: HostConfig,
        host_type: str,
        auto_install: bool = False
    ) -> tuple[bool, str]:
        """
        Check if PostgreSQL is available on a host and offer installation if needed.

        Args:
            host_config: Host configuration
            host_type: "source" or "destination" for user messaging
            auto_install: Whether to automatically install if missing

        Returns:
            Tuple of (available, message)
        """
        pg_manager = PostgreSQLManager(host_config)

        # Check if PostgreSQL is installed
        is_installed, install_msg, version = pg_manager.check_postgresql_installation()

        if is_installed:
            # Check if service is running
            is_running, service_msg = pg_manager.check_service_status()

            if is_running:
                # For SSH hosts, also verify user authentication
                if isinstance(host_config, SSHHost):
                    auth_success, auth_msg = self._verify_postgresql_authentication(host_config)
                    if not auth_success:
                        console.print(f"[yellow]⚠️  PostgreSQL user authentication needed on {host_type} host[/yellow]")

                        # Offer to set up user
                        if auto_install or Confirm.ask(f"Set up PostgreSQL user authentication on {host_type} host?"):
                            setup_success, setup_msg = pg_manager._setup_postgresql_user()
                            if setup_success:
                                console.print(f"[green]✅ PostgreSQL user configured on {host_type} host[/green]")
                                return True, f"PostgreSQL ready with user authentication on {host_type}"
                            else:
                                return False, f"Failed to setup user authentication: {setup_msg}"
                        else:
                            return False, f"PostgreSQL user authentication not configured on {host_type} host"

                console.print(f"[green]✅ PostgreSQL is ready on {host_type} host[/green]")
                return True, f"PostgreSQL ready on {host_type}"
            else:
                console.print(f"[yellow]⚠️  PostgreSQL installed but not running on {host_type} host[/yellow]")

                # Try to start the service
                if auto_install or Confirm.ask(f"PostgreSQL is installed but not running on {host_type} host. Start the service?"):
                    console.print(f"[blue]🚀 Starting PostgreSQL service on {host_type} host...[/blue]")
                    start_success, start_msg = pg_manager.start_service()

                    if start_success:
                        console.print(f"[green]✅ PostgreSQL service started on {host_type} host[/green]")
                        return True, f"PostgreSQL service started on {host_type}"
                    else:
                        return False, f"Failed to start PostgreSQL service: {start_msg}"
                else:
                    return False, f"PostgreSQL service not running on {host_type} host"
        else:
            console.print(f"[red]❌ PostgreSQL not installed on {host_type} host[/red]")

            # Offer to install PostgreSQL
            if auto_install or Confirm.ask(f"PostgreSQL is not installed on {host_type} host. Install it now?"):
                console.print(f"[blue]📦 Installing PostgreSQL on {host_type} host...[/blue]")
                install_success, install_msg = pg_manager.install_postgresql()

                if install_success:
                    console.print(f"[green]✅ PostgreSQL installed successfully on {host_type} host[/green]")

                    # Start the service after installation
                    console.print(f"[blue]🚀 Starting PostgreSQL service on {host_type} host...[/blue]")
                    start_success, start_msg = pg_manager.start_service()

                    if start_success:
                        console.print(f"[green]✅ PostgreSQL service started on {host_type} host[/green]")
                        return True, f"PostgreSQL installed and started on {host_type}"
                    else:
                        return False, f"PostgreSQL installed but failed to start service: {start_msg}"
                else:
                    return False, f"Failed to install PostgreSQL: {install_msg}"
            else:
                return False, f"PostgreSQL not available on {host_type} host"

    def _verify_postgresql_authentication(self, host_config: SSHHost) -> tuple[bool, str]:
        """Verify PostgreSQL access via sudo on SSH host."""
        try:
            # Test sudo -u {user} access
            test_cmd = f"sudo -u {host_config.superuser} psql --list --quiet"

            result = subprocess.run(
                ["ssh", host_config.ssh_config, test_cmd],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return True, "PostgreSQL access via sudo successful"
            else:
                return False, f"PostgreSQL access failed: {result.stderr}"

        except Exception as e:
            return False, f"PostgreSQL access test failed: {e}"
