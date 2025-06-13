"""PostgreSQL database operations and installation management."""

import psycopg2
import subprocess
import platform
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Union
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .config import HostConfig, LocalHost, SSHHost
from .ssh import SSHManager

console = Console()

# PostgreSQL installation commands by platform
INSTALL_COMMANDS = {
    "Darwin": {  # macOS
        "check": ["brew", "--version"],
        "install": ["brew", "install", "postgresql@15"],
        "service_check": ["brew", "services", "list", "postgresql@15"],
        "service_start": ["brew", "services", "start", "postgresql@15"],
        "service_stop": ["brew", "services", "stop", "postgresql@15"],
    },
    "Linux": {
        "ubuntu": {
            "check": ["apt", "--version"],
            "install": ["sudo", "apt", "update", "&&", "sudo", "apt", "install", "-y", "postgresql", "postgresql-contrib"],
            "service_check": ["systemctl", "is-active", "postgresql"],
            "service_start": ["sudo", "systemctl", "start", "postgresql"],
            "service_stop": ["sudo", "systemctl", "stop", "postgresql"],
        },
        "centos": {
            "check": ["yum", "--version"],
            "install": ["sudo", "yum", "install", "-y", "postgresql", "postgresql-server"],
            "service_check": ["systemctl", "is-active", "postgresql"],
            "service_start": ["sudo", "systemctl", "start", "postgresql"],
            "service_stop": ["sudo", "systemctl", "stop", "postgresql"],
        }
    }
}


