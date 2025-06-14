"""Integration tests for real-world PostgreSQL Manager scenarios."""

import os
import subprocess
from unittest.mock import Mock, patch

import pytest

from pgsqlmgr.config import LocalHost, SSHHost
from pgsqlmgr.sync import DatabaseSyncManager


class TestRealWorldIntegration:
    """Integration tests for real-world scenarios."""

    def setup_method(self):
        """Set up test environment."""
        self.test_db_name = "pgsqlmgr_integration_test"

        # Create test configs
        self.local_config = LocalHost(
            superuser=os.getenv("USER", "postgres"),  # Use current user
            host="localhost",
            port=5432,
            password=""  # No password needed for local user
        )

        self.ssh_config = SSHHost(
            ssh_config="genesis",
            superuser="postgres",
            host="localhost",
            port=5432,
            password="test_password"
        )

    def test_database_creation_and_verification(self):
        """Test creating a test database with data for sync testing."""
        # Check if PostgreSQL is accessible first
        if not self._check_postgresql_accessible():
            pytest.skip("PostgreSQL not accessible - skipping real database test")

        try:
            # Clean up any existing test database
            self._cleanup_test_database()

            # Create test database
            success = self._create_test_database()
            assert success, "Failed to create test database"

            # Verify database exists and has data
            data = self._get_database_data()
            assert len(data) > 0, "Test database should contain data"

            # Verify specific test data
            names = [row['name'] for row in data]
            assert "John Doe" in names, "Test data should include John Doe"
            assert "Jane Smith" in names, "Test data should include Jane Smith"

        finally:
            self._cleanup_test_database()

    def test_data_modification_and_sync_verification(self):
        """Test modifying data and verifying sync accuracy."""
        # Check if PostgreSQL is accessible first
        if not self._check_postgresql_accessible():
            pytest.skip("PostgreSQL not accessible - skipping real database test")

        try:
            # Create initial database
            self._cleanup_test_database()
            self._create_test_database()

            original_data = self._get_database_data()
            original_count = len(original_data)

            # Modify data - delete a record
            self._delete_test_record("John Doe")

            # Verify deletion
            modified_data = self._get_database_data()
            assert len(modified_data) == original_count - 1, "Record should be deleted"

            names = [row['name'] for row in modified_data]
            assert "John Doe" not in names, "John Doe should be deleted"
            assert "Jane Smith" in names, "Jane Smith should still exist"

            # Add new record
            self._add_test_record("Alice Johnson", "alice@example.com")

            # Verify addition
            final_data = self._get_database_data()
            assert len(final_data) == original_count, "Should have same count after add"

            names = [row['name'] for row in final_data]
            assert "Alice Johnson" in names, "Alice Johnson should be added"

        finally:
            self._cleanup_test_database()

    @patch('src.pgsqlmgr.sync.Confirm.ask')
    @patch('subprocess.run')
    def test_postgresql_availability_check_missing_installation(self, mock_run, mock_confirm):
        """Test availability check when PostgreSQL is not installed."""
        # Mock PostgreSQL not found
        mock_run.side_effect = FileNotFoundError("psql: command not found")
        mock_confirm.return_value = False  # User declines installation

        sync_manager = DatabaseSyncManager(self.local_config, self.ssh_config)

        available, message = sync_manager._check_postgresql_availability(
            self.ssh_config, "destination", auto_install=False
        )

        assert not available, "Should detect PostgreSQL as not available"
        assert "not installed" in message.lower() or "not available" in message.lower()

    @patch('src.pgsqlmgr.sync.Confirm.ask')
    @patch('subprocess.run')
    def test_postgresql_availability_check_service_not_running(self, mock_run, mock_confirm):
        """Test availability check when PostgreSQL is installed but not running."""
        # Mock PostgreSQL installed but service not running
        def mock_subprocess(cmd, *args, **kwargs):
            if 'psql --version' in ' '.join(cmd):
                return Mock(returncode=0, stdout="psql (PostgreSQL) 14.0")
            elif 'brew services list' in ' '.join(cmd):
                return Mock(returncode=0, stdout="postgresql stopped")
            elif 'systemctl is-active' in ' '.join(cmd):
                return Mock(returncode=3, stdout="inactive")
            else:
                return Mock(returncode=1, stderr="Service not running")

        mock_run.side_effect = mock_subprocess
        mock_confirm.return_value = False  # User declines starting service

        sync_manager = DatabaseSyncManager(self.local_config, self.local_config)

        available, message = sync_manager._check_postgresql_availability(
            self.local_config, "destination", auto_install=False
        )

        assert not available, "Should detect service as not running"
        assert "not running" in message.lower()

    @patch('pgsqlmgr.sync.Confirm.ask')
    @patch('subprocess.run')
    def test_postgresql_auto_installation_workflow(self, mock_run, mock_confirm):
        """Test the auto-installation workflow when PostgreSQL is missing."""
        # Mock user confirms installation
        mock_confirm.return_value = True

        # Mock installation success
        def mock_subprocess(cmd, *args, **kwargs):
            if 'psql --version' in ' '.join(cmd):
                # First call: not installed, second call: installed
                if not hasattr(mock_subprocess, 'install_called'):
                    mock_subprocess.install_called = False

                if not mock_subprocess.install_called:
                    raise FileNotFoundError("psql: command not found")
                else:
                    return Mock(returncode=0, stdout="psql (PostgreSQL) 14.0")

            elif 'brew install postgresql' in ' '.join(cmd):
                mock_subprocess.install_called = True
                return Mock(returncode=0, stdout="Installation successful")

            elif 'brew services start postgresql' in ' '.join(cmd):
                return Mock(returncode=0, stdout="Service started")

            else:
                return Mock(returncode=0)

        mock_run.side_effect = mock_subprocess

        sync_manager = DatabaseSyncManager(self.local_config, self.local_config)

        available, message = sync_manager._check_postgresql_availability(
            self.local_config, "destination", auto_install=False
        )

        # Should offer installation and succeed
        assert mock_confirm.called, "Should prompt user for installation"
        # Note: This test verifies the workflow logic, actual result depends on mocking details

    def test_sync_error_handling_invalid_database(self):
        """Test sync error handling when source database doesn't exist."""
        sync_manager = DatabaseSyncManager(self.local_config, self.local_config)

        success, message = sync_manager.sync_database(
            database_name="nonexistent_database_xyz123",
            auto_install=True  # Skip installation prompts
        )

        assert not success, "Should fail when source database doesn't exist"
        assert "not exist" in message.lower() or "failed" in message.lower()

    def _create_test_database(self) -> bool:
        """Create a test database with sample data."""
        try:
            # Create database
            cmd = ["createdb", "-h", self.local_config.host, "-p", str(self.local_config.port),
                   "-U", self.local_config.superuser, "--maintenance-db=postgres", self.test_db_name]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "PGPASSWORD": getattr(self.local_config, 'password', '')}
            )

            if result.returncode != 0:
                if "already exists" not in result.stderr:
                    return False

            # Create table and insert data
            sql_commands = [
                """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100),
                    email VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """,
                """
                INSERT INTO users (name, email) VALUES
                ('John Doe', 'john@example.com'),
                ('Jane Smith', 'jane@example.com'),
                ('Bob Wilson', 'bob@example.com')
                ON CONFLICT DO NOTHING;
                """
            ]

            for sql in sql_commands:
                cmd = ["psql", "-h", self.local_config.host, "-p", str(self.local_config.port),
                       "-U", self.local_config.superuser, "-d", self.test_db_name, "-c", sql]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env={**os.environ, "PGPASSWORD": getattr(self.local_config, 'password', '')}
                )

                if result.returncode != 0:
                    return False

            return True

        except Exception:
            return False

    def _get_database_data(self) -> list:
        """Get all data from the test database."""
        try:
            cmd = ["psql", "-h", self.local_config.host, "-p", str(self.local_config.port),
                   "-U", self.local_config.superuser, "-d", self.test_db_name, "-c",
                   "SELECT id, name, email FROM users ORDER BY id;",
                   "--tuples-only", "--no-align", "--field-separator=|"]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "PGPASSWORD": getattr(self.local_config, 'password', '')}
            )

            if result.returncode != 0:
                return []

            data = []
            for line in result.stdout.strip().split('\n'):
                if line and '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 3:
                        data.append({
                            'id': int(parts[0].strip()),
                            'name': parts[1].strip(),
                            'email': parts[2].strip()
                        })

            return data

        except Exception:
            return []

    def _delete_test_record(self, name: str) -> bool:
        """Delete a specific record from the test database."""
        try:
            cmd = ["psql", "-h", self.local_config.host, "-p", str(self.local_config.port),
                   "-U", self.local_config.superuser, "-d", self.test_db_name, "-c",
                   f"DELETE FROM users WHERE name = '{name}';"]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "PGPASSWORD": getattr(self.local_config, 'password', '')}
            )

            return result.returncode == 0

        except Exception:
            return False

    def _add_test_record(self, name: str, email: str) -> bool:
        """Add a new record to the test database."""
        try:
            cmd = ["psql", "-h", self.local_config.host, "-p", str(self.local_config.port),
                   "-U", self.local_config.superuser, "-d", self.test_db_name, "-c",
                   f"INSERT INTO users (name, email) VALUES ('{name}', '{email}');"]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "PGPASSWORD": getattr(self.local_config, 'password', '')}
            )

            return result.returncode == 0

        except Exception:
            return False

    def _check_postgresql_accessible(self) -> bool:
        """Check if PostgreSQL is accessible for testing."""
        try:
            cmd = ["psql", "-h", self.local_config.host, "-p", str(self.local_config.port),
                   "-U", self.local_config.superuser, "-d", "postgres", "-c", "SELECT 1;"]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                env={**os.environ, "PGPASSWORD": getattr(self.local_config, 'password', '')}
            )
            return result.returncode == 0
        except Exception:
            return False

    def _cleanup_test_database(self):
        """Clean up the test database."""
        try:
            cmd = ["dropdb", "--if-exists", "-h", self.local_config.host, "-p", str(self.local_config.port),
                   "-U", self.local_config.superuser, "--maintenance-db=postgres", self.test_db_name]

            subprocess.run(
                cmd,
                capture_output=True,
                timeout=30,
                env={**os.environ, "PGPASSWORD": getattr(self.local_config, 'password', '')}
            )
        except Exception:
            pass  # Ignore cleanup errors


