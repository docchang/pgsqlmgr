"""Tests for database operations and PostgreSQL installation."""

import pytest
import platform
from unittest.mock import Mock, patch, MagicMock
import subprocess

from pgsqlmgr.db import PostgreSQLManager, INSTALL_COMMANDS
from pgsqlmgr.config import LocalHost, SSHHost


class TestPostgreSQLManager:
    """Test PostgreSQL installation management."""
    
    def test_init_local_host(self):
        """Test PostgreSQL manager initialization with local host."""
        local_config = LocalHost(user="postgres")
        manager = PostgreSQLManager(local_config)
        
        assert manager.config == local_config
        assert manager.ssh_manager is None
    
    def test_init_ssh_host(self):
        """Test PostgreSQL manager initialization with SSH host."""
        ssh_config = SSHHost(ssh_config="test", user="postgres")
        manager = PostgreSQLManager(ssh_config)
        
        assert manager.config == ssh_config
        assert manager.ssh_manager is not None
    
    @patch('subprocess.run')
    def test_check_local_installation_success(self, mock_run):
        """Test successful local PostgreSQL installation check."""
        # Mock successful psql --version command
        mock_run.return_value = Mock(
            returncode=0,
            stdout="psql (PostgreSQL) 15.4"
        )
        
        local_config = LocalHost(user="postgres")
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
        
        local_config = LocalHost(user="postgres")
        manager = PostgreSQLManager(local_config)
        
        is_installed, message, version = manager.check_postgresql_installation()
        
        assert is_installed is False
        assert "not installed" in message.lower()
        assert version is None
    
    @patch('subprocess.run')
    def test_check_local_installation_timeout(self, mock_run):
        """Test local PostgreSQL installation check timeout."""
        # Mock timeout
        mock_run.side_effect = subprocess.TimeoutExpired(["psql", "--version"], 10)
        
        local_config = LocalHost(user="postgres")
        manager = PostgreSQLManager(local_config)
        
        is_installed, message, version = manager.check_postgresql_installation()
        
        assert is_installed is False
        assert "timed out" in message.lower()
        assert version is None
    
    def test_check_ssh_installation_placeholder(self):
        """Test SSH PostgreSQL installation check (placeholder)."""
        ssh_config = SSHHost(ssh_config="test", user="postgres")
        manager = PostgreSQLManager(ssh_config)
        
        is_installed, message, version = manager._check_ssh_installation()
        
        assert is_installed is False
        assert "not yet implemented" in message
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
        
        local_config = LocalHost(user="postgres")
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
        
        local_config = LocalHost(user="postgres")
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
        
        local_config = LocalHost(user="postgres")
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
        
        local_config = LocalHost(user="postgres")
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
        
        local_config = LocalHost(user="postgres")
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
        
        local_config = LocalHost(user="postgres")
        manager = PostgreSQLManager(local_config)
        
        success, message = manager.install_postgresql()
        
        assert success is False
        assert "Installation failed" in message
    
    @patch('platform.system')
    def test_install_linux_placeholder(self, mock_system):
        """Test PostgreSQL installation on Linux (placeholder)."""
        mock_system.return_value = "Linux"
        
        local_config = LocalHost(user="postgres")
        manager = PostgreSQLManager(local_config)
        
        success, message = manager.install_postgresql()
        
        assert success is False
        assert "not yet implemented" in message
    
    @patch('platform.system')
    def test_install_unsupported_platform(self, mock_system):
        """Test PostgreSQL installation on unsupported platform."""
        mock_system.return_value = "Windows"
        
        local_config = LocalHost(user="postgres")
        manager = PostgreSQLManager(local_config)
        
        success, message = manager.install_postgresql()
        
        assert success is False
        assert "not supported" in message
    
    def test_install_ssh_placeholder(self):
        """Test SSH PostgreSQL installation (placeholder)."""
        ssh_config = SSHHost(ssh_config="test", user="postgres")
        manager = PostgreSQLManager(ssh_config)
        
        success, message = manager.install_postgresql()
        
        assert success is False
        assert "not yet implemented" in message
    
    @patch('platform.system')
    @patch('subprocess.run')
    def test_start_local_service_macos_success(self, mock_run, mock_system):
        """Test starting PostgreSQL service on macOS."""
        mock_system.return_value = "Darwin"
        mock_run.return_value = Mock(returncode=0)
        
        local_config = LocalHost(user="postgres")
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
        
        local_config = LocalHost(user="postgres")
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
        
        local_config = LocalHost(user="postgres")
        manager = PostgreSQLManager(local_config)
        
        success, message = manager.start_service()
        
        assert success is False
        assert "Failed to start service" in message
    
    def test_start_ssh_service_placeholder(self):
        """Test starting PostgreSQL service via SSH (placeholder)."""
        ssh_config = SSHHost(ssh_config="test", user="postgres")
        manager = PostgreSQLManager(ssh_config)
        
        success, message = manager.start_service()
        
        assert success is False
        assert "not yet implemented" in message


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


# DatabaseConnection tests will be added when needed for database operations 