class DatabaseManager:
    """Manage PostgreSQL database operations."""
    
    def __init__(self, host_config: HostConfig):
        """Initialize database manager with host configuration."""
        self.config = host_config
        self._connection: Optional[psycopg2.extensions.connection] = None
    
    def connect(self) -> psycopg2.extensions.connection:
        """
        Establish connection to PostgreSQL database.
        
        Returns:
            psycopg2 connection object
            
        Raises:
            psycopg2.Error: If unable to connect to database
        """
        # Implementation placeholder
        console.print("[yellow]⚠️  Database connection not implemented yet[/yellow]")
        raise NotImplementedError("Database connection functionality coming soon")
    
    def test_connection(self) -> bool:
        """
        Test database connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        # Implementation placeholder
        console.print("[yellow]⚠️  Connection test not implemented yet[/yellow]")
        return False
    
    def list_databases(self) -> List[str]:
        """
        List all databases on the PostgreSQL instance.
        
        Returns:
            List of database names
        """
        # Implementation placeholder
        console.print("[yellow]⚠️  Database listing not implemented yet[/yellow]")
        return []
    
    def database_exists(self, database_name: str) -> bool:
        """
        Check if a database exists.
        
        Args:
            database_name: Name of the database to check
            
        Returns:
            True if database exists, False otherwise
        """
        # Implementation placeholder
        console.print(f"[yellow]⚠️  Would check if database '{database_name}' exists[/yellow]")
        return False
    
    def create_database(self, database_name: str) -> None:
        """
        Create a new database.
        
        Args:
            database_name: Name of the database to create
            
        Raises:
            psycopg2.Error: If database creation fails
        """
        # Implementation placeholder
        console.print(f"[yellow]⚠️  Would create database '{database_name}'[/yellow]")
        raise NotImplementedError("Database creation functionality coming soon")
    
    def drop_database(self, database_name: str, force: bool = False) -> None:
        """
        Drop a database.
        
        Args:
            database_name: Name of the database to drop
            force: Force drop without confirmation
            
        Raises:
            psycopg2.Error: If database drop fails
        """
        # Implementation placeholder
        console.print(f"[yellow]⚠️  Would drop database '{database_name}' (force={force})[/yellow]")
        raise NotImplementedError("Database drop functionality coming soon")
    
    def dump_database(self, database_name: str, output_path: Path) -> None:
        """
        Create a dump of the specified database.
        
        Args:
            database_name: Name of the database to dump
            output_path: Path where to save the dump file
            
        Raises:
            RuntimeError: If pg_dump fails
        """
        # Implementation placeholder
        console.print(f"[yellow]⚠️  Would dump database '{database_name}' to {output_path}[/yellow]")
        raise NotImplementedError("Database dump functionality coming soon")
    
    def restore_database(self, database_name: str, dump_path: Path) -> None:
        """
        Restore a database from a dump file.
        
        Args:
            database_name: Name of the database to restore to
            dump_path: Path to the dump file
            
        Raises:
            RuntimeError: If pg_restore fails
        """
        # Implementation placeholder
        console.print(f"[yellow]⚠️  Would restore database '{database_name}' from {dump_path}[/yellow]")
        raise NotImplementedError("Database restore functionality coming soon")
    
    def get_database_info(self, database_name: str) -> Dict[str, Any]:
        """
        Get information about a database.
        
        Args:
            database_name: Name of the database
            
        Returns:
            Dictionary with database information
        """
        # Implementation placeholder
        console.print(f"[yellow]⚠️  Would get info for database '{database_name}'[/yellow]")
        return {}
    
    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None 


class PostgreSQLManager:
    """Manage PostgreSQL installation and operations."""
    
    def __init__(self, host_config: HostConfig):
        """Initialize PostgreSQL manager with host configuration."""
        self.config = host_config
        self.ssh_manager = None
        
        if isinstance(host_config, SSHHost):
            self.ssh_manager = SSHManager(host_config)
    
    def check_postgresql_installation(self) -> Tuple[bool, str, Optional[str]]:
        """
        Check if PostgreSQL is installed on the host.
        
        Returns:
            Tuple of (is_installed, status_message, version_info)
        """
        if isinstance(self.config, LocalHost):
            return self._check_local_installation()
        elif isinstance(self.config, SSHHost):
            return self._check_ssh_installation()
        else:
            return False, "Unsupported host type for PostgreSQL installation check", None
    
    def _check_local_installation(self) -> Tuple[bool, str, Optional[str]]:
        """Check PostgreSQL installation locally."""
        try:
            # Check if psql is available
            result = subprocess.run(
                ["psql", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                version_info = result.stdout.strip()
                return True, "PostgreSQL is installed locally", version_info
            else:
                return False, "PostgreSQL not found in PATH", None
                
        except subprocess.TimeoutExpired:
            return False, "PostgreSQL version check timed out", None
        except FileNotFoundError:
            return False, "PostgreSQL not installed (psql command not found)", None
        except Exception as e:
            return False, f"Error checking PostgreSQL installation: {e}", None
    
    def _check_ssh_installation(self) -> Tuple[bool, str, Optional[str]]:
        """Check PostgreSQL installation via SSH."""
        console.print(f"[blue]🔍 Checking PostgreSQL installation on {self.config.ssh_config}...[/blue]")
        
        # For now, return placeholder - will be implemented when SSH functionality is ready
        console.print("[yellow]⚠️  SSH installation check will be implemented with SSH functionality[/yellow]")
        console.print(f"[yellow]   Would execute: ssh {self.config.ssh_config} 'psql --version'[/yellow]")
        
        return False, "SSH installation check not yet implemented", None
    
    def check_service_status(self) -> Tuple[bool, str]:
        """
        Check if PostgreSQL service is running.
        
        Returns:
            Tuple of (is_running, status_message)
        """
        if isinstance(self.config, LocalHost):
            return self._check_local_service()
        elif isinstance(self.config, SSHHost):
            return self._check_ssh_service()
        else:
            return False, "Unsupported host type for service check"
    
    def _check_local_service(self) -> Tuple[bool, str]:
        """Check PostgreSQL service status locally."""
        system = platform.system()
        
        try:
            if system == "Darwin":  # macOS
                result = subprocess.run(
                    ["brew", "services", "list"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    # Check if postgresql is in the output and running
                    if "postgresql" in result.stdout and "started" in result.stdout:
                        return True, "PostgreSQL service is running"
                    else:
                        return False, "PostgreSQL service is not running"
                        
            elif system == "Linux":
                result = subprocess.run(
                    ["systemctl", "is-active", "postgresql"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0 and "active" in result.stdout:
                    return True, "PostgreSQL service is running"
                else:
                    return False, "PostgreSQL service is not running"
            else:
                return False, f"Service check not supported on {system}"
                
        except subprocess.TimeoutExpired:
            return False, "Service check timed out"
        except FileNotFoundError as e:
            return False, f"Service management tool not found: {e}"
        except Exception as e:
            return False, f"Error checking service status: {e}"
    
    def _check_ssh_service(self) -> Tuple[bool, str]:
        """Check PostgreSQL service status via SSH."""
        console.print(f"[blue]🔍 Checking PostgreSQL service on {self.config.ssh_config}...[/blue]")
        
        # Placeholder for SSH service check
        console.print("[yellow]⚠️  SSH service check will be implemented with SSH functionality[/yellow]")
        console.print(f"[yellow]   Would execute: ssh {self.config.ssh_config} 'systemctl is-active postgresql'[/yellow]")
        
        return False, "SSH service check not yet implemented"
    
    def install_postgresql(self) -> Tuple[bool, str]:
        """
        Install PostgreSQL on the host.
        
        Returns:
            Tuple of (success, message)
        """
        if isinstance(self.config, LocalHost):
            return self._install_local()
        elif isinstance(self.config, SSHHost):
            return self._install_ssh()
        else:
            return False, "Unsupported host type for PostgreSQL installation"
    
    def _install_local(self) -> Tuple[bool, str]:
        """Install PostgreSQL locally."""
        system = platform.system()
        
        if system == "Darwin":  # macOS
            return self._install_macos()
        elif system == "Linux":
            return self._install_linux()
        else:
            return False, f"Automatic installation not supported on {system}. Please install PostgreSQL manually."
    
    def _install_macos(self) -> Tuple[bool, str]:
        """Install PostgreSQL on macOS using Homebrew."""
        console.print("[blue]🍺 Installing PostgreSQL via Homebrew...[/blue]")
        
        try:
            # Check if Homebrew is installed
            result = subprocess.run(
                ["brew", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return False, "Homebrew not found. Please install Homebrew first: https://brew.sh"
            
            # Install PostgreSQL
            console.print("[blue]📦 Installing postgresql@15...[/blue]")
            result = subprocess.run(
                ["brew", "install", "postgresql@15"],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode == 0:
                console.print("[green]✅ PostgreSQL installed successfully![/green]")
                console.print("[blue]🚀 Starting PostgreSQL service...[/blue]")
                
                # Start the service
                start_result = subprocess.run(
                    ["brew", "services", "start", "postgresql@15"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if start_result.returncode == 0:
                    return True, "PostgreSQL installed and started successfully"
                else:
                    return True, "PostgreSQL installed but service start failed. Start manually with: brew services start postgresql@15"
            else:
                return False, f"Installation failed: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return False, "Installation timed out"
        except Exception as e:
            return False, f"Installation error: {e}"
    
    def _install_linux(self) -> Tuple[bool, str]:
        """Install PostgreSQL on Linux."""
        console.print("[blue]🐧 Installing PostgreSQL on Linux...[/blue]")
        
        # For now, provide instructions rather than automatic installation
        instructions = """
