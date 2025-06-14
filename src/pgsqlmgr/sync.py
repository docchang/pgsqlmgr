"""Database synchronization operations for PostgreSQL Manager."""

import os
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.text import Text

from .config import HostConfig, LocalHost, SSHHost
from .ssh import SSHManager
from .db import PostgreSQLManager

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
        schema_only: bool = False
    ) -> Tuple[bool, str]:
        """
        Sync a database from source to destination.
        
        Args:
            database_name: Name of database to sync
            drop_existing: Whether to drop existing database at destination
            data_only: Sync only data (no schema)
            schema_only: Sync only schema (no data)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            console.print(f"[blue]🔄 Starting database sync: {database_name}[/blue]")
            console.print(f"[blue]   Source: {self._get_host_description(self.source_config)}[/blue]")
            console.print(f"[blue]   Destination: {self._get_host_description(self.destination_config)}[/blue]")
            
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
    ) -> Tuple[bool, str]:
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
    ) -> Tuple[bool, str]:
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
                "--username", self.source_config.user,
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
    ) -> Tuple[bool, str]:
        """Create a database dump from SSH host."""
        console.print(f"[blue]🔗 Creating dump via SSH: {self.source_config.ssh_config}[/blue]")
        
        # For now, return placeholder - will be implemented when SSH functionality is ready
        console.print("[yellow]⚠️  SSH dump creation will be implemented with SSH functionality[/yellow]")
        console.print(f"[yellow]   Would execute: ssh {self.source_config.ssh_config} 'pg_dump ...'[/yellow]")
        
        # Create a placeholder dump file for testing
        dump_file.write_text("-- Placeholder dump file\n-- SSH dump functionality coming soon\n")
        
        return False, "SSH dump creation not yet implemented"
    
    def _transfer_dump_file(self, dump_file: Path) -> Tuple[bool, str]:
        """Transfer dump file between hosts if needed."""
        # For local-to-local sync, no transfer needed
        if isinstance(self.source_config, LocalHost) and isinstance(self.destination_config, LocalHost):
            return True, "No file transfer needed for local-to-local sync"
        
        console.print("[blue]📁 Transferring dump file...[/blue]")
        
        # For now, return placeholder for SSH transfers
        console.print("[yellow]⚠️  SSH file transfer will be implemented with SSH functionality[/yellow]")
        
        if isinstance(self.source_config, SSHHost):
            console.print(f"[yellow]   Would download: scp {self.source_config.ssh_config}:remote_file {dump_file}[/yellow]")
        
        if isinstance(self.destination_config, SSHHost):
            console.print(f"[yellow]   Would upload: scp {dump_file} {self.destination_config.ssh_config}:remote_file[/yellow]")
        
        return False, "SSH file transfer not yet implemented"
    
    def _restore_dump(
        self, 
        database_name: str, 
        dump_file: Path, 
        drop_existing: bool = False
    ) -> Tuple[bool, str]:
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
    ) -> Tuple[bool, str]:
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
                    "--username", self.destination_config.user,
                    "--if-exists",
                    database_name
                ]
                
                subprocess.run(drop_cmd, env=env, capture_output=True, timeout=30)
            
            # Create database
            createdb_cmd = [
                "createdb",
                "--host", self.destination_config.host,
                "--port", str(self.destination_config.port),
                "--username", self.destination_config.user,
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
                "--username", self.destination_config.user,
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
    ) -> Tuple[bool, str]:
        """Restore database dump to SSH host."""
        console.print(f"[blue]🔗 Restoring via SSH: {self.destination_config.ssh_config}[/blue]")
        
        # For now, return placeholder - will be implemented when SSH functionality is ready
        console.print("[yellow]⚠️  SSH restore will be implemented with SSH functionality[/yellow]")
        console.print(f"[yellow]   Would execute: ssh {self.destination_config.ssh_config} 'psql ...'[/yellow]")
        
        return False, "SSH restore not yet implemented"
    
    def _cleanup(self):
        """Clean up temporary files."""
        if self.temp_dir and Path(self.temp_dir).exists():
            import shutil
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                console.print(f"[yellow]⚠️  Warning: Could not clean up temporary directory: {e}[/yellow]")
    
    def list_databases(self, host_config: HostConfig) -> Tuple[bool, List[str], str]:
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
    
    def _list_local_databases(self, host_config: LocalHost) -> Tuple[bool, List[str], str]:
        """List databases on local PostgreSQL."""
        try:
            cmd = [
                "psql",
                "--host", host_config.host,
                "--port", str(host_config.port),
                "--username", host_config.user,
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
    
    def _list_ssh_databases(self, host_config: SSHHost) -> Tuple[bool, List[str], str]:
        """List databases on SSH host."""
        console.print(f"[blue]🔗 Listing databases via SSH: {host_config.ssh_config}[/blue]")
        
        # Placeholder for SSH implementation
        console.print("[yellow]⚠️  SSH database listing will be implemented with SSH functionality[/yellow]")
        
        return False, [], "SSH database listing not yet implemented" 