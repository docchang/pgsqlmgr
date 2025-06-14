"""Tests for PostgreSQL listing functionality."""

from unittest.mock import Mock, patch

import pytest

from src.pgsqlmgr.config import HostType, LocalHost, SSHHost
from src.pgsqlmgr.listing import (
    PostgreSQLLister,
    display_databases,
    display_table_preview,
    display_tables,
    display_users,
)


@pytest.fixture
def local_host_config():
    """Create a local host configuration for testing."""
    return LocalHost(
        type=HostType.LOCAL,
        host="localhost",
        port=5432,
        superuser="postgres",
        password="testpass",
        database="postgres",
        description="Test local host"
    )


@pytest.fixture
def ssh_host_config():
    """Create an SSH host configuration for testing."""
    return SSHHost(
        type=HostType.SSH,
        host="remote.example.com",
        port=5432,
        superuser="postgres",
        password="testpass",
        database="postgres",
        description="Test SSH host",
        ssh_config="test-ssh"
    )


class TestPostgreSQLLister:
    """Test the PostgreSQLLister class."""

    def test_init(self, local_host_config):
        """Test lister initialization."""
        lister = PostgreSQLLister(local_host_config)
        assert lister.host_config == local_host_config

    @patch('src.pgsqlmgr.listing.subprocess.run')
    def test_list_local_databases_success(self, mock_run, local_host_config):
        """Test successful local database listing."""
        # Mock subprocess output
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "testdb|postgres|UTF8|en_US.UTF-8|en_US.UTF-8||\npostgres|postgres|UTF8|en_US.UTF-8|en_US.UTF-8||"
        mock_run.return_value = mock_result

        lister = PostgreSQLLister(local_host_config)

        # Mock the database size method
        with patch.object(lister, '_get_database_size', return_value="10 MB"):
            success, databases, error = lister.list_databases(include_system=False)

        assert success is True
        assert len(databases) == 1  # Only testdb, postgres is system db
        assert databases[0]['name'] == 'testdb'
        assert databases[0]['owner'] == 'postgres'
        assert databases[0]['encoding'] == 'UTF8'
        assert error == ""

    @patch('src.pgsqlmgr.listing.subprocess.run')
    def test_list_local_databases_include_system(self, mock_run, local_host_config):
        """Test local database listing including system databases."""
        # Mock subprocess output
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "testdb|postgres|UTF8|en_US.UTF-8|en_US.UTF-8||\npostgres|postgres|UTF8|en_US.UTF-8|en_US.UTF-8||"
        mock_run.return_value = mock_result

        lister = PostgreSQLLister(local_host_config)

        # Mock the database size method
        with patch.object(lister, '_get_database_size', return_value="10 MB"):
            success, databases, error = lister.list_databases(include_system=True)

        assert success is True
        assert len(databases) == 2  # Both testdb and postgres
        assert error == ""

    @patch('src.pgsqlmgr.listing.subprocess.run')
    def test_list_local_databases_failure(self, mock_run, local_host_config):
        """Test failed local database listing."""
        # Mock subprocess failure
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Connection failed"
        mock_run.return_value = mock_result

        lister = PostgreSQLLister(local_host_config)
        success, databases, error = lister.list_databases()

        assert success is False
        assert databases == []
        assert "Connection failed" in error

    @patch('src.pgsqlmgr.listing.subprocess.run')
    def test_list_ssh_databases_success(self, mock_run, ssh_host_config):
        """Test successful SSH database listing."""
        # Mock subprocess output
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "testdb|postgres|UTF8|en_US.UTF-8|en_US.UTF-8||"
        mock_run.return_value = mock_result

        lister = PostgreSQLLister(ssh_host_config)

        # Mock the SSH database size method
        with patch.object(lister, '_get_ssh_database_size', return_value="10 MB"):
            success, databases, error = lister.list_databases()

        assert success is True
        assert len(databases) == 1
        assert databases[0]['name'] == 'testdb'
        assert error == ""

    @patch('src.pgsqlmgr.listing.subprocess.run')
    def test_list_local_users_success(self, mock_run, local_host_config):
        """Test successful local user listing."""
        # Mock subprocess output
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "postgres|t|t|t|t|-1|\ntestuser|f|f|f|t|10|2024-12-31"
        mock_run.return_value = mock_result

        lister = PostgreSQLLister(local_host_config)
        success, users, error = lister.list_users()

        assert success is True
        assert len(users) == 2
        assert users[0]['username'] == 'postgres'
        assert users[0]['is_superuser'] is True
        assert users[1]['username'] == 'testuser'
        assert users[1]['is_superuser'] is False
        assert users[1]['connection_limit'] == '10'
        assert error == ""

    @patch('src.pgsqlmgr.listing.subprocess.run')
    def test_list_tables_for_database_success(self, mock_run, local_host_config):
        """Test successful table listing for specific database."""
        # Mock subprocess output
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "public|users|postgres|1024 bytes|100\npublic|orders|postgres|2048 bytes|50"
        mock_run.return_value = mock_result

        lister = PostgreSQLLister(local_host_config)
        success, tables, error = lister.list_tables("testdb")

        assert success is True
        assert len(tables) == 2
        assert tables[0]['schema'] == 'public'
        assert tables[0]['table'] == 'users'
        assert tables[0]['owner'] == 'postgres'
        assert tables[0]['size'] == '1024 bytes'
        assert tables[0]['row_count'] == '100'
        assert error == ""

    def test_unsupported_host_type(self):
        """Test handling of unsupported host types."""
        # Create a mock host config with unsupported type
        mock_config = Mock()
        mock_config.type = "unsupported"

        lister = PostgreSQLLister(mock_config)
        success, databases, error = lister.list_databases()

        assert success is False
        assert databases == []
        assert "Unsupported host type" in error

    @patch('src.pgsqlmgr.listing.subprocess.run')
    def test_preview_table_content_success(self, mock_run, local_host_config):
        """Test successful table content preview."""
        # Mock subprocess output for column query
        mock_column_result = Mock()
        mock_column_result.returncode = 0
        mock_column_result.stdout = "id|integer\nname|character varying\nemail|character varying"

        # Mock subprocess output for data query
        mock_data_result = Mock()
        mock_data_result.returncode = 0
        mock_data_result.stdout = "1|John Doe|john@example.com\n2|Jane Smith|jane@example.com"

        # Set up mock to return different results for different calls
        mock_run.side_effect = [mock_column_result, mock_data_result]

        lister = PostgreSQLLister(local_host_config)
        success, data_rows, columns, error = lister.preview_table_content("testdb", "users")

        assert success is True
        assert len(data_rows) == 2
        assert columns == ['id', 'name', 'email']
        assert data_rows[0]['id'] == '1'
        assert data_rows[0]['name'] == 'John Doe'
        assert data_rows[0]['email'] == 'john@example.com'
        assert data_rows[1]['id'] == '2'
        assert data_rows[1]['name'] == 'Jane Smith'
        assert error == ""

    @patch('src.pgsqlmgr.listing.subprocess.run')
    def test_preview_table_content_with_nulls(self, mock_run, local_host_config):
        """Test table content preview with NULL values."""
        # Mock subprocess output for column query
        mock_column_result = Mock()
        mock_column_result.returncode = 0
        mock_column_result.stdout = "id|integer\nname|character varying\nemail|character varying"

        # Mock subprocess output for data query with NULL values (empty fields)
        mock_data_result = Mock()
        mock_data_result.returncode = 0
        mock_data_result.stdout = "1|John Doe|\n2||jane@example.com"

        mock_run.side_effect = [mock_column_result, mock_data_result]

        lister = PostgreSQLLister(local_host_config)
        success, data_rows, columns, error = lister.preview_table_content("testdb", "users")

        assert success is True
        assert len(data_rows) == 2
        assert data_rows[0]['email'] is None  # Empty field becomes None
        assert data_rows[1]['name'] is None   # Empty field becomes None
        assert data_rows[1]['email'] == 'jane@example.com'
        assert error == ""

    @patch('src.pgsqlmgr.listing.subprocess.run')
    def test_preview_table_content_no_columns(self, mock_run, local_host_config):
        """Test table content preview when no columns are found."""
        # Mock subprocess output for column query (no results)
        mock_column_result = Mock()
        mock_column_result.returncode = 0
        mock_column_result.stdout = ""

        mock_run.return_value = mock_column_result

        lister = PostgreSQLLister(local_host_config)
        success, data_rows, columns, error = lister.preview_table_content("testdb", "nonexistent")

        assert success is False
        assert data_rows == []
        assert columns == []
        assert "No columns found" in error

    @patch('src.pgsqlmgr.listing.subprocess.run')
    def test_preview_table_content_query_failure(self, mock_run, local_host_config):
        """Test table content preview when query fails."""
        # Mock subprocess failure
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Table does not exist"

        mock_run.return_value = mock_result

        lister = PostgreSQLLister(local_host_config)
        success, data_rows, columns, error = lister.preview_table_content("testdb", "nonexistent")

        assert success is False
        assert data_rows == []
        assert columns == []
        assert "Table does not exist" in error

    @patch('src.pgsqlmgr.listing.subprocess.run')
    def test_preview_table_content_ssh_success(self, mock_run, ssh_host_config):
        """Test successful SSH table content preview."""
        # Mock subprocess output for column query
        mock_column_result = Mock()
        mock_column_result.returncode = 0
        mock_column_result.stdout = "id|integer\nname|character varying"

        # Mock subprocess output for data query
        mock_data_result = Mock()
        mock_data_result.returncode = 0
        mock_data_result.stdout = "1|Test User\n2|Another User"

        mock_run.side_effect = [mock_column_result, mock_data_result]

        lister = PostgreSQLLister(ssh_host_config)
        success, data_rows, columns, error = lister.preview_table_content("testdb", "users")

        assert success is True
        assert len(data_rows) == 2
        assert columns == ['id', 'name']
        assert data_rows[0]['id'] == '1'
        assert data_rows[0]['name'] == 'Test User'
        assert error == ""

    def test_preview_table_content_unsupported_host_type(self):
        """Test table preview with unsupported host type."""
        mock_config = Mock()
        mock_config.type = "unsupported"

        lister = PostgreSQLLister(mock_config)
        success, data_rows, columns, error = lister.preview_table_content("testdb", "users")

        assert success is False
        assert data_rows == []
        assert columns == []
        assert "Unsupported host type" in error