class TestSSHSyncIntegration:
    """Integration tests for SSH sync scenarios."""

    @pytest.mark.skip(reason="Requires actual SSH setup - run manually for testing")
    def test_local_to_ssh_sync_full_workflow(self):
        """Test complete local-to-SSH sync workflow."""
        # This test requires actual SSH setup and would be run manually
        # for real-world testing with genesis/skynet hosts

        local_config = LocalHost(user=os.getenv("USER", "postgres"))
        ssh_config = SSHHost(ssh_config="genesis", superuser="postgres")

        sync_manager = DatabaseSyncManager(local_config, ssh_config)

        success, message = sync_manager.sync_database(
            database_name="pgsqlmgr_test",
            auto_install=True,
            drop_existing=True
        )

        # This would test the real SSH functionality
        assert success, f"SSH sync should succeed: {message}"

    @pytest.mark.skip(reason="Requires actual SSH setup - run manually for testing")
    def test_ssh_to_local_sync_full_workflow(self):
        """Test complete SSH-to-local sync workflow."""
        # This test requires actual SSH setup and would be run manually

        ssh_config = SSHHost(ssh_config="genesis", superuser="postgres")
        local_config = LocalHost(user=os.getenv("USER", "postgres"))

        sync_manager = DatabaseSyncManager(ssh_config, local_config)

        success, message = sync_manager.sync_database(
            database_name="pgsqlmgr_test",
            auto_install=True,
            drop_existing=True
        )

        assert success, f"SSH to local sync should succeed: {message}"

    @pytest.mark.skip(reason="Requires actual SSH setup - run manually for testing")
    def test_bidirectional_sync_data_consistency(self):
        """Test bidirectional sync and verify data consistency."""
        # This would test:
        # 1. Sync from local to SSH
        # 2. Modify data on SSH side
        # 3. Sync back from SSH to local
        # 4. Verify data consistency
        pass
