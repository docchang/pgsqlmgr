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
                timeout=30
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
                timeout=30
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
        """Setup PostgreSQL user with prompted credentials."""
        try:
            console.print(f"[blue]👤 Setting up PostgreSQL user on {self.host_config.ssh_config}...[/blue]")

            # Check if user already has credentials configured
            if hasattr(self.host_config, 'password') and self.host_config.password:
                # Use existing credentials from config
                username = self.host_config.superuser
                password = self.host_config.password
                console.print(f"[blue]   Using configured credentials for user: {username}[/blue]")
            else:
                # Prompt for new credentials
                console.print("[yellow]🔐 PostgreSQL needs a user account for sync operations[/yellow]")
                username = Prompt.ask("PostgreSQL username", default="pgsqlmgr")
                password = Prompt.ask("PostgreSQL password", password=True)

            # Create PostgreSQL user
            create_user_cmd = f"sudo -u postgres psql -c \"CREATE USER {username} WITH PASSWORD '{password}' CREATEDB CREATEROLE;\""

            result = subprocess.run(
                ["ssh", self.host_config.ssh_config, create_user_cmd],
                capture_output=True,
                text=True,
                timeout=60
            )

            # Check if user creation succeeded or user already exists
            if result.returncode == 0 or "already exists" in result.stderr:
                console.print(f"[green]✅ PostgreSQL user '{username}' ready[/green]")

                # Update host config with credentials if not already set
                if not hasattr(self.host_config, 'password') or not self.host_config.password:
                    self.host_config.superuser = username
                    self.host_config.password = password
                    console.print("[blue]💡 Credentials saved for this session[/blue]")

                return True, f"User '{username}' configured successfully"
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
