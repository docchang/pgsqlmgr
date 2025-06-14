"""Tests for database operations and PostgreSQL installation."""

import subprocess
from unittest.mock import Mock, patch

import pytest

from pgsqlmgr.config import LocalHost, SSHHost
from pgsqlmgr.db import INSTALL_COMMANDS, DatabaseManager, PostgreSQLManager


class TestPostgreSQLManager:
    """Test PostgreSQL installation management."""

    def test_init_local_host(self):
        """Test PostgreSQL manager initialization with local host."""
        local_config = LocalHost(superuser="postgres")
        manager = PostgreSQLManager(local_config)

        assert manager.host_config == local_config
        assert manager.is_local
        assert not manager.is_ssh
        assert manager.ssh_manager is None

    def test_init_ssh_host(self):
        """Test PostgreSQL manager initialization with SSH host."""
        ssh_config = SSHHost(ssh_config="test", superuser="postgres")
        manager = PostgreSQLManager(ssh_config)

        assert manager.host_config == ssh_config
        assert not manager.is_local
        assert manager.is_ssh
        assert manager.ssh_manager is not None

    @patch('subprocess.run')
    def test_check_local_installation_success(self, mock_run):
        """Test successful local PostgreSQL installation check."""
        # Mock successful psql --version command
        mock_run.return_value = Mock(
            returncode=0,
            stdout="psql (PostgreSQL) 15.4"
        )

        local_config = LocalHost(superuser="postgres")
        manager = PostgreSQLManager(local_config)

        is_installed, message, version = manager.check_postgresql_installation()

        assert is_installed is True
        assert "PostgreSQL is installed locally" in message
        assert version == "psql (PostgreSQL) 15.4"
        mock_run.assert_called_once_with(
            ["psql", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )

    @patch('subprocess.run')
    def test_check_local_installation_not_found(self, mock_run):
        """Test local PostgreSQL installation check when not installed."""
        # Mock FileNotFoundError (psql command not found)
        mock_run.side_effect = FileNotFoundError()

        local_config = LocalHost(superuser="postgres")
        manager = PostgreSQLManager(local_config)

        is_installed, message, version = manager.check_postgresql_installation()

        assert is_installed is False
        assert "not installed" in message
        assert version is None

    @patch('subprocess.run')
    def test_check_local_installation_timeout(self, mock_run):
        """Test local PostgreSQL installation check timeout."""
        # Mock timeout
        mock_run.side_effect = subprocess.TimeoutExpired(["psql", "--version"], 10)

        local_config = LocalHost(superuser="postgres")
        manager = PostgreSQLManager(local_config)

        is_installed, message, version = manager.check_postgresql_installation()

        assert is_installed is False
        assert "timed out" in message.lower()
        assert version is None

    @patch('subprocess.run')
    def test_check_ssh_installation_not_found(self, mock_run):
        """Test SSH PostgreSQL installation check when not found."""
        mock_run.return_value = Mock(returncode=1, stderr="command not found")

        ssh_config = SSHHost(ssh_config="test", superuser="postgres")
        manager = PostgreSQLManager(ssh_config)

        is_installed, message, version = manager._check_ssh_postgresql()

        assert is_installed is False
        assert "not installed" in message
        assert version is None

    @patch('platform.system')
    @patch('subprocess.run')
    def test_check_local_service_macos_running(self, mock_run, mock_system):
        """Test local service check on macOS when service is running."""
        mock_system.return_value = "Darwin"
        mock_run.return_value = Mock(
            returncode=0,
            stdout="postgresql@15 started"
        )

        local_config = LocalHost(superuser="postgres")
        manager = PostgreSQLManager(local_config)

        is_running, message = manager.check_service_status()

        assert is_running is True
        assert "running" in message.lower()

    @patch('platform.system')
    @patch('subprocess.run')
    def test_check_local_service_macos_not_running(self, mock_run, mock_system):
        """Test local service check on macOS when service is not running."""
        mock_system.return_value = "Darwin"
        mock_run.return_value = Mock(
            returncode=0,
            stdout="postgresql@15 stopped"
        )

        local_config = LocalHost(superuser="postgres")
        manager = PostgreSQLManager(local_config)

        is_running, message = manager.check_service_status()

        assert is_running is False
        assert "not running" in message.lower()

    @patch('platform.system')
    @patch('subprocess.run')
    def test_check_local_service_linux_running(self, mock_run, mock_system):
        """Test local service check on Linux when service is running."""
        mock_system.return_value = "Linux"
        mock_run.return_value = Mock(
            returncode=0,
            stdout="active"
        )

        local_config = LocalHost(superuser="postgres")
        manager = PostgreSQLManager(local_config)

        is_running, message = manager.check_service_status()

        assert is_running is True
        assert "running" in message.lower()

    @patch('platform.system')
    @patch('subprocess.run')
    def test_install_macos_success(self, mock_run, mock_system):
        """Test successful PostgreSQL installation on macOS."""
        mock_system.return_value = "Darwin"

        # Mock brew --version check (success)
        # Mock brew install postgresql@15 (success)
        # Mock brew services start (success)
        mock_run.side_effect = [
            Mock(returncode=0),  # brew --version
            Mock(returncode=0, stderr=""),  # brew install
            Mock(returncode=0)   # brew services start
        ]

        local_config = LocalHost(superuser="postgres")
        manager = PostgreSQLManager(local_config)

        success, message = manager.install_postgresql()

        assert success is True
        assert "installed and started successfully" in message
        assert mock_run.call_count == 3

    @patch('platform.system')
    @patch('subprocess.run')
    def test_install_macos_no_homebrew(self, mock_run, mock_system):
        """Test PostgreSQL installation on macOS when Homebrew is not installed."""
        mock_system.return_value = "Darwin"

        # Mock brew --version check (failure)
        mock_run.return_value = Mock(returncode=1)

        local_config = LocalHost(superuser="postgres")
        manager = PostgreSQLManager(local_config)

        success, message = manager.install_postgresql()

        assert success is False
        assert "Homebrew not found" in message

    @patch('platform.system')
    @patch('subprocess.run')
    def test_install_macos_installation_failed(self, mock_run, mock_system):
        """Test PostgreSQL installation failure on macOS."""
        mock_system.return_value = "Darwin"

        # Mock brew --version (success), brew install (failure)
        mock_run.side_effect = [
            Mock(returncode=0),  # brew --version
            Mock(returncode=1, stderr="Installation failed")  # brew install
        ]

        local_config = LocalHost(superuser="postgres")
        manager = PostgreSQLManager(local_config)

        success, message = manager.install_postgresql()

        assert success is False
        assert "Installation failed" in message

    @patch('platform.system')
    def test_install_linux_placeholder(self, mock_system):
        """Test PostgreSQL installation on Linux (placeholder)."""
        mock_system.return_value = "Linux"

        local_config = LocalHost(superuser="postgres")
        manager = PostgreSQLManager(local_config)

        success, message = manager.install_postgresql()

        assert success is False
        assert "not yet implemented" in message

    @patch('platform.system')
    def test_install_unsupported_platform(self, mock_system):
        """Test PostgreSQL installation on unsupported platform."""
        mock_system.return_value = "Windows"

        local_config = LocalHost(superuser="postgres")
        manager = PostgreSQLManager(local_config)

        success, message = manager.install_postgresql()

        assert success is False
        assert "not supported" in message

    @patch('src.pgsqlmgr.db.PostgreSQLManager._detect_ssh_os')
    def test_install_ssh_os_detection_failed(self, mock_detect_os):
        """Test SSH PostgreSQL installation when OS detection fails."""
        mock_detect_os.return_value = None

        ssh_config = SSHHost(ssh_config="test", superuser="postgres")
        manager = PostgreSQLManager(ssh_config)

        success, message = manager.install_postgresql()

        assert success is False
        assert "Could not detect operating system" in message

    @patch('platform.system')
    @patch('subprocess.run')
    def test_start_local_service_macos_success(self, mock_run, mock_system):
        """Test starting PostgreSQL service on macOS."""
        mock_system.return_value = "Darwin"
        mock_run.return_value = Mock(returncode=0)

        local_config = LocalHost(superuser="postgres")
        manager = PostgreSQLManager(local_config)

        success, message = manager.start_service()

        assert success is True
        assert "started successfully" in message
        mock_run.assert_called_once_with(
            ["brew", "services", "start", "postgresql@15"],
            capture_output=True,
            text=True,
            timeout=30
        )

    @patch('platform.system')
    @patch('subprocess.run')
    def test_start_local_service_linux_success(self, mock_run, mock_system):
        """Test starting PostgreSQL service on Linux."""
        mock_system.return_value = "Linux"
        mock_run.return_value = Mock(returncode=0)

        local_config = LocalHost(superuser="postgres")
        manager = PostgreSQLManager(local_config)

        success, message = manager.start_service()

        assert success is True
        assert "started successfully" in message
        mock_run.assert_called_once_with(
            ["sudo", "systemctl", "start", "postgresql"],
            capture_output=True,
            text=True,
            timeout=30
        )

    @patch('platform.system')
    @patch('subprocess.run')
    def test_start_local_service_failed(self, mock_run, mock_system):
        """Test failed PostgreSQL service start."""
        mock_system.return_value = "Darwin"
        mock_run.return_value = Mock(returncode=1, stderr="Service start failed")

        local_config = LocalHost(superuser="postgres")
        manager = PostgreSQLManager(local_config)

        success, message = manager.start_service()

        assert success is False
        assert "Failed to start service" in message

    @patch('subprocess.run')
    def test_start_ssh_service_failed(self, mock_run):
        """Test starting PostgreSQL service via SSH failure."""
        mock_run.return_value = Mock(returncode=1, stderr="Service start failed")

        ssh_config = SSHHost(ssh_config="test", superuser="postgres")
        manager = PostgreSQLManager(ssh_config)

        success, message = manager.start_service()

        assert success is False
        assert "Failed to start PostgreSQL service" in message


class TestInstallCommands:
    """Test installation command constants."""

    def test_install_commands_structure(self):
        """Test that install commands have proper structure."""
        assert "Darwin" in INSTALL_COMMANDS
        assert "Linux" in INSTALL_COMMANDS

        # Check macOS commands
        darwin_cmds = INSTALL_COMMANDS["Darwin"]
        assert "check" in darwin_cmds
        assert "install" in darwin_cmds
        assert "service_start" in darwin_cmds

        # Check Linux commands
        linux_cmds = INSTALL_COMMANDS["Linux"]
        assert "ubuntu" in linux_cmds
        assert "centos" in linux_cmds


class TestDatabaseManager:
    """Test DatabaseManager class."""

    def test_init_local_host(self):
        """Test DatabaseManager initialization with local host."""
        config = LocalHost(superuser="postgres", password="test123")
        manager = DatabaseManager(config)

        assert manager.config == config
        assert manager._connection is None

    def test_init_ssh_host(self):
        """Test DatabaseManager initialization with SSH host."""
        config = SSHHost(ssh_config="test", superuser="postgres")
        manager = DatabaseManager(config)

        assert manager.config == config
        assert manager._connection is None

    # Database Deletion Tests

    def test_drop_database_empty_name(self):
        """Test drop_database with empty database name."""
        config = LocalHost(superuser="postgres")
        manager = DatabaseManager(config)

        with pytest.raises(ValueError, match="Database name cannot be empty"):
            manager.drop_database("")

        with pytest.raises(ValueError, match="Database name cannot be empty"):
            manager.drop_database("   ")

    def test_drop_database_system_database(self):
        """Test drop_database prevents deletion of system databases."""
        config = LocalHost(superuser="postgres")
        manager = DatabaseManager(config)

        system_dbs = ['postgres', 'template0', 'template1', 'POSTGRES', 'Template0']

        for db_name in system_dbs:
            success, message = manager.drop_database(db_name)
            assert success is False
            assert "Cannot delete system database" in message

    @patch('subprocess.run')
    def test_drop_local_database_success(self, mock_run):
        """Test successful local database deletion."""
        mock_run.return_value = Mock(returncode=0, stderr="")

        config = LocalHost(superuser="postgres", password="test123")
        manager = DatabaseManager(config)

        success, message = manager.drop_database("testdb")

        assert success is True
        assert "deleted successfully" in message

        # Verify dropdb command was called correctly
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "dropdb" in args
        assert "--if-exists" in args
        assert "testdb" in args
        assert "--host" in args
        assert "--port" in args
        assert "--username" in args

    @patch('subprocess.run')
    def test_drop_local_database_not_exists(self, mock_run):
        """Test local database deletion when database doesn't exist."""
        mock_run.return_value = Mock(returncode=1, stderr="database does not exist")

        config = LocalHost(superuser="postgres")
        manager = DatabaseManager(config)

        success, message = manager.drop_database("nonexistent")

        assert success is True
        assert "does not exist" in message

    @patch('subprocess.run')
    def test_drop_local_database_failure(self, mock_run):
        """Test local database deletion failure."""
        mock_run.return_value = Mock(returncode=1, stderr="Permission denied")

        config = LocalHost(superuser="postgres")
        manager = DatabaseManager(config)

        success, message = manager.drop_database("testdb")

        assert success is False
        assert "Permission denied" in message

    @patch('subprocess.run')
    def test_drop_local_database_timeout(self, mock_run):
        """Test local database deletion timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("dropdb", 60)

        config = LocalHost(superuser="postgres")
        manager = DatabaseManager(config)

        success, message = manager.drop_database("testdb")

        assert success is False
        assert "timed out" in message

    @patch('subprocess.run')
    def test_drop_local_database_command_not_found(self, mock_run):
        """Test local database deletion when dropdb command not found."""
        mock_run.side_effect = FileNotFoundError("dropdb not found")

        config = LocalHost(superuser="postgres")
        manager = DatabaseManager(config)

        success, message = manager.drop_database("testdb")

        assert success is False
        assert "dropdb command not found" in message

    @patch('subprocess.run')
    def test_drop_ssh_database_success(self, mock_run):
        """Test successful SSH database deletion."""
        mock_run.return_value = Mock(returncode=0, stderr="")

        config = SSHHost(ssh_config="test", superuser="postgres")
        manager = DatabaseManager(config)

        success, message = manager.drop_database("testdb")

        assert success is True
        assert "deleted successfully via SSH" in message

        # Verify SSH command was called correctly
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "ssh" in args
        assert "test" in args
        assert "dropdb" in args[2]
        assert "--if-exists" in args[2]

    @patch('subprocess.run')
    def test_drop_ssh_database_not_exists(self, mock_run):
        """Test SSH database deletion when database doesn't exist."""
        mock_run.return_value = Mock(returncode=1, stderr="database does not exist")

        config = SSHHost(ssh_config="test", superuser="postgres")
        manager = DatabaseManager(config)

        success, message = manager.drop_database("nonexistent")

        assert success is True
        assert "does not exist" in message

    @patch('subprocess.run')
    def test_drop_ssh_database_failure(self, mock_run):
        """Test SSH database deletion failure."""
        mock_run.return_value = Mock(returncode=1, stderr="Connection refused")

        config = SSHHost(ssh_config="test", superuser="postgres")
        manager = DatabaseManager(config)

        success, message = manager.drop_database("testdb")

        assert success is False
        assert "Connection refused" in message

    @patch('subprocess.run')
    def test_drop_ssh_database_timeout(self, mock_run):
        """Test SSH database deletion timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("ssh", 60)

        config = SSHHost(ssh_config="test", superuser="postgres")
        manager = DatabaseManager(config)

        success, message = manager.drop_database("testdb")

        assert success is False
        assert "timed out" in message

    # Database Info Tests

    @patch('subprocess.run')
    def test_get_local_database_info_success(self, mock_run):
        """Test successful local database info retrieval."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="testdb|postgres|UTF8|en_US.UTF-8|en_US.UTF-8|1024 MB|-1|2\n"
        )

        config = LocalHost(superuser="postgres", password="test123")
        manager = DatabaseManager(config)

        info = manager.get_database_info("testdb")

        assert info["exists"] is True
        assert info["name"] == "testdb"
        assert info["owner"] == "postgres"
        assert info["encoding"] == "UTF8"
        assert info["size"] == "1024 MB"
        assert info["active_connections"] == "2"

    @patch('subprocess.run')
    def test_get_local_database_info_not_found(self, mock_run):
        """Test local database info when database not found."""
        mock_run.return_value = Mock(returncode=0, stdout="")

        config = LocalHost(superuser="postgres")
        manager = DatabaseManager(config)

        info = manager.get_database_info("nonexistent")

        assert info["exists"] is False
        assert "error" in info

    @patch('subprocess.run')
    def test_get_local_database_info_failure(self, mock_run):
        """Test local database info failure."""
        mock_run.return_value = Mock(returncode=1, stderr="Connection failed")

        config = LocalHost(superuser="postgres")
        manager = DatabaseManager(config)

        info = manager.get_database_info("testdb")

        assert info["exists"] is False
        assert "error" in info

    @patch('subprocess.run')
    def test_get_ssh_database_info_success(self, mock_run):
        """Test successful SSH database info retrieval."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="testdb|postgres|UTF8|en_US.UTF-8|en_US.UTF-8|1024 MB|-1|2\n"
        )

        config = SSHHost(ssh_config="test", superuser="postgres")
        manager = DatabaseManager(config)

        info = manager.get_database_info("testdb")

        assert info["exists"] is True
        assert info["name"] == "testdb"
        assert info["owner"] == "postgres"
        assert info["encoding"] == "UTF8"
        assert info["size"] == "1024 MB"
        assert info["active_connections"] == "2"

    @patch('subprocess.run')
    def test_get_ssh_database_info_not_found(self, mock_run):
        """Test SSH database info when database not found."""
        mock_run.return_value = Mock(returncode=0, stdout="")

        config = SSHHost(ssh_config="test", superuser="postgres")
        manager = DatabaseManager(config)

        info = manager.get_database_info("nonexistent")

        assert info["exists"] is False
        assert "error" in info

    @patch('subprocess.run')
    def test_get_ssh_database_info_failure(self, mock_run):
        """Test SSH database info failure."""
        mock_run.return_value = Mock(returncode=1, stderr="SSH connection failed")

        config = SSHHost(ssh_config="test", superuser="postgres")
        manager = DatabaseManager(config)

        info = manager.get_database_info("testdb")

        assert info["exists"] is False
        assert "error" in info

    def test_unsupported_host_type_drop(self):
        """Test drop_database with unsupported host type."""
        # Create a mock config that's neither LocalHost nor SSHHost
        config = Mock()
        config.__class__.__name__ = "UnsupportedHost"

        manager = DatabaseManager(config)

        success, message = manager.drop_database("testdb")

        assert success is False
        assert "Unsupported host type" in message

    def test_unsupported_host_type_info(self):
        """Test get_database_info with unsupported host type."""
        # Create a mock config that's neither LocalHost nor SSHHost
        config = Mock()
        config.__class__.__name__ = "UnsupportedHost"

        manager = DatabaseManager(config)

        info = manager.get_database_info("testdb")

        assert "error" in info
        assert "Unsupported host type" in info["error"]

    def test_close_connection(self):
        """Test closing database connection."""
        config = LocalHost(superuser="postgres")
        manager = DatabaseManager(config)

        # Mock connection
        mock_connection = Mock()
        manager._connection = mock_connection

        manager.close()

        mock_connection.close.assert_called_once()
        assert manager._connection is None

    def test_close_no_connection(self):
        """Test closing when no connection exists."""
        config = LocalHost(superuser="postgres")
        manager = DatabaseManager(config)

        # Should not raise an error
        manager.close()
        assert manager._connection is None


# DatabaseConnection tests will be added when needed for database operations
