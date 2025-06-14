"""Tests for database synchronization functionality."""

import pytest
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from pgsqlmgr.sync import DatabaseSyncManager
from pgsqlmgr.config import LocalHost, SSHHost


class TestDatabaseSyncManager:
    """Test database synchronization management."""
    
    def test_init_local_to_local(self):
        """Test sync manager initialization for local to local sync."""
        source_config = LocalHost(user="postgres")
        dest_config = LocalHost(user="postgres", port=5433)
        
        sync_manager = DatabaseSyncManager(source_config, dest_config)
        
        assert sync_manager.source_config == source_config
        assert sync_manager.destination_config == dest_config
        assert sync_manager.source_ssh is None
        assert sync_manager.dest_ssh is None
    
    def test_init_local_to_ssh(self):
        """Test sync manager initialization for local to SSH sync."""
        source_config = LocalHost(user="postgres")
        dest_config = SSHHost(ssh_config="test", user="postgres")
        
        sync_manager = DatabaseSyncManager(source_config, dest_config)
        
        assert sync_manager.source_config == source_config
        assert sync_manager.destination_config == dest_config
        assert sync_manager.source_ssh is None
        assert sync_manager.dest_ssh is not None
    
    def test_init_ssh_to_local(self):
        """Test sync manager initialization for SSH to local sync."""
        source_config = SSHHost(ssh_config="test", user="postgres")
        dest_config = LocalHost(user="postgres")
        
        sync_manager = DatabaseSyncManager(source_config, dest_config)
        
        assert sync_manager.source_config == source_config
        assert sync_manager.destination_config == dest_config
        assert sync_manager.source_ssh is not None
        assert sync_manager.dest_ssh is None
    
    def test_get_host_description(self):
        """Test host description generation."""
        local_config = LocalHost(user="postgres")
        ssh_config = SSHHost(ssh_config="test", user="postgres")
        
        sync_manager = DatabaseSyncManager(local_config, ssh_config)
        
        local_desc = sync_manager._get_host_description(local_config)
        ssh_desc = sync_manager._get_host_description(ssh_config)
        
        assert "local (localhost:5432)" in local_desc
        assert "test (localhost:5432)" in ssh_desc
    
    @patch('subprocess.run')
    @patch('tempfile.mkdtemp')
    def test_create_local_dump_success(self, mock_mkdtemp, mock_run):
        """Test successful local database dump creation."""
        # Mock temporary directory
        mock_mkdtemp.return_value = "/tmp/test"
        
        # Mock successful pg_dump
        mock_run.return_value = Mock(returncode=0)
        
        source_config = LocalHost(user="postgres", password="test123")
        dest_config = LocalHost(user="postgres", port=5433)
        sync_manager = DatabaseSyncManager(source_config, dest_config)
        
        dump_file = Path("/tmp/test/testdb.sql")
        success, message = sync_manager._create_local_dump("testdb", dump_file)
        
        assert success is True
        assert "Database dump created" in message
        
        # Verify pg_dump was called with correct arguments
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        
        assert "pg_dump" in cmd
        assert "--host" in cmd
        assert "localhost" in cmd
        assert "--username" in cmd
        assert "postgres" in cmd
        assert "testdb" in cmd
    
    @patch('subprocess.run')
    def test_create_local_dump_failure(self, mock_run):
        """Test local database dump creation failure."""
        # Mock failed pg_dump
        mock_run.return_value = Mock(returncode=1, stderr="Database not found")
        
        source_config = LocalHost(user="postgres")
        dest_config = LocalHost(user="postgres", port=5433)
        sync_manager = DatabaseSyncManager(source_config, dest_config)
        
        dump_file = Path("/tmp/testdb.sql")
        success, message = sync_manager._create_local_dump("testdb", dump_file)
        
        assert success is False
        assert "pg_dump failed" in message
        assert "Database not found" in message
    
    @patch('subprocess.run')
    def test_create_local_dump_timeout(self, mock_run):
        """Test local database dump creation timeout."""
        # Mock timeout
        mock_run.side_effect = subprocess.TimeoutExpired(["pg_dump"], 300)
        
        source_config = LocalHost(user="postgres")
        dest_config = LocalHost(user="postgres", port=5433)
        sync_manager = DatabaseSyncManager(source_config, dest_config)
        
        dump_file = Path("/tmp/testdb.sql")
        success, message = sync_manager._create_local_dump("testdb", dump_file)
        
        assert success is False
        assert "timed out" in message.lower()
    
    @patch('subprocess.run')
    def test_create_local_dump_not_found(self, mock_run):
        """Test local database dump when pg_dump not found."""
        # Mock FileNotFoundError
        mock_run.side_effect = FileNotFoundError()
        
        source_config = LocalHost(user="postgres")
        dest_config = LocalHost(user="postgres", port=5433)
        sync_manager = DatabaseSyncManager(source_config, dest_config)
        
        dump_file = Path("/tmp/testdb.sql")
        success, message = sync_manager._create_local_dump("testdb", dump_file)
        
        assert success is False
        assert "not found" in message.lower()
    
    def test_create_ssh_dump_placeholder(self):
        """Test SSH database dump creation (placeholder)."""
        source_config = SSHHost(ssh_config="test", user="postgres")
        dest_config = LocalHost(user="postgres")
        sync_manager = DatabaseSyncManager(source_config, dest_config)
        
        dump_file = Path("/tmp/testdb.sql")
        success, message = sync_manager._create_ssh_dump("testdb", dump_file)
        
        assert success is False
        assert "not yet implemented" in message
        assert dump_file.exists()  # Placeholder file should be created
    
    def test_transfer_dump_file_local_to_local(self):
        """Test dump file transfer for local to local (no transfer needed)."""
        source_config = LocalHost(user="postgres")
        dest_config = LocalHost(user="postgres", port=5433)
        sync_manager = DatabaseSyncManager(source_config, dest_config)
        
        dump_file = Path("/tmp/testdb.sql")
        success, message = sync_manager._transfer_dump_file(dump_file)
        
        assert success is True
        assert "No file transfer needed" in message
    
    def test_transfer_dump_file_ssh_placeholder(self):
        """Test dump file transfer with SSH (placeholder)."""
        source_config = SSHHost(ssh_config="test", user="postgres")
        dest_config = LocalHost(user="postgres")
        sync_manager = DatabaseSyncManager(source_config, dest_config)
        
        dump_file = Path("/tmp/testdb.sql")
        success, message = sync_manager._transfer_dump_file(dump_file)
        
        assert success is False
        assert "not yet implemented" in message
    
    @patch('subprocess.run')
    def test_restore_local_dump_success(self, mock_run):
        """Test successful local database restore."""
        # Mock successful createdb and psql
        mock_run.side_effect = [
            Mock(returncode=0),  # createdb
            Mock(returncode=0)   # psql
        ]
        
        source_config = LocalHost(user="postgres")
        dest_config = LocalHost(user="postgres", port=5433, password="test123")
        sync_manager = DatabaseSyncManager(source_config, dest_config)
        
        # Create a temporary dump file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            f.write("-- Test dump file")
            dump_file = Path(f.name)
        
        try:
            success, message = sync_manager._restore_local_dump("testdb", dump_file, False)
            
            assert success is True
            assert "restored successfully" in message
            
            # Verify createdb and psql were called
            assert mock_run.call_count == 2
            
        finally:
            dump_file.unlink()
    
    @patch('subprocess.run')
    def test_restore_local_dump_with_drop(self, mock_run):
        """Test local database restore with drop existing."""
        # Mock successful dropdb, createdb, and psql
        mock_run.side_effect = [
            Mock(returncode=0),  # dropdb
            Mock(returncode=0),  # createdb
            Mock(returncode=0)   # psql
        ]
        
        source_config = LocalHost(user="postgres")
        dest_config = LocalHost(user="postgres", port=5433)
        sync_manager = DatabaseSyncManager(source_config, dest_config)
        
        # Create a temporary dump file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            f.write("-- Test dump file")
            dump_file = Path(f.name)
        
        try:
            success, message = sync_manager._restore_local_dump("testdb", dump_file, True)
            
            assert success is True
            assert "restored successfully" in message
            
            # Verify dropdb, createdb, and psql were called
            assert mock_run.call_count == 3
            
        finally:
            dump_file.unlink()
    
    @patch('subprocess.run')
    def test_restore_local_dump_createdb_failure(self, mock_run):
        """Test local database restore when createdb fails."""
        # Mock failed createdb
        mock_run.return_value = Mock(returncode=1, stderr="Permission denied")
        
        source_config = LocalHost(user="postgres")
        dest_config = LocalHost(user="postgres", port=5433)
        sync_manager = DatabaseSyncManager(source_config, dest_config)
        
        dump_file = Path("/tmp/testdb.sql")
        success, message = sync_manager._restore_local_dump("testdb", dump_file, False)
        
        assert success is False
        assert "Failed to create database" in message
    
    @patch('subprocess.run')
    def test_restore_local_dump_psql_failure(self, mock_run):
        """Test local database restore when psql fails."""
        # Mock successful createdb but failed psql
        mock_run.side_effect = [
            Mock(returncode=0),  # createdb
            Mock(returncode=1, stderr="Syntax error")  # psql
        ]
        
        source_config = LocalHost(user="postgres")
        dest_config = LocalHost(user="postgres", port=5433)
        sync_manager = DatabaseSyncManager(source_config, dest_config)
        
        # Create a temporary dump file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            f.write("-- Test dump file")
            dump_file = Path(f.name)
        
        try:
            success, message = sync_manager._restore_local_dump("testdb", dump_file, False)
            
            assert success is False
            assert "psql restore failed" in message
            
        finally:
            dump_file.unlink()
    
    def test_restore_ssh_dump_placeholder(self):
        """Test SSH database restore (placeholder)."""
        source_config = LocalHost(user="postgres")
        dest_config = SSHHost(ssh_config="test", user="postgres")
        sync_manager = DatabaseSyncManager(source_config, dest_config)
        
        dump_file = Path("/tmp/testdb.sql")
        success, message = sync_manager._restore_ssh_dump("testdb", dump_file, False)
        
        assert success is False
        assert "not yet implemented" in message
    
    @patch('subprocess.run')
    def test_list_local_databases_success(self, mock_run):
        """Test successful local database listing."""
        # Mock successful psql --list
        mock_run.return_value = Mock(
            returncode=0,
            stdout="testdb|owner|UTF8|\nappdb|owner|UTF8|\ntemplate0|postgres|UTF8|\npostgres|postgres|UTF8|\n"
        )
        
        host_config = LocalHost(user="postgres", password="test123")
        sync_manager = DatabaseSyncManager(host_config, host_config)
        
        success, databases, error_msg = sync_manager._list_local_databases(host_config)
        
        assert success is True
        assert "testdb" in databases
        assert "appdb" in databases
        assert "template0" not in databases  # System databases should be filtered
        assert "postgres" not in databases
        assert error_msg == ""
    
    @patch('subprocess.run')
    def test_list_local_databases_failure(self, mock_run):
        """Test local database listing failure."""
        # Mock failed psql --list
        mock_run.return_value = Mock(returncode=1, stderr="Connection failed")
        
        host_config = LocalHost(user="postgres")
        sync_manager = DatabaseSyncManager(host_config, host_config)
        
        success, databases, error_msg = sync_manager._list_local_databases(host_config)
        
        assert success is False
        assert databases == []
        assert "Connection failed" in error_msg
    
    def test_list_ssh_databases_placeholder(self):
        """Test SSH database listing (placeholder)."""
        host_config = SSHHost(ssh_config="test", user="postgres")
        sync_manager = DatabaseSyncManager(host_config, host_config)
        
        success, databases, error_msg = sync_manager._list_ssh_databases(host_config)
        
        assert success is False
        assert databases == []
        assert "not yet implemented" in error_msg
    
    @patch('shutil.rmtree')
    def test_cleanup_success(self, mock_rmtree):
        """Test successful cleanup of temporary directory."""
        source_config = LocalHost(user="postgres")
        dest_config = LocalHost(user="postgres", port=5433)
        sync_manager = DatabaseSyncManager(source_config, dest_config)
        
        sync_manager.temp_dir = "/tmp/test_cleanup"
        
        # Mock Path.exists to return True
        with patch.object(Path, 'exists', return_value=True):
            sync_manager._cleanup()
        
        mock_rmtree.assert_called_once_with("/tmp/test_cleanup")
    
    @patch('shutil.rmtree')
    def test_cleanup_failure(self, mock_rmtree):
        """Test cleanup failure handling."""
        # Mock rmtree to raise exception
        mock_rmtree.side_effect = PermissionError("Permission denied")
        
        source_config = LocalHost(user="postgres")
        dest_config = LocalHost(user="postgres", port=5433)
        sync_manager = DatabaseSyncManager(source_config, dest_config)
        
        sync_manager.temp_dir = "/tmp/test_cleanup"
        
        # Mock Path.exists to return True
        with patch.object(Path, 'exists', return_value=True):
            # This should not raise an exception
            sync_manager._cleanup()


