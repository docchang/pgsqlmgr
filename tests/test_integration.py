"""Integration tests for PostgreSQL Manager."""

import os
import subprocess
from unittest.mock import patch

import pytest

from src.pgsqlmgr.config import LocalHost, SSHHost
from src.pgsqlmgr.sync import DatabaseSyncManager


class TestRealWorldIntegration:
    """Real-world integration tests that require actual PostgreSQL setup."""

    def setup_method(self):
        """Set up test environment."""
        # Use environment variables or defaults for testing
        self.local_config = LocalHost(
            host=os.getenv("PGHOST", "localhost"),
            port=int(os.getenv("PGPORT", "5432")),
            superuser=os.getenv("PGUSER", "postgres")
        )
        self.test_db_name = "pgsqlmgr_integration_test"

        # Skip tests if PostgreSQL is not accessible
        if not self._check_postgresql_accessible():
            pytest.skip("PostgreSQL not accessible for integration testing")

        # Clean up any existing test database
        self._cleanup_test_database()

    def test_database_creation_and_verification(self):
        """Test creating a database and verifying its contents."""
        # Create test database with data
        assert self._create_test_database(), "Failed to create test database"

        # Verify data exists
        data = self._get_database_data()
        assert len(data) == 3, f"Expected 3 records, got {len(data)}"

        expected_names = {"John Doe", "Jane Smith", "Bob Wilson"}
        actual_names = {row['name'] for row in data}
        assert actual_names == expected_names, f"Expected {expected_names}, got {actual_names}"

        # Clean up
        self._cleanup_test_database()

    def test_data_modification_and_sync_verification(self):
        """Test modifying data and verifying changes."""
        # Create test database
        assert self._create_test_database(), "Failed to create test database"

        # Get initial data
        initial_data = self._get_database_data()
        assert len(initial_data) == 3, "Initial data should have 3 records"

        # Delete one record
        assert self._delete_test_record("John Doe"), "Failed to delete record"

        # Verify deletion
        after_delete = self._get_database_data()
        assert len(after_delete) == 2, "Should have 2 records after deletion"

        # Add new record
        assert self._add_test_record("Alice Cooper", "alice@example.com"), "Failed to add record"

        # Verify addition
        final_data = self._get_database_data()
        assert len(final_data) == 3, "Should have 3 records after addition"

        # Verify Alice is in the data
        names = {row['name'] for row in final_data}
        assert "Alice Cooper" in names, "Alice Cooper should be in the data"
        assert "John Doe" not in names, "John Doe should not be in the data"

        # Clean up
        self._cleanup_test_database()

    @patch('src.pgsqlmgr.sync.Confirm.ask')
    @patch('subprocess.run')
    def test_postgresql_availability_check_missing_installation(self, mock_run, mock_confirm):
        """Test PostgreSQL availability check when installation is missing."""
        # Mock subprocess to simulate missing PostgreSQL
        mock_run.side_effect = FileNotFoundError("psql: command not found")
        mock_confirm.return_value = False  # User chooses not to install

        local_config = LocalHost(superuser="postgres")
        ssh_config = LocalHost(superuser="postgres")  # Use LocalHost for testing

        sync_manager = DatabaseSyncManager(local_config, ssh_config)

        success, message = sync_manager.sync_database("test_db", auto_install=False)
        assert not success
        assert "not found" in message.lower() or "not installed" in message.lower()

    @patch('src.pgsqlmgr.sync.Confirm.ask')
    @patch('subprocess.run')
    def test_postgresql_availability_check_service_not_running(self, mock_run, mock_confirm):
        """Test PostgreSQL availability check when service is not running."""
        mock_confirm.return_value = False  # User chooses not to start service

        def mock_subprocess(cmd, *args, **kwargs):
            """Mock subprocess responses."""
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else cmd

            if 'psql --version' in cmd_str:
                # PostgreSQL is installed
                return type('MockResult', (), {'returncode': 0, 'stdout': 'psql (PostgreSQL) 14.0'})()
            elif 'psql' in cmd_str and '--list' in cmd_str:
                # Connection fails - service not running
                return type('MockResult', (), {
                    'returncode': 2,
                    'stderr': 'psql: error: connection to server on socket failed'
                })()
            else:
                return type('MockResult', (), {'returncode': 0, 'stdout': '', 'stderr': ''})()

        mock_run.side_effect = mock_subprocess

        local_config = LocalHost(superuser="postgres")
        ssh_config = LocalHost(superuser="postgres")

        sync_manager = DatabaseSyncManager(local_config, ssh_config)

        success, message = sync_manager.sync_database("test_db", auto_install=False)
        assert not success
        assert "connection" in message.lower() or "service" in message.lower()

    @patch('pgsqlmgr.sync.Confirm.ask')
    @patch('subprocess.run')
    def test_postgresql_auto_installation_workflow(self, mock_run, mock_confirm):
        """Test PostgreSQL auto-installation workflow."""
        mock_confirm.return_value = True  # User agrees to install

        def mock_subprocess(cmd, *args, **kwargs):
            """Mock subprocess for installation workflow."""
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else cmd

            if 'psql --version' in cmd_str:
                # First call: not installed, second call: installed
                if not hasattr(mock_subprocess, 'version_called'):
                    mock_subprocess.version_called = True
                    raise FileNotFoundError("psql: command not found")
                else:
                    return type('MockResult', (), {'returncode': 0, 'stdout': 'psql (PostgreSQL) 14.0'})()
            elif 'brew install' in cmd_str or 'apt-get install' in cmd_str:
                # Installation succeeds
                return type('MockResult', (), {'returncode': 0, 'stdout': 'Installation successful'})()
            else:
                return type('MockResult', (), {'returncode': 0, 'stdout': '', 'stderr': ''})()

        mock_run.side_effect = mock_subprocess

        local_config = LocalHost(superuser="postgres")
        ssh_config = LocalHost(superuser="postgres")

        sync_manager = DatabaseSyncManager(local_config, ssh_config)

        # This should trigger auto-installation
        success, message = sync_manager._check_postgresql_availability(
            local_config, "source", auto_install=True
        )

        # Should succeed after installation
        assert success or "install" in message.lower()

    def test_sync_error_handling_invalid_database(self):
        """Test sync error handling with invalid database name."""
        local_config = LocalHost(superuser="postgres")
        ssh_config = LocalHost(superuser="postgres")

        sync_manager = DatabaseSyncManager(local_config, ssh_config)

        # Try to sync a non-existent database
        success, message = sync_manager.sync_database("nonexistent_database_12345")
        assert not success
        assert "not found" in message.lower() or "does not exist" in message.lower()

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
                env=os.environ
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
                    env=os.environ
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
                env=os.environ
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
                env=os.environ
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
                env=os.environ
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
                env=os.environ
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
                env=os.environ
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

        local_config = LocalHost(superuser=os.getenv("USER", "postgres"))
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
        local_config = LocalHost(superuser=os.getenv("USER", "postgres"))

        sync_manager = DatabaseSyncManager(ssh_config, local_config)

        success, message = sync_manager.sync_database(
            database_name="pgsqlmgr_test",
            auto_install=True,
            drop_existing=True
        )

        assert success, f"SSH to local sync should succeed: {message}"

    @pytest.mark.skip(reason="Requires actual SSH setup - run manually for testing")
    def test_bidirectional_sync_data_consistency(self):
        """Test bidirectional sync maintains data consistency."""
        # This would test syncing data back and forth between hosts
        # and ensuring consistency is maintained

        # local_config = LocalHost(superuser=os.getenv("USER", "postgres"))
        # ssh_config = SSHHost(ssh_config="genesis", superuser="postgres")

        # Test local -> SSH -> local roundtrip
        # sync_manager_to_ssh = DatabaseSyncManager(local_config, ssh_config)
        # sync_manager_to_local = DatabaseSyncManager(ssh_config, local_config)

        # This would involve creating test data, syncing it, modifying it,
        # syncing back, and verifying consistency
        pass