Please install PostgreSQL manually:

Ubuntu/Debian:
  sudo apt update
  sudo apt install postgresql postgresql-contrib
  sudo systemctl start postgresql
  sudo systemctl enable postgresql

CentOS/RHEL:
  sudo yum install postgresql postgresql-server
  sudo postgresql-setup initdb
  sudo systemctl start postgresql
  sudo systemctl enable postgresql
"""
        console.print(Panel(instructions, title="Manual Installation Required", style="yellow"))
        return False, "Automatic Linux installation not yet implemented. See instructions above."
    
    def _install_ssh(self) -> Tuple[bool, str]:
        """Install PostgreSQL via SSH."""
        console.print(f"[blue]🔧 Installing PostgreSQL on {self.config.ssh_config}...[/blue]")
        
        # Placeholder for SSH installation
        console.print("[yellow]⚠️  SSH installation will be implemented with SSH functionality[/yellow]")
        console.print(f"[yellow]   Would execute installation commands via: ssh {self.config.ssh_config}[/yellow]")
        
        return False, "SSH installation not yet implemented"
    
    def start_service(self) -> Tuple[bool, str]:
        """Start PostgreSQL service."""
        if isinstance(self.config, LocalHost):
            return self._start_local_service()
        elif isinstance(self.config, SSHHost):
            return self._start_ssh_service()
        else:
            return False, "Unsupported host type for service management"
    
    def _start_local_service(self) -> Tuple[bool, str]:
        """Start PostgreSQL service locally."""
        system = platform.system()
        
        try:
            if system == "Darwin":  # macOS
                result = subprocess.run(
                    ["brew", "services", "start", "postgresql@15"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            elif system == "Linux":
                result = subprocess.run(
                    ["sudo", "systemctl", "start", "postgresql"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            else:
                return False, f"Service management not supported on {system}"
            
            if result.returncode == 0:
                return True, "PostgreSQL service started successfully"
            else:
                return False, f"Failed to start service: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return False, "Service start timed out"
        except Exception as e:
            return False, f"Error starting service: {e}"
    
    def _start_ssh_service(self) -> Tuple[bool, str]:
        """Start PostgreSQL service via SSH."""
        console.print(f"[blue]🚀 Starting PostgreSQL service on {self.config.ssh_config}...[/blue]")
        
        # Placeholder for SSH service start
        console.print("[yellow]⚠️  SSH service management will be implemented with SSH functionality[/yellow]")
        
        return False, "SSH service management not yet implemented" 