# Integration tests will be added when sync functionality is implemented
class TestSyncIntegration:
    """Integration tests for sync functionality (future implementation)."""
    
    def test_full_sync_local_to_local(self):
        """Test full sync between local instances (placeholder)."""
        # This test will be implemented when sync functionality is ready
        pytest.skip("Sync integration tests will be implemented in Milestone 3")
    
    def test_full_sync_local_to_ssh(self):
        """Test full sync from local to SSH instance (placeholder)."""
        # This test will be implemented when sync functionality is ready
        pytest.skip("Sync integration tests will be implemented in Milestone 3")
    
    def test_full_sync_ssh_to_local(self):
        """Test full sync from SSH to local instance (placeholder)."""
        # This test will be implemented when sync functionality is ready
        pytest.skip("Sync integration tests will be implemented in Milestone 3")
    
    def test_full_sync_ssh_to_ssh(self):
        """Test full sync between SSH instances (placeholder)."""
        # This test will be implemented when sync functionality is ready
        pytest.skip("Sync integration tests will be implemented in Milestone 3")
    
    def test_sync_with_large_database(self):
        """Test sync with large database (placeholder)."""
        # This test will be implemented when sync functionality is ready
        pytest.skip("Sync integration tests will be implemented in Milestone 3")
    
    def test_sync_error_handling(self):
        """Test sync error handling (placeholder)."""
        # This test will be implemented when sync functionality is ready
        pytest.skip("Sync integration tests will be implemented in Milestone 3")
    
    def test_sync_verification(self):
        """Test sync verification (placeholder)."""
        # This test will be implemented when sync functionality is ready
        pytest.skip("Sync integration tests will be implemented in Milestone 3") 