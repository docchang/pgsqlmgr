"""PostgreSQL database operations and installation management."""

import platform
import subprocess
from pathlib import Path
from typing import Any

import psycopg2
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from .config import HostConfig, LocalHost, SSHHost
from .ssh import SSHManager

console = Console()


def _get_auth_help_message(host_config: HostConfig) -> str:
    """Get helpful authentication error message with .pgpass guidance."""
    if isinstance(host_config, LocalHost):
        return (
            f"\n\n💡 Authentication Help:\n"
            f"Set up PostgreSQL authentication in ~/.pgpass:\n"
            f"  {host_config.host}:{host_config.port}:*:{host_config.superuser}:your_password\n"
            f"Then run: chmod 600 ~/.pgpass"
        )
    elif isinstance(host_config, SSHHost):
        return (
            f"\n\n💡 Authentication Help:\n"
            f"For SSH connections, ensure:\n"
            f"1. SSH access is configured in ~/.ssh/config\n"
            f"2. PostgreSQL authentication is set up on the remote host\n"
            f"3. The user '{host_config.superuser}' has appropriate permissions"
        )
    else:
        return ""


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
        self._connection: psycopg2.extensions.connection | None = None

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

    def list_databases(self) -> list[str]:
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

    def drop_database(self, database_name: str, force: bool = False) -> tuple[bool, str]:
        """
        Drop a database.

        Args:
            database_name: Name of the database to drop
            force: Force drop without confirmation

        Returns:
            Tuple of (success, message)

        Raises:
            ValueError: If database_name is invalid
        """
        # Validate database name
        if not database_name or not database_name.strip():
            raise ValueError("Database name cannot be empty")

        database_name = database_name.strip()

        # Prevent deletion of system databases
        system_databases = {'postgres', 'template0', 'template1'}
        if database_name.lower() in system_databases:
            return False, f"Cannot delete system database '{database_name}'"

        if isinstance(self.config, LocalHost):
            return self._drop_local_database(database_name, force)
        elif isinstance(self.config, SSHHost):
            return self._drop_ssh_database(database_name, force)
        else:
            return False, "Unsupported host type for database deletion"

    def _drop_local_database(self, database_name: str, force: bool = False) -> tuple[bool, str]:
        """Drop a database on local PostgreSQL."""
        try:
            # Build dropdb command
            cmd = [
                "dropdb",
                "--host", self.config.host,
                "--port", str(self.config.port),
                "--username", self.config.superuser,
                "--if-exists",  # Don't error if database doesn't exist
                database_name
            ]

            # Execute dropdb command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60  # 1 minute timeout
            )

            if result.returncode == 0:
                return True, f"Database '{database_name}' deleted successfully"
            else:
                # Check if it's just a "database doesn't exist" message
                if "does not exist" in result.stderr.lower():
                    return True, f"Database '{database_name}' does not exist (already deleted)"
                else:
                    error_msg = f"Failed to delete database: {result.stderr.strip()}"
                    if "authentication failed" in result.stderr.lower() or "password" in result.stderr.lower():
                        error_msg += _get_auth_help_message(self.config)
                    return False, error_msg

        except subprocess.TimeoutExpired:
            return False, f"Database deletion timed out for '{database_name}'"
        except FileNotFoundError:
            return False, "dropdb command not found. Ensure PostgreSQL client tools are installed."
        except Exception as e:
            return False, f"Error deleting database '{database_name}': {e}"

    def _drop_ssh_database(self, database_name: str, force: bool = False) -> tuple[bool, str]:
        """Drop a database on SSH host."""
        try:
            console.print(f"[blue]🔗 Deleting database via SSH: {self.config.ssh_config}[/blue]")

            # Use sudo -u {user} for SSH connections (same pattern as sync)
            ssh_cmd = [
                "ssh",
                self.config.ssh_config,
                f"sudo -u {self.config.superuser} dropdb --if-exists {database_name}"
            ]

            console.print(f"[blue]   Executing: {' '.join(ssh_cmd)}[/blue]")

            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=60  # 1 minute timeout
            )

            if result.returncode == 0:
                return True, f"Database '{database_name}' deleted successfully via SSH"
            else:
                # Check if it's just a "database doesn't exist" message
                if "does not exist" in result.stderr.lower():
                    return True, f"Database '{database_name}' does not exist on SSH host (already deleted)"
                else:
                    return False, f"SSH dropdb failed: {result.stderr.strip()}"

        except subprocess.TimeoutExpired:
            return False, f"SSH database deletion timed out for '{database_name}'"
        except Exception as e:
            return False, f"Error deleting database '{database_name}' via SSH: {e}"

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

    def get_database_info(self, database_name: str) -> dict[str, Any]:
        """
        Get information about a database.

        Args:
            database_name: Name of the database

        Returns:
            Dictionary with database information
        """
        if isinstance(self.config, LocalHost):
            return self._get_local_database_info(database_name)
        elif isinstance(self.config, SSHHost):
            return self._get_ssh_database_info(database_name)
        else:
            return {"error": "Unsupported host type"}

    def _get_local_database_info(self, database_name: str) -> dict[str, Any]:
        """Get database information from local PostgreSQL."""
        try:
            # Query to get database information
            query = """
            SELECT
                d.datname as name,
                pg_catalog.pg_get_userbyid(d.datdba) as owner,
                pg_catalog.pg_encoding_to_char(d.encoding) as encoding,
                d.datcollate as collate,
                d.datctype as ctype,
                pg_catalog.pg_size_pretty(pg_catalog.pg_database_size(d.datname)) as size,
                d.datconnlimit as connection_limit,
                (SELECT count(*) FROM pg_stat_activity WHERE datname = d.datname) as active_connections
            FROM pg_catalog.pg_database d
            WHERE d.datname = %s;
            """

            cmd = [
                "psql",
                "--host", self.config.host,
                "--port", str(self.config.port),
                "--username", self.config.superuser,
                "--dbname", "postgres",  # Connect to postgres database to query
                "--tuples-only",
                "--no-align",
                "--field-separator=|",
                "--command", query.replace("%s", f"'{database_name}'")
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0 and result.stdout.strip():
                # Parse the result
                line = result.stdout.strip()
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 8:
                        return {
                            "name": parts[0].strip(),
                            "owner": parts[1].strip(),
                            "encoding": parts[2].strip(),
                            "collate": parts[3].strip(),
                            "ctype": parts[4].strip(),
                            "size": parts[5].strip(),
                            "connection_limit": parts[6].strip(),
                            "active_connections": parts[7].strip(),
                            "exists": True
                        }

            # Check for authentication errors
            if result.returncode != 0:
                error_msg = f"Failed to get database info: {result.stderr.strip()}"
                if "authentication failed" in result.stderr.lower() or "password" in result.stderr.lower():
                    error_msg += _get_auth_help_message(self.config)
                return {"exists": False, "error": error_msg}

            return {"exists": False, "error": "Database not found"}

        except Exception as e:
            return {"exists": False, "error": f"Failed to get database info: {e}"}

    def _get_ssh_database_info(self, database_name: str) -> dict[str, Any]:
        """Get database information from SSH host."""
        try:
            # Same query as local but executed via SSH
            query = """
            SELECT
                d.datname as name,
                pg_catalog.pg_get_userbyid(d.datdba) as owner,
                pg_catalog.pg_encoding_to_char(d.encoding) as encoding,
                d.datcollate as collate,
                d.datctype as ctype,
                pg_catalog.pg_size_pretty(pg_catalog.pg_database_size(d.datname)) as size,
                d.datconnlimit as connection_limit,
                (SELECT count(*) FROM pg_stat_activity WHERE datname = d.datname) as active_connections
            FROM pg_catalog.pg_database d
            WHERE d.datname = '{database_name}';
            """

            ssh_cmd = [
                "ssh",
                self.config.ssh_config,
                f"sudo -u {self.config.superuser} psql --dbname postgres --tuples-only --no-align --field-separator='|' --command \"{query}\""
            ]

            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0 and result.stdout.strip():
                # Parse the result
                line = result.stdout.strip()
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 8:
                        return {
                            "name": parts[0].strip(),
                            "owner": parts[1].strip(),
                            "encoding": parts[2].strip(),
                            "collate": parts[3].strip(),
                            "ctype": parts[4].strip(),
                            "size": parts[5].strip(),
                            "connection_limit": parts[6].strip(),
                            "active_connections": parts[7].strip(),
                            "exists": True
                        }

            return {"exists": False, "error": "Database not found"}

        except Exception as e:
            return {"exists": False, "error": f"Failed to get database info via SSH: {e}"}

    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None


class PostgreSQLManager:
    """Manage PostgreSQL installation, configuration, and operations."""

    def __init__(self, host_config: HostConfig):
        """Initialize PostgreSQL manager with host configuration."""
        self.host_config = host_config
        self.is_local = isinstance(host_config, LocalHost)
        self.is_ssh = isinstance(host_config, SSHHost)
        self.ssh_manager = None

        if isinstance(host_config, SSHHost):
            self.ssh_manager = SSHManager(host_config)

    def check_postgresql_installation(self) -> tuple[bool, str, str | None]:
        """
        Check if PostgreSQL is installed on the host.

        Returns:
            Tuple of (is_installed, message, version)
        """
        if self.is_local:
            return self._check_local_postgresql()
        elif self.is_ssh:
            return self._check_ssh_postgresql()
        else:
            return False, "Unsupported host configuration", None

    def _check_local_postgresql(self) -> tuple[bool, str, str | None]:
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

    def _check_ssh_postgresql(self) -> tuple[bool, str, str | None]:
        """Check PostgreSQL installation on SSH host."""
        try:
            console.print(f"[blue]🔗 Checking PostgreSQL on {self.host_config.ssh_config}...[/blue]")

            # Check if PostgreSQL is installed
            result = subprocess.run(
                ["ssh", self.host_config.ssh_config, "psql --version"],
                capture_output=True,
                text=True,
                timeout=5  # Reduced from 30 to 5 seconds for quick status checks
            )

            if result.returncode == 0:
                version = result.stdout.strip()
                console.print(f"[green]✅ PostgreSQL found: {version}[/green]")
                return True, f"PostgreSQL installed: {version}", version
            else:
                console.print(f"[yellow]⚠️  PostgreSQL not found on {self.host_config.ssh_config}[/yellow]")
                return False, "PostgreSQL not installed", None

        except subprocess.TimeoutExpired:
            return False, "SSH connection timed out", None
        except Exception as e:
            return False, f"SSH check failed: {e}", None

    def check_service_status(self) -> tuple[bool, str]:
        """
        Check if PostgreSQL service is running.

        Returns:
            Tuple of (is_running, status_message)
        """
        if isinstance(self.host_config, LocalHost):
            return self._check_local_service()
        elif isinstance(self.host_config, SSHHost):
            return self._check_ssh_service()
        else:
            return False, "Unsupported host type for service check"

    def _check_local_service(self) -> tuple[bool, str]:
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

    def _check_ssh_service(self) -> tuple[bool, str]:
        """Check PostgreSQL service status via SSH."""
        console.print(f"[blue]🔍 Checking PostgreSQL service on {self.host_config.ssh_config}...[/blue]")

        try:
            # Check if PostgreSQL service is running
            result = subprocess.run(
                ["ssh", self.host_config.ssh_config, "systemctl is-active postgresql || sudo systemctl is-active postgresql"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0 and "active" in result.stdout:
                console.print(f"[green]✅ PostgreSQL service is running on {self.host_config.ssh_config}[/green]")
                return True, "PostgreSQL service is running"
            else:
                console.print(f"[yellow]⚠️  PostgreSQL service not running on {self.host_config.ssh_config}[/yellow]")
                return False, "PostgreSQL service not running"

        except subprocess.TimeoutExpired:
            return False, "SSH service check timed out"
        except Exception as e:
            return False, f"SSH service check failed: {e}"

    def install_postgresql(self) -> tuple[bool, str]:
        """
        Install PostgreSQL on the host with intelligent OS detection.

        Returns:
            Tuple of (success, message)
        """
        if self.is_local:
            return self._install_local_postgresql()
        elif self.is_ssh:
            return self._install_ssh_postgresql()
        else:
            return False, "Unsupported host configuration"

    def _install_local_postgresql(self) -> tuple[bool, str]:
        """Install PostgreSQL locally."""
        system = platform.system()

        if system == "Darwin":  # macOS
            return self._install_macos()
        elif system == "Linux":
            return self._install_linux()
        else:
            return False, f"Automatic installation not supported on {system}. Please install PostgreSQL manually."

    def _install_macos(self) -> tuple[bool, str]:
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

    def _install_linux(self) -> tuple[bool, str]:
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

    def _install_ssh_postgresql(self) -> tuple[bool, str]:
        """Install PostgreSQL on SSH host with OS detection and user setup."""
        try:
            console.print(f"[blue]🚀 Installing PostgreSQL on {self.host_config.ssh_config}...[/blue]")

            # Step 1: Detect operating system
            os_info = self._detect_ssh_os()
            if not os_info:
                return False, "Could not detect operating system"

            os_type, os_version = os_info
            console.print(f"[blue]🔍 Detected OS: {os_type} {os_version}[/blue]")

            # Step 2: Install PostgreSQL based on OS
            install_success, install_msg = self._install_postgresql_by_os(os_type, os_version)
            if not install_success:
                return False, f"Installation failed: {install_msg}"

            # Step 3: Setup PostgreSQL user and configuration
            setup_success, setup_msg = self._setup_postgresql_user()
            if not setup_success:
                return False, f"User setup failed: {setup_msg}"

            console.print(f"[green]✅ PostgreSQL successfully installed and configured on {self.host_config.ssh_config}[/green]")
            return True, "PostgreSQL installed and configured successfully"

        except Exception as e:
            return False, f"Installation error: {e}"

    def _detect_ssh_os(self) -> tuple[str, str] | None:
        """Detect operating system on SSH host."""
        try:
            # Try to get OS information
            result = subprocess.run(
                ["ssh", self.host_config.ssh_config, "cat /etc/os-release 2>/dev/null || uname -s"],
                capture_output=True,
                text=True,
                timeout=5  # Reduced from 30 to 5 seconds for quick status checks
            )

            if result.returncode != 0:
                return None

            output = result.stdout.strip()

            # Parse os-release file
            if "ID=" in output:
                os_info = {}
                for line in output.split('\n'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        os_info[key] = value.strip('"')

                os_id = os_info.get('ID', '').lower()
                version = os_info.get('VERSION_ID', 'unknown')

                return (os_id, version)

            # Fallback for macOS
            elif "Darwin" in output:
                return ("macos", "unknown")

            return None

        except Exception:
            return None

    def _install_postgresql_by_os(self, os_type: str, os_version: str) -> tuple[bool, str]:
        """Install PostgreSQL based on detected OS."""
        installation_commands = self._get_installation_commands(os_type)

        if not installation_commands:
            return False, f"Unsupported operating system: {os_type}"

        console.print(f"[blue]📦 Installing PostgreSQL using {installation_commands['name']}...[/blue]")

        # Execute installation commands
        for description, command in installation_commands['commands']:
            console.print(f"[blue]   {description}[/blue]")

            result = subprocess.run(
                ["ssh", self.host_config.ssh_config, command],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout for installations
            )

            if result.returncode != 0:
                return False, f"{description} failed: {result.stderr}"

        return True, f"PostgreSQL installed using {installation_commands['name']}"

    def _get_installation_commands(self, os_type: str) -> dict | None:
        """Get installation commands for specific OS."""
        commands = {
            'ubuntu': {
                'name': 'apt (Ubuntu/Debian)',
                'commands': [
                    ("Updating package list", "sudo apt update"),
                    ("Installing PostgreSQL", "sudo apt install -y postgresql postgresql-contrib"),
                    ("Starting PostgreSQL service", "sudo systemctl start postgresql"),
                    ("Enabling PostgreSQL service", "sudo systemctl enable postgresql"),
                ]
            },
            'debian': {
                'name': 'apt (Debian)',
                'commands': [
                    ("Updating package list", "sudo apt update"),
                    ("Installing PostgreSQL", "sudo apt install -y postgresql postgresql-contrib"),
                    ("Starting PostgreSQL service", "sudo systemctl start postgresql"),
                    ("Enabling PostgreSQL service", "sudo systemctl enable postgresql"),
                ]
            },
            'centos': {
                'name': 'yum (CentOS/RHEL)',
                'commands': [
                    ("Installing PostgreSQL", "sudo yum install -y postgresql-server postgresql-contrib"),
                    ("Initializing database", "sudo postgresql-setup initdb"),
                    ("Starting PostgreSQL service", "sudo systemctl start postgresql"),
                    ("Enabling PostgreSQL service", "sudo systemctl enable postgresql"),
                ]
            },
            'rhel': {
                'name': 'yum (Red Hat)',
                'commands': [
                    ("Installing PostgreSQL", "sudo yum install -y postgresql-server postgresql-contrib"),
                    ("Initializing database", "sudo postgresql-setup initdb"),
                    ("Starting PostgreSQL service", "sudo systemctl start postgresql"),
                    ("Enabling PostgreSQL service", "sudo systemctl enable postgresql"),
                ]
            },
            'fedora': {
                'name': 'dnf (Fedora)',
                'commands': [
                    ("Installing PostgreSQL", "sudo dnf install -y postgresql-server postgresql-contrib"),
                    ("Initializing database", "sudo postgresql-setup --initdb"),
                    ("Starting PostgreSQL service", "sudo systemctl start postgresql"),
                    ("Enabling PostgreSQL service", "sudo systemctl enable postgresql"),
                ]
            },
            'macos': {
                'name': 'Homebrew (macOS)',
                'commands': [
                    ("Installing PostgreSQL", "brew install postgresql"),
                    ("Starting PostgreSQL service", "brew services start postgresql"),
                ]
            },
            'alpine': {
                'name': 'apk (Alpine Linux)',
                'commands': [
                    ("Updating package index", "sudo apk update"),
                    ("Installing PostgreSQL", "sudo apk add postgresql postgresql-contrib"),
                    ("Initializing database", "sudo -u postgres initdb -D /var/lib/postgresql/data"),
                    ("Starting PostgreSQL service", "sudo rc-service postgresql start"),
                    ("Adding to startup", "sudo rc-update add postgresql"),
                ]
            }
        }

        return commands.get(os_type.lower())

    def _setup_postgresql_user(self) -> tuple[bool, str]:
        """Setup PostgreSQL superuser without password."""
        try:
            console.print(f"[blue]👤 Setting up PostgreSQL superuser on {self.host_config.ssh_config}...[/blue]")

            # Use the configured superuser from the host config
            username = self.host_config.superuser
            console.print(f"[blue]   Using superuser: {username}[/blue]")

            # Create PostgreSQL superuser without password (trusted authentication)
            # This is more secure for local/SSH environments where access is already controlled
            create_user_cmd = f"sudo -u postgres psql -c \"DO \\$\\$ BEGIN IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = '{username}') THEN CREATE USER {username} WITH SUPERUSER CREATEDB CREATEROLE; END IF; END \\$\\$;\""

            result = subprocess.run(
                ["ssh", self.host_config.ssh_config, create_user_cmd],
                capture_output=True,
                text=True,
                timeout=60
            )

            # Check if user creation succeeded
            if result.returncode == 0:
                console.print(f"[green]✅ PostgreSQL superuser '{username}' ready (no password required)[/green]")
                console.print("[blue]💡 User can connect without password via local/SSH trust authentication[/blue]")

                return True, f"Superuser '{username}' configured successfully without password"
            else:
                return False, f"Failed to create user: {result.stderr}"

        except Exception as e:
            return False, f"User setup error: {e}"

    def start_service(self) -> tuple[bool, str]:
        """Start PostgreSQL service."""
        if isinstance(self.host_config, LocalHost):
            return self._start_local_service()
        elif isinstance(self.host_config, SSHHost):
            return self._start_ssh_service()
        else:
            return False, "Unsupported host type for service management"

    def _start_local_service(self) -> tuple[bool, str]:
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

    def _start_ssh_service(self) -> tuple[bool, str]:
        """Start PostgreSQL service via SSH."""
        console.print(f"[blue]🚀 Starting PostgreSQL service on {self.host_config.ssh_config}...[/blue]")

        try:
            # Try to start PostgreSQL service
            result = subprocess.run(
                ["ssh", self.host_config.ssh_config, "sudo systemctl start postgresql"],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                console.print(f"[green]✅ PostgreSQL service started on {self.host_config.ssh_config}[/green]")
                return True, "PostgreSQL service started successfully"
            else:
                return False, f"Failed to start PostgreSQL service: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, "SSH service start timed out"
        except Exception as e:
            return False, f"SSH service start failed: {e}"

    def uninstall_postgresql(self) -> tuple[bool, str]:
        """
        Uninstall PostgreSQL from the host.

        Returns:
            Tuple of (success, message)
        """
        if self.is_local:
            return self._uninstall_local_postgresql()
        elif self.is_ssh:
            return self._uninstall_ssh_postgresql()
        else:
            return False, "Unsupported host configuration"

    def _uninstall_local_postgresql(self) -> tuple[bool, str]:
        """Uninstall PostgreSQL locally."""
        system = platform.system()

        if system == "Darwin":  # macOS
            return self._uninstall_macos()
        elif system == "Linux":
            return self._uninstall_linux()
        else:
            return False, f"Automatic uninstallation not supported on {system}. Please uninstall PostgreSQL manually."

    def _uninstall_macos(self) -> tuple[bool, str]:
        """Uninstall PostgreSQL on macOS using Homebrew."""
        console.print("[blue]🍺 Uninstalling PostgreSQL via Homebrew...[/blue]")

        try:
            # Stop the service first
            console.print("[blue]🛑 Stopping PostgreSQL service...[/blue]")
            stop_result = subprocess.run(
                ["brew", "services", "stop", "postgresql@15"],
                capture_output=True,
                text=True,
                timeout=30
            )

            # Uninstall PostgreSQL (ignore errors if not installed)
            console.print("[blue]🗑️  Removing PostgreSQL package...[/blue]")
            result = subprocess.run(
                ["brew", "uninstall", "--ignore-dependencies", "postgresql@15"],
                capture_output=True,
                text=True,
                timeout=120
            )

            # Also try to remove any PostgreSQL data directories
            console.print("[blue]🗑️  Removing PostgreSQL data directories...[/blue]")
            data_cleanup = subprocess.run(
                ["rm", "-rf", "/opt/homebrew/var/postgresql@15", "/usr/local/var/postgresql@15"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0 or "No such keg" in result.stderr:
                return True, "PostgreSQL uninstalled successfully"
            else:
                return False, f"Uninstallation failed: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, "Uninstallation timed out"
        except Exception as e:
            return False, f"Uninstallation error: {e}"

    def _uninstall_linux(self) -> tuple[bool, str]:
        """Uninstall PostgreSQL on Linux (placeholder)."""
        console.print("[blue]🐧 Uninstalling PostgreSQL on Linux...[/blue]")

        instructions = """
Manual PostgreSQL uninstallation required:

Ubuntu/Debian:
  sudo systemctl stop postgresql
  sudo systemctl disable postgresql
  sudo apt remove --purge postgresql postgresql-*
  sudo rm -rf /var/lib/postgresql/
  sudo rm -rf /etc/postgresql/

CentOS/RHEL:
  sudo systemctl stop postgresql
  sudo systemctl disable postgresql
  sudo yum remove postgresql postgresql-server
  sudo rm -rf /var/lib/pgsql/
"""
        console.print(Panel(instructions, title="Manual Uninstallation Required", style="yellow"))
        return False, "Automatic Linux uninstallation not yet implemented. See instructions above."

    def _uninstall_ssh_postgresql(self) -> tuple[bool, str]:
        """Uninstall PostgreSQL on SSH host with OS detection."""
        try:
            console.print(f"[blue]🚀 Uninstalling PostgreSQL on {self.host_config.ssh_config}...[/blue]")

            # Step 1: Detect operating system
            os_info = self._detect_ssh_os()
            if not os_info:
                return False, "Could not detect operating system"

            os_type, os_version = os_info
            console.print(f"[blue]🔍 Detected OS: {os_type} {os_version}[/blue]")

            # Step 2: Stop PostgreSQL service
            console.print("[blue]🛑 Stopping PostgreSQL service...[/blue]")
            stop_result = subprocess.run(
                ["ssh", self.host_config.ssh_config, "sudo systemctl stop postgresql"],
                capture_output=True,
                text=True,
                timeout=30
            )

            # Step 3: Uninstall PostgreSQL based on OS
            uninstall_success, uninstall_msg = self._uninstall_postgresql_by_os(os_type, os_version)
            if not uninstall_success:
                return False, f"Uninstallation failed: {uninstall_msg}"

            console.print(f"[green]✅ PostgreSQL successfully uninstalled from {self.host_config.ssh_config}[/green]")
            return True, "PostgreSQL uninstalled successfully"

        except Exception as e:
            return False, f"Uninstallation error: {e}"

    def _uninstall_postgresql_by_os(self, os_type: str, os_version: str) -> tuple[bool, str]:
        """Uninstall PostgreSQL based on detected OS."""
        uninstall_commands = self._get_uninstall_commands(os_type)

        if not uninstall_commands:
            return False, f"Unsupported operating system: {os_type}"

        console.print(f"[blue]🗑️  Uninstalling PostgreSQL using {uninstall_commands['name']}...[/blue]")

        # Execute uninstall commands
        for description, command in uninstall_commands['commands']:
            console.print(f"[blue]   {description}[/blue]")

            result = subprocess.run(
                ["ssh", self.host_config.ssh_config, command],
                capture_output=True,
                text=True,
                timeout=300  # Increased from 120 to 300 seconds (5 minutes) for uninstall operations
            )

            # For uninstall operations, some failures are acceptable (e.g., package not found)
            if result.returncode != 0 and "not found" not in result.stderr.lower() and "not installed" not in result.stderr.lower():
                console.print(f"[yellow]⚠️  {description} warning: {result.stderr}[/yellow]")

        return True, f"PostgreSQL uninstalled using {uninstall_commands['name']}"

    def _get_uninstall_commands(self, os_type: str) -> dict | None:
        """Get uninstall commands for specific OS."""
        commands = {
            'ubuntu': {
                'name': 'apt (Ubuntu/Debian)',
                'commands': [
                    ("Stopping PostgreSQL service", "sudo systemctl stop postgresql"),
                    ("Disabling PostgreSQL service", "sudo systemctl disable postgresql"),
                    ("Removing PostgreSQL packages", "sudo apt remove --purge -y postgresql postgresql-*"),
                    ("Removing PostgreSQL data", "sudo rm -rf /var/lib/postgresql/"),
                    ("Removing PostgreSQL config", "sudo rm -rf /etc/postgresql/"),
                    ("Cleaning up packages", "sudo apt autoremove -y"),
                ]
            },
            'debian': {
                'name': 'apt (Debian)',
                'commands': [
                    ("Stopping PostgreSQL service", "sudo systemctl stop postgresql"),
                    ("Disabling PostgreSQL service", "sudo systemctl disable postgresql"),
                    ("Removing PostgreSQL packages", "sudo apt remove --purge -y postgresql postgresql-*"),
                    ("Removing PostgreSQL data", "sudo rm -rf /var/lib/postgresql/"),
                    ("Removing PostgreSQL config", "sudo rm -rf /etc/postgresql/"),
                    ("Cleaning up packages", "sudo apt autoremove -y"),
                ]
            },
            'centos': {
                'name': 'yum (CentOS/RHEL)',
                'commands': [
                    ("Stopping PostgreSQL service", "sudo systemctl stop postgresql"),
                    ("Disabling PostgreSQL service", "sudo systemctl disable postgresql"),
                    ("Removing PostgreSQL packages", "sudo yum remove -y postgresql-server postgresql-contrib"),
                    ("Removing PostgreSQL data", "sudo rm -rf /var/lib/pgsql/"),
                ]
            },
            'rhel': {
                'name': 'yum (Red Hat)',
                'commands': [
                    ("Stopping PostgreSQL service", "sudo systemctl stop postgresql"),
                    ("Disabling PostgreSQL service", "sudo systemctl disable postgresql"),
                    ("Removing PostgreSQL packages", "sudo yum remove -y postgresql-server postgresql-contrib"),
                    ("Removing PostgreSQL data", "sudo rm -rf /var/lib/pgsql/"),
                ]
            },
            'fedora': {
                'name': 'dnf (Fedora)',
                'commands': [
                    ("Stopping PostgreSQL service", "sudo systemctl stop postgresql"),
                    ("Disabling PostgreSQL service", "sudo systemctl disable postgresql"),
                    ("Removing PostgreSQL packages", "sudo dnf remove -y postgresql-server postgresql-contrib"),
                    ("Removing PostgreSQL data", "sudo rm -rf /var/lib/pgsql/"),
                ]
            }
        }

        return commands.get(os_type.lower())

    def backup_all_databases(self, backup_path: str | None = None) -> bool:
        """
        Create backups of all user databases before uninstallation.

        Args:
            backup_path: Directory to save backups (default: current directory)

        Returns:
            True if all backups succeeded, False otherwise
        """
        try:
            console.print("[blue]🔍 Discovering databases to backup...[/blue]")
            
            # Create database manager to list databases
            db_manager = DatabaseManager(self.host_config)
            databases = db_manager.list_databases()
            
            # Filter out system databases
            user_databases = [db for db in databases if db not in ['postgres', 'template0', 'template1']]
            
            if not user_databases:
                console.print("[blue]ℹ️  No user databases found to backup[/blue]")
                return True
            
            console.print(f"[blue]📦 Found {len(user_databases)} user database(s) to backup: {', '.join(user_databases)}[/blue]")
            
            # Set backup directory
            if backup_path:
                backup_dir = Path(backup_path)
            else:
                backup_dir = Path.cwd()
            
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Backup each database
            backup_success = True
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            for db_name in user_databases:
                backup_filename = f"{db_name}_backup_{timestamp}.sql"
                backup_file = backup_dir / backup_filename
                
                console.print(f"[blue]💾 Backing up database '{db_name}' to {backup_file}...[/blue]")
                
                try:
                    db_manager.dump_database(db_name, backup_file)
                    console.print(f"[green]✅ Database '{db_name}' backed up successfully[/green]")
                except Exception as e:
                    console.print(f"[red]❌ Failed to backup database '{db_name}': {e}[/red]")
                    backup_success = False
            
            if backup_success:
                console.print(f"[green]✅ All databases backed up successfully to {backup_dir}[/green]")
            else:
                console.print(f"[yellow]⚠️  Some database backups failed. Check logs above.[/yellow]")
                
            return backup_success
            
        except Exception as e:
            console.print(f"[red]❌ Error during database backup: {e}[/red]")
            return False

    def check_update_available(self) -> tuple[bool, str]:
        """
        Check if PostgreSQL update is available.

        Returns:
            Tuple of (update_available, update_info)
        """
        if self.is_local:
            return self._check_local_update()
        elif self.is_ssh:
            return self._check_ssh_update()
        else:
            return False, "Update check not supported for this host type"

    def _check_local_update(self) -> tuple[bool, str]:
        """Check for PostgreSQL updates locally."""
        system = platform.system()

        try:
            if system == "Darwin":  # macOS
                # Check if there's a newer version available via Homebrew
                result = subprocess.run(
                    ["brew", "outdated", "postgresql@15"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    return True, "Update available via Homebrew"
                else:
                    return False, "PostgreSQL is up to date"

            elif system == "Linux":
                # Check for updates using package manager
                result = subprocess.run(
                    ["apt", "list", "--upgradable", "postgresql"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0 and "postgresql" in result.stdout:
                    return True, "Update available via package manager"
                else:
                    return False, "PostgreSQL is up to date"
            else:
                return False, f"Update check not supported on {system}"

        except subprocess.TimeoutExpired:
            return False, "Update check timed out"
        except Exception as e:
            return False, f"Error checking for updates: {e}"

    def _check_ssh_update(self) -> tuple[bool, str]:
        """Check for PostgreSQL updates on SSH host."""
        try:
            console.print(f"[blue]🔍 Checking for PostgreSQL updates on {self.host_config.ssh_config}...[/blue]")

            # Detect OS first
            os_info = self._detect_ssh_os()
            if not os_info:
                return False, "Could not detect operating system"

            os_type, _ = os_info

            # Check for updates based on OS
            if os_type.lower() in ['ubuntu', 'debian']:
                # Update package list and check for upgrades
                update_result = subprocess.run(
                    ["ssh", self.host_config.ssh_config, "sudo apt update && apt list --upgradable postgresql 2>/dev/null"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if update_result.returncode == 0 and "postgresql" in update_result.stdout:
                    return True, "Update available via apt"
                else:
                    return False, "PostgreSQL is up to date"

            elif os_type.lower() in ['centos', 'rhel']:
                # Check for updates using yum
                result = subprocess.run(
                    ["ssh", self.host_config.ssh_config, "yum list updates postgresql-server 2>/dev/null || echo 'No updates'"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0 and "postgresql-server" in result.stdout:
                    return True, "Update available via yum"
                else:
                    return False, "PostgreSQL is up to date"

            elif os_type.lower() == 'fedora':
                # Check for updates using dnf
                result = subprocess.run(
                    ["ssh", self.host_config.ssh_config, "dnf list updates postgresql-server 2>/dev/null || echo 'No updates'"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0 and "postgresql-server" in result.stdout:
                    return True, "Update available via dnf"
                else:
                    return False, "PostgreSQL is up to date"
            else:
                return False, f"Update check not supported for {os_type}"

        except subprocess.TimeoutExpired:
            return False, "Update check timed out"
        except Exception as e:
            return False, f"Error checking for updates: {e}"

    def update_postgresql(self) -> tuple[bool, str]:
        """
        Update PostgreSQL to the latest version.

        Returns:
            Tuple of (success, message)
        """
        if self.is_local:
            return self._update_local_postgresql()
        elif self.is_ssh:
            return self._update_ssh_postgresql()
        else:
            return False, "Update not supported for this host type"

    def _update_local_postgresql(self) -> tuple[bool, str]:
        """Update PostgreSQL locally."""
        system = platform.system()

        if system == "Darwin":  # macOS
            return self._update_macos()
        elif system == "Linux":
            return self._update_linux()
        else:
            return False, f"Automatic update not supported on {system}. Please update PostgreSQL manually."

    def _update_macos(self) -> tuple[bool, str]:
        """Update PostgreSQL on macOS using Homebrew."""
        console.print("[blue]🍺 Updating PostgreSQL via Homebrew...[/blue]")

        try:
            # Update Homebrew first
            console.print("[blue]📦 Updating Homebrew...[/blue]")
            update_result = subprocess.run(
                ["brew", "update"],
                capture_output=True,
                text=True,
                timeout=120
            )

            # Upgrade PostgreSQL
            console.print("[blue]⬆️  Upgrading PostgreSQL...[/blue]")
            result = subprocess.run(
                ["brew", "upgrade", "postgresql@15"],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )

            if result.returncode == 0:
                console.print("[green]✅ PostgreSQL updated successfully![/green]")
                
                # Restart the service
                console.print("[blue]🔄 Restarting PostgreSQL service...[/blue]")
                restart_result = subprocess.run(
                    ["brew", "services", "restart", "postgresql@15"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if restart_result.returncode == 0:
                    return True, "PostgreSQL updated and restarted successfully"
                else:
                    return True, "PostgreSQL updated but service restart failed. Restart manually with: brew services restart postgresql@15"
            else:
                return False, f"Update failed: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, "Update timed out"
        except Exception as e:
            return False, f"Update error: {e}"

    def _update_linux(self) -> tuple[bool, str]:
        """Update PostgreSQL on Linux (placeholder)."""
        console.print("[blue]🐧 Updating PostgreSQL on Linux...[/blue]")

        instructions = """
Manual PostgreSQL update required:

Ubuntu/Debian:
  sudo apt update
  sudo apt upgrade postgresql postgresql-contrib
  sudo systemctl restart postgresql

CentOS/RHEL:
  sudo yum update postgresql-server
  sudo systemctl restart postgresql

Fedora:
  sudo dnf update postgresql-server
  sudo systemctl restart postgresql
"""
        console.print(Panel(instructions, title="Manual Update Required", style="yellow"))
        return False, "Automatic Linux update not yet implemented. See instructions above."

    def _update_ssh_postgresql(self) -> tuple[bool, str]:
        """Update PostgreSQL on SSH host with OS detection."""
        try:
            console.print(f"[blue]🚀 Updating PostgreSQL on {self.host_config.ssh_config}...[/blue]")

            # Step 1: Detect operating system
            os_info = self._detect_ssh_os()
            if not os_info:
                return False, "Could not detect operating system"

            os_type, os_version = os_info
            console.print(f"[blue]🔍 Detected OS: {os_type} {os_version}[/blue]")

            # Step 2: Update PostgreSQL based on OS
            update_success, update_msg = self._update_postgresql_by_os(os_type, os_version)
            if not update_success:
                return False, f"Update failed: {update_msg}"

            console.print(f"[green]✅ PostgreSQL successfully updated on {self.host_config.ssh_config}[/green]")
            return True, "PostgreSQL updated successfully"

        except Exception as e:
            return False, f"Update error: {e}"

    def _update_postgresql_by_os(self, os_type: str, os_version: str) -> tuple[bool, str]:
        """Update PostgreSQL based on detected OS."""
        update_commands = self._get_update_commands(os_type)

        if not update_commands:
            return False, f"Unsupported operating system: {os_type}"

        console.print(f"[blue]⬆️  Updating PostgreSQL using {update_commands['name']}...[/blue]")

        # Execute update commands
        for description, command in update_commands['commands']:
            console.print(f"[blue]   {description}[/blue]")

            result = subprocess.run(
                ["ssh", self.host_config.ssh_config, command],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout for update operations
            )

            if result.returncode != 0:
                return False, f"{description} failed: {result.stderr}"

        return True, f"PostgreSQL updated using {update_commands['name']}"

    def _get_update_commands(self, os_type: str) -> dict | None:
        """Get update commands for specific OS."""
        commands = {
            'ubuntu': {
                'name': 'apt (Ubuntu/Debian)',
                'commands': [
                    ("Updating package list", "sudo apt update"),
                    ("Upgrading PostgreSQL", "sudo apt upgrade -y postgresql postgresql-contrib"),
                    ("Restarting PostgreSQL service", "sudo systemctl restart postgresql"),
                ]
            },
            'debian': {
                'name': 'apt (Debian)',
                'commands': [
                    ("Updating package list", "sudo apt update"),
                    ("Upgrading PostgreSQL", "sudo apt upgrade -y postgresql postgresql-contrib"),
                    ("Restarting PostgreSQL service", "sudo systemctl restart postgresql"),
                ]
            },
            'centos': {
                'name': 'yum (CentOS/RHEL)',
                'commands': [
                    ("Updating PostgreSQL", "sudo yum update -y postgresql-server postgresql-contrib"),
                    ("Restarting PostgreSQL service", "sudo systemctl restart postgresql"),
                ]
            },
            'rhel': {
                'name': 'yum (Red Hat)',
                'commands': [
                    ("Updating PostgreSQL", "sudo yum update -y postgresql-server postgresql-contrib"),
                    ("Restarting PostgreSQL service", "sudo systemctl restart postgresql"),
                ]
            },
            'fedora': {
                'name': 'dnf (Fedora)',
                'commands': [
                    ("Updating PostgreSQL", "sudo dnf update -y postgresql-server postgresql-contrib"),
                    ("Restarting PostgreSQL service", "sudo systemctl restart postgresql"),
                ]
            }
        }

        return commands.get(os_type.lower())