class TestDisplayFunctions:
    """Test the display functions."""

    @patch('src.pgsqlmgr.listing.console')
    def test_display_databases_empty(self, mock_console):
        """Test displaying empty database list."""
        display_databases([], "test-host")
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "No user databases found" in call_args

    @patch('src.pgsqlmgr.listing.console')
    def test_display_databases_with_data(self, mock_console):
        """Test displaying database list with data."""
        databases = [
            {
                'name': 'testdb',
                'owner': 'postgres',
                'encoding': 'UTF8',
                'size': '10 MB',
                'access_privileges': 'None'
            }
        ]

        display_databases(databases, "test-host")

        # Should call print twice - once for table, once for console.print(table)
        assert mock_console.print.called

    @patch('src.pgsqlmgr.listing.console')
    def test_display_tables_empty(self, mock_console):
        """Test displaying empty table list."""
        display_tables([], "in database 'test'")
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "No tables found" in call_args

    @patch('src.pgsqlmgr.listing.console')
    def test_display_tables_with_data(self, mock_console):
        """Test displaying table list with data."""
        tables = [
            {
                'schema': 'public',
                'table': 'users',
                'owner': 'postgres',
                'size': '1024 bytes',
                'row_count': '100'
            }
        ]

        display_tables(tables, "in database 'test'")

        assert mock_console.print.called

    @patch('src.pgsqlmgr.listing.console')
    def test_display_tables_with_database_column(self, mock_console):
        """Test displaying table list with database column."""
        tables = [
            {
                'database': 'testdb',
                'schema': 'public',
                'table': 'users',
                'owner': 'postgres',
                'size': '1024 bytes',
                'row_count': '100'
            }
        ]

        display_tables(tables, "across all databases")

        assert mock_console.print.called

    @patch('src.pgsqlmgr.listing.console')
    def test_display_users_empty(self, mock_console):
        """Test displaying empty user list."""
        display_users([], "test-host")
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "No users found" in call_args

    @patch('src.pgsqlmgr.listing.console')
    def test_display_users_with_data(self, mock_console):
        """Test displaying user list with data."""
        users = [
            {
                'username': 'postgres',
                'is_superuser': True,
                'can_create_roles': True,
                'can_create_databases': True,
                'can_login': True,
                'connection_limit': 'Unlimited',
                'valid_until': 'Never'
            }
        ]

        display_users(users, "test-host")

        assert mock_console.print.called

    @patch('src.pgsqlmgr.listing.console')
    def test_display_table_preview_empty(self, mock_console):
        """Test displaying empty table preview."""
        display_table_preview([], ['id', 'name'], "users", "testdb")
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "No data found" in call_args

    @patch('src.pgsqlmgr.listing.console')
    def test_display_table_preview_with_data(self, mock_console):
        """Test displaying table preview with data."""
        data_rows = [
            {'id': '1', 'name': 'John Doe', 'email': 'john@example.com'},
            {'id': '2', 'name': 'Jane Smith', 'email': 'jane@example.com'}
        ]
        columns = ['id', 'name', 'email']

        display_table_preview(data_rows, columns, "users", "testdb", "public", 10)

        # Should call print at least once for the table
        assert mock_console.print.called

    @patch('src.pgsqlmgr.listing.console')
    def test_display_table_preview_with_nulls(self, mock_console):
        """Test displaying table preview with NULL values."""
        data_rows = [
            {'id': '1', 'name': 'John Doe', 'email': None},
            {'id': '2', 'name': None, 'email': 'jane@example.com'}
        ]
        columns = ['id', 'name', 'email']

        display_table_preview(data_rows, columns, "users", "testdb", "public", 10)

        assert mock_console.print.called

    @patch('src.pgsqlmgr.listing.console')
    def test_display_table_preview_long_values(self, mock_console):
        """Test displaying table preview with long values that get truncated."""
        data_rows = [
            {
                'id': '1',
                'name': 'This is a very long name that should be truncated for display purposes',
                'description': 'This is an extremely long description that definitely exceeds the display limit'
            }
        ]
        columns = ['id', 'name', 'description']

        display_table_preview(data_rows, columns, "users", "testdb", "public", 10)

        assert mock_console.print.called

    @patch('src.pgsqlmgr.listing.console')
    def test_display_table_preview_limit_reached(self, mock_console):
        """Test displaying table preview when limit is reached."""
        # Create exactly 10 rows to match the limit
        data_rows = [{'id': str(i), 'name': f'User {i}'} for i in range(1, 11)]
        columns = ['id', 'name']

        display_table_preview(data_rows, columns, "users", "testdb", "public", 10)

        # Should call print multiple times (table + limit note)
        assert mock_console.print.call_count >= 2


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_exception_in_list_databases(self, local_host_config):
        """Test exception handling in list_databases."""
        lister = PostgreSQLLister(local_host_config)

        # Mock subprocess to raise an exception
        with patch('src.pgsqlmgr.listing.subprocess.run', side_effect=Exception("Test error")):
            success, databases, error = lister.list_databases()

        assert success is False
        assert databases == []
        assert "Test error" in error

    def test_exception_in_list_users(self, local_host_config):
        """Test exception handling in list_users."""
        lister = PostgreSQLLister(local_host_config)

        # Mock subprocess to raise an exception
        with patch('src.pgsqlmgr.listing.subprocess.run', side_effect=Exception("Test error")):
            success, users, error = lister.list_users()

        assert success is False
        assert users == []
        assert "Test error" in error

    def test_exception_in_list_tables(self, local_host_config):
        """Test exception handling in list_tables."""
        lister = PostgreSQLLister(local_host_config)

        # Mock subprocess to raise an exception
        with patch('src.pgsqlmgr.listing.subprocess.run', side_effect=Exception("Test error")):
            success, tables, error = lister.list_tables("testdb")

        assert success is False
        assert tables == []
        assert "Test error" in error

    @patch('src.pgsqlmgr.listing.subprocess.run')
    def test_list_tables_with_preview_integration(self, mock_run, local_host_config):
        """Test that preview functionality can be integrated with table listing."""
        # Mock table listing response
        mock_table_result = Mock()
        mock_table_result.returncode = 0
        mock_table_result.stdout = "public|users|postgres|1024 bytes|100\npublic|orders|postgres|2048 bytes|50"

        # Mock column query response for preview
        mock_column_result = Mock()
        mock_column_result.returncode = 0
        mock_column_result.stdout = "id|integer\nname|character varying"

        # Mock data query response for preview
        mock_data_result = Mock()
        mock_data_result.returncode = 0
        mock_data_result.stdout = "1|John Doe\n2|Jane Smith"

        # Set up mock to return different results for different calls
        # First call: table listing, then alternating column/data queries for each table
        mock_run.side_effect = [
            mock_table_result,  # Table listing
            mock_column_result, mock_data_result,  # Preview for users table
            mock_column_result, mock_data_result   # Preview for orders table
        ]

        lister = PostgreSQLLister(local_host_config)

        # Test table listing
        success, tables, error = lister.list_tables("testdb")
        assert success is True
        assert len(tables) == 2

        # Test preview for each table (simulating the integrated functionality)
        for table in tables:
            table_name = table['table']
            success, data_rows, columns, error = lister.preview_table_content("testdb", table_name)
            assert success is True
            assert len(data_rows) == 2
            assert columns == ['id', 'name']

    @patch('src.pgsqlmgr.listing.subprocess.run')
    def test_preview_with_fixed_limit(self, mock_run, local_host_config):
        """Test preview functionality with fixed 10 record limit."""
        # Mock column query response
        mock_column_result = Mock()
        mock_column_result.returncode = 0
        mock_column_result.stdout = "id|integer\nname|character varying"

        # Mock data query response with more records
        mock_data_result = Mock()
        mock_data_result.returncode = 0
        mock_data_result.stdout = "1|User 1\n2|User 2\n3|User 3\n4|User 4\n5|User 5"

        mock_run.side_effect = [mock_column_result, mock_data_result]

        lister = PostgreSQLLister(local_host_config)
        # Test with fixed limit of 10 (simulating --preview)
        success, data_rows, columns, error = lister.preview_table_content("testdb", "users", "public", 10)

        assert success is True
        assert len(data_rows) == 5  # Only 5 records in mock data
        assert columns == ['id', 'name']
        assert data_rows[0]['id'] == '1'
        assert data_rows[4]['id'] == '5'

    @patch('src.pgsqlmgr.listing.subprocess.run')
    def test_preview_with_empty_table(self, mock_run, local_host_config):
        """Test preview functionality with an empty table."""
        # Mock column query response
        mock_column_result = Mock()
        mock_column_result.returncode = 0
        mock_column_result.stdout = "id|integer\nname|character varying"

        # Mock empty data query response
        mock_data_result = Mock()
        mock_data_result.returncode = 0
        mock_data_result.stdout = ""

        mock_run.side_effect = [mock_column_result, mock_data_result]

        lister = PostgreSQLLister(local_host_config)
        success, data_rows, columns, error = lister.preview_table_content("testdb", "empty_table")

        assert success is True
        assert len(data_rows) == 0
        assert columns == ['id', 'name']
        assert error == ""

    @patch('src.pgsqlmgr.listing.subprocess.run')
    def test_preview_with_different_schemas(self, mock_run, local_host_config):
        """Test preview functionality with different schemas."""
        # Mock column query response
        mock_column_result = Mock()
        mock_column_result.returncode = 0
        mock_column_result.stdout = "product_id|integer\nproduct_name|character varying"

        # Mock data query response
        mock_data_result = Mock()
        mock_data_result.returncode = 0
        mock_data_result.stdout = "1|Widget A\n2|Widget B"

        mock_run.side_effect = [mock_column_result, mock_data_result]

        lister = PostgreSQLLister(local_host_config)
        success, data_rows, columns, error = lister.preview_table_content("testdb", "products", "inventory")

        assert success is True
        assert len(data_rows) == 2
        assert columns == ['product_id', 'product_name']
        assert data_rows[0]['product_id'] == '1'
        assert data_rows[0]['product_name'] == 'Widget A'
