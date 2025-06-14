"""PostgreSQL database object listing functionality."""

import subprocess
from typing import Any

from rich.console import Console
from rich.table import Table

from .config import HostConfig, HostType, LocalHost, SSHHost

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


class PostgreSQLLister:
    """Handle listing of PostgreSQL database objects."""

    def __init__(self, host_config: HostConfig):
        """Initialize with host configuration."""
        self.host_config = host_config

    def list_databases(self, include_system: bool = False) -> tuple[bool, list[dict[str, Any]], str]:
        """
        List all databases on the host.

        Args:
            include_system: Whether to include system databases (postgres, template0, template1)

        Returns:
            Tuple of (success, database_list, error_message)
        """
        try:
            if self.host_config.type == HostType.LOCAL:
                return self._list_local_databases(include_system)
            elif self.host_config.type == HostType.SSH:
                return self._list_ssh_databases(include_system)
            else:
                return False, [], "Unsupported host type for database listing"
        except Exception as e:
            return False, [], f"Error listing databases: {e}"

    def list_tables(self, database_name: str | None = None, include_system: bool = False) -> tuple[bool, list[dict[str, Any]], str]:
        """
        List tables in a specific database or all user databases.

        Args:
            database_name: Specific database to list tables for (None for all user databases)
            include_system: Whether to include system tables

        Returns:
            Tuple of (success, table_list, error_message)
        """
        try:
            if database_name:
                # List tables for specific database
                return self._list_tables_for_database(database_name, include_system)
            else:
                # List tables for all user databases
                return self._list_tables_all_databases(include_system)
        except Exception as e:
            return False, [], f"Error listing tables: {e}"

    def list_users(self) -> tuple[bool, list[dict[str, Any]], str]:
        """
        List all PostgreSQL users/roles.

        Returns:
            Tuple of (success, user_list, error_message)
        """
        try:
            if self.host_config.type == HostType.LOCAL:
                return self._list_local_users()
            elif self.host_config.type == HostType.SSH:
                return self._list_ssh_users()
            else:
                return False, [], "Unsupported host type for user listing"
        except Exception as e:
            return False, [], f"Error listing users: {e}"

    def preview_table_content(self, database_name: str, table_name: str, schema: str = "public", limit: int = 10) -> tuple[bool, list[dict[str, Any]], list[str], str]:
        """
        Preview table content with a limited number of records.

        Args:
            database_name: Database containing the table
            table_name: Name of the table to preview
            schema: Schema name (default: public)
            limit: Maximum number of records to return (default: 10)

        Returns:
            Tuple of (success, data_rows, column_names, error_message)
        """
        try:
            # Build the SQL query to get table content
            sql_query = f"""
            SELECT * FROM {schema}.{table_name}
            ORDER BY 1
            LIMIT {limit};
            """

            if self.host_config.type == HostType.LOCAL:
                return self._execute_local_preview_query(database_name, sql_query, table_name)
            elif self.host_config.type == HostType.SSH:
                return self._execute_ssh_preview_query(database_name, sql_query, table_name)
            else:
                return False, [], [], "Unsupported host type for table preview"
        except Exception as e:
            return False, [], [], f"Error previewing table content: {e}"

    def _list_local_databases(self, include_system: bool) -> tuple[bool, list[dict[str, Any]], str]:
        """List databases on local PostgreSQL."""
        cmd = [
            "psql",
            "--host", self.host_config.host,
            "--port", str(self.host_config.port),
            "--username", self.host_config.superuser,
            "--list",
            "--tuples-only",
            "--no-align",
            "--field-separator=|"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            error_msg = f"Failed to list databases: {result.stderr}"
            if "authentication failed" in result.stderr.lower() or "password" in result.stderr.lower():
                error_msg += _get_auth_help_message(self.host_config)
            return False, [], error_msg

        databases = []
        system_dbs = {'postgres', 'template0', 'template1'}

        for line in result.stdout.strip().split('\n'):
            if line and '|' in line:
                parts = line.split('|')
                if len(parts) >= 6:
                    db_name = parts[0].strip()
                    if db_name and (include_system or db_name not in system_dbs):
                        databases.append({
                            'name': db_name,
                            'owner': parts[1].strip(),
                            'encoding': parts[2].strip(),
                            'collate': parts[3].strip(),
                            'ctype': parts[4].strip(),
                            'access_privileges': parts[5].strip() if parts[5].strip() else 'None',
                            'size': self._get_database_size(db_name)
                        })

        return True, databases, ""

    def _list_ssh_databases(self, include_system: bool) -> tuple[bool, list[dict[str, Any]], str]:
        """List databases on SSH PostgreSQL."""
        cmd = [
            "ssh",
            self.host_config.ssh_config,
            f"sudo -u {self.host_config.superuser} psql --list --tuples-only --no-align --field-separator='|'"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return False, [], f"Failed to list databases via SSH: {result.stderr}"

        databases = []
        system_dbs = {'postgres', 'template0', 'template1'}

        for line in result.stdout.strip().split('\n'):
            if line and '|' in line:
                parts = line.split('|')
                if len(parts) >= 6:
                    db_name = parts[0].strip()
                    if db_name and (include_system or db_name not in system_dbs):
                        databases.append({
                            'name': db_name,
                            'owner': parts[1].strip(),
                            'encoding': parts[2].strip(),
                            'collate': parts[3].strip(),
                            'ctype': parts[4].strip(),
                            'access_privileges': parts[5].strip() if parts[5].strip() else 'None',
                            'size': self._get_ssh_database_size(db_name)
                        })

        return True, databases, ""

    def _list_tables_for_database(self, database_name: str, include_system: bool) -> tuple[bool, list[dict[str, Any]], str]:
        """List tables for a specific database."""
        # SQL query to get table information
        # Build the WHERE clause based on include_system flag
        if include_system:
            where_clause = ""
        else:
            where_clause = "WHERE schemaname != 'information_schema' AND schemaname != 'pg_catalog'"

        sql_query = f"""
        SELECT
            schemaname,
            tablename,
            tableowner,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
            pg_stat_get_tuples_returned(c.oid) as row_count
        FROM pg_tables pt
        JOIN pg_class c ON c.relname = pt.tablename
        {where_clause}
        ORDER BY schemaname, tablename;
        """

        if self.host_config.type == HostType.LOCAL:
            return self._execute_local_query(database_name, sql_query)
        elif self.host_config.type == HostType.SSH:
            return self._execute_ssh_query(database_name, sql_query)
        else:
            return False, [], "Unsupported host type"

    def _list_tables_all_databases(self, include_system: bool) -> tuple[bool, list[dict[str, Any]], str]:
        """List tables for all user databases."""
        # First get list of databases
        success, databases, error = self.list_databases(include_system=False)
        if not success:
            return False, [], error

        all_tables = []
        for db in databases:
            db_name = db['name']
            success, tables, error = self._list_tables_for_database(db_name, include_system)
            if success:
                # Add database name to each table record
                for table in tables:
                    table['database'] = db_name
                all_tables.extend(tables)
            else:
                console.print(f"[yellow]⚠️  Could not list tables for database '{db_name}': {error}[/yellow]")

        return True, all_tables, ""

    def _list_local_users(self) -> tuple[bool, list[dict[str, Any]], str]:
        """List users on local PostgreSQL."""
        sql_query = """
        SELECT
            rolname as username,
            rolsuper as is_superuser,
            rolcreaterole as can_create_roles,
            rolcreatedb as can_create_databases,
            rolcanlogin as can_login,
            rolconnlimit as connection_limit,
            rolvaliduntil as valid_until
        FROM pg_roles
        ORDER BY rolname;
        """

        return self._execute_local_query("postgres", sql_query)

    def _list_ssh_users(self) -> tuple[bool, list[dict[str, Any]], str]:
        """List users on SSH PostgreSQL."""
        sql_query = """
        SELECT
            rolname as username,
            rolsuper as is_superuser,
            rolcreaterole as can_create_roles,
            rolcreatedb as can_create_databases,
            rolcanlogin as can_login,
            rolconnlimit as connection_limit,
            rolvaliduntil as valid_until
        FROM pg_roles
        ORDER BY rolname;
        """

        return self._execute_ssh_query("postgres", sql_query)

    def _execute_local_query(self, database_name: str, sql_query: str) -> tuple[bool, list[dict[str, Any]], str]:
        """Execute SQL query on local PostgreSQL."""
        cmd = [
            "psql",
            "--host", self.host_config.host,
            "--port", str(self.host_config.port),
            "--username", self.host_config.superuser,
            "--dbname", database_name,
            "--tuples-only",
            "--no-align",
            "--field-separator=|",
            "--command", sql_query
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            error_msg = f"Query failed: {result.stderr}"
            if "authentication failed" in result.stderr.lower() or "password" in result.stderr.lower():
                error_msg += _get_auth_help_message(self.host_config)
            return False, [], error_msg

        return self._parse_query_result(result.stdout, sql_query)

    def _execute_ssh_query(self, database_name: str, sql_query: str) -> tuple[bool, list[dict[str, Any]], str]:
        """Execute SQL query on SSH PostgreSQL."""
        # Escape the SQL query for shell
        escaped_query = sql_query.replace("'", "'\"'\"'")

        cmd = [
            "ssh",
            self.host_config.ssh_config,
            f"sudo -u {self.host_config.superuser} psql --dbname {database_name} --tuples-only --no-align --field-separator='|' --command '{escaped_query}'"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return False, [], f"SSH query failed: {result.stderr}"

        return self._parse_query_result(result.stdout, sql_query)

    def _parse_query_result(self, output: str, sql_query: str) -> tuple[bool, list[dict[str, Any]], str]:
        """Parse SQL query result into list of dictionaries."""
        lines = [line.strip() for line in output.strip().split('\n') if line.strip()]
        if not lines:
            return True, [], ""

        # Determine column names based on query type
        if "pg_tables" in sql_query:
            columns = ['schema', 'table', 'owner', 'size', 'row_count']
        elif "pg_roles" in sql_query:
            columns = ['username', 'is_superuser', 'can_create_roles', 'can_create_databases',
                      'can_login', 'connection_limit', 'valid_until']
        else:
            # Generic parsing - use first line as headers if available
            columns = [f'column_{i}' for i in range(len(lines[0].split('|')))]

        results = []
        for line in lines:
            if '|' in line:
                values = line.split('|')
                if len(values) == len(columns):
                    row = {}
                    for i, col in enumerate(columns):
                        value = values[i].strip()
                        # Convert boolean strings
                        if value.lower() in ('t', 'true'):
                            value = True
                        elif value.lower() in ('f', 'false'):
                            value = False
                        elif value == '-1':
                            value = 'Unlimited'
                        elif value == '':
                            value = None
                        row[col] = value
                    results.append(row)

        return True, results, ""

    def _get_database_size(self, database_name: str) -> str:
        """Get database size for local PostgreSQL."""
        try:
            cmd = [
                "psql",
                "--host", self.host_config.host,
                "--port", str(self.host_config.port),
                "--username", self.host_config.superuser,
                "--dbname", database_name,
                "--tuples-only",
                "--no-align",
                "--command", f"SELECT pg_size_pretty(pg_database_size('{database_name}'));"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return "Unknown"

    def _get_ssh_database_size(self, database_name: str) -> str:
        """Get database size for SSH PostgreSQL."""
        try:
            cmd = [
                "ssh",
                self.host_config.ssh_config,
                f"sudo -u {self.host_config.superuser} psql --dbname {database_name} --tuples-only --no-align --command \"SELECT pg_size_pretty(pg_database_size('{database_name}'));\""
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return "Unknown"

    def _execute_local_preview_query(self, database_name: str, sql_query: str, table_name: str) -> tuple[bool, list[dict[str, Any]], list[str], str]:
        """Execute preview query on local PostgreSQL."""
        # First get column names
        column_query = f"""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = '{table_name}'
        ORDER BY ordinal_position;
        """

        cmd = [
            "psql",
            "--host", self.host_config.host,
            "--port", str(self.host_config.port),
            "--username", self.host_config.superuser,
            "--dbname", database_name,
            "--tuples-only",
            "--no-align",
            "--field-separator=|",
            "--command", column_query
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return False, [], [], f"Failed to get column info: {result.stderr}"

        # Parse column names and types
        columns = []
        for line in result.stdout.strip().split('\n'):
            if line and '|' in line:
                parts = line.split('|')
                if len(parts) >= 2:
                    columns.append(parts[0].strip())

        if not columns:
            return False, [], [], f"No columns found for table {table_name}"

        # Now get the actual data
        cmd[9] = sql_query  # Replace the command

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return False, [], [], f"Query failed: {result.stderr}"

        # Parse the data
        data_rows = []
        for line in result.stdout.strip().split('\n'):
            if line and '|' in line:
                values = line.split('|')
                if len(values) == len(columns):
                    row = {}
                    for i, col in enumerate(columns):
                        value = values[i].strip()
                        # Handle NULL values
                        if value == '':
                            value = None
                        row[col] = value
                    data_rows.append(row)

        return True, data_rows, columns, ""

    def _execute_ssh_preview_query(self, database_name: str, sql_query: str, table_name: str) -> tuple[bool, list[dict[str, Any]], list[str], str]:
        """Execute preview query on SSH PostgreSQL."""
        # First get column names
        column_query = f"""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = '{table_name}'
        ORDER BY ordinal_position;
        """

        # Escape the SQL query for shell
        escaped_column_query = column_query.replace("'", "'\"'\"'")

        cmd = [
            "ssh",
            self.host_config.ssh_config,
            f"sudo -u {self.host_config.superuser} psql --dbname {database_name} --tuples-only --no-align --field-separator='|' --command '{escaped_column_query}'"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return False, [], [], f"SSH column query failed: {result.stderr}"

        # Parse column names
        columns = []
        for line in result.stdout.strip().split('\n'):
            if line and '|' in line:
                parts = line.split('|')
                if len(parts) >= 2:
                    columns.append(parts[0].strip())

        if not columns:
            return False, [], [], f"No columns found for table {table_name}"

        # Now get the actual data
        escaped_data_query = sql_query.replace("'", "'\"'\"'")

        cmd = [
            "ssh",
            self.host_config.ssh_config,
            f"sudo -u {self.host_config.superuser} psql --dbname {database_name} --tuples-only --no-align --field-separator='|' --command '{escaped_data_query}'"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return False, [], [], f"SSH data query failed: {result.stderr}"

        # Parse the data
        data_rows = []
        for line in result.stdout.strip().split('\n'):
            if line and '|' in line:
                values = line.split('|')
                if len(values) == len(columns):
                    row = {}
                    for i, col in enumerate(columns):
                        value = values[i].strip()
                        # Handle NULL values
                        if value == '':
                            value = None
                        row[col] = value
                    data_rows.append(row)

        return True, data_rows, columns, ""


def display_databases(databases: list[dict[str, Any]], host_name: str, include_system: bool = False):
    """Display databases in a nice table format."""
    if not databases:
        console.print(f"[yellow]No {'databases' if include_system else 'user databases'} found on {host_name}[/yellow]")
        return

    table = Table(title=f"Databases on {host_name}")
    table.add_column("Database Name", style="cyan", no_wrap=True)
    table.add_column("Owner", style="green")
    table.add_column("Encoding", style="blue")
    table.add_column("Size", style="magenta")
    table.add_column("Access Privileges", style="yellow")

    for db in databases:
        table.add_row(
            db['name'],
            db['owner'],
            db['encoding'],
            db['size'],
            db['access_privileges']
        )

    console.print(table)


def display_tables(tables: list[dict[str, Any]], context: str):
    """Display tables in a nice table format."""
    if not tables:
        console.print(f"[yellow]No tables found {context}[/yellow]")
        return

    table = Table(title=f"Tables {context}")

    # Check if we have database column (multi-database listing)
    has_database_col = any('database' in t for t in tables)

    if has_database_col:
        table.add_column("Database", style="cyan", no_wrap=True)

    table.add_column("Schema", style="blue", no_wrap=True)
    table.add_column("Table Name", style="green", no_wrap=True)
    table.add_column("Owner", style="yellow")
    table.add_column("Size", style="magenta")
    table.add_column("Est. Rows", style="red")

    for t in tables:
        row = []
        if has_database_col:
            row.append(t.get('database', 'N/A'))

        row.extend([
            t.get('schema', 'N/A'),
            t.get('table', 'N/A'),
            t.get('owner', 'N/A'),
            t.get('size', 'N/A'),
            str(t.get('row_count', 'N/A'))
        ])

        table.add_row(*row)

    console.print(table)


def display_users(users: list[dict[str, Any]], host_name: str):
    """Display users in a nice table format."""
    if not users:
        console.print(f"[yellow]No users found on {host_name}[/yellow]")
        return

    table = Table(title=f"PostgreSQL Users on {host_name}")
    table.add_column("Username", style="cyan", no_wrap=True)
    table.add_column("Superuser", style="red")
    table.add_column("Create Roles", style="green")
    table.add_column("Create DBs", style="blue")
    table.add_column("Can Login", style="yellow")
    table.add_column("Connection Limit", style="magenta")
    table.add_column("Valid Until", style="white")

    for user in users:
        table.add_row(
            user['username'],
            "✓" if user['is_superuser'] else "✗",
            "✓" if user['can_create_roles'] else "✗",
            "✓" if user['can_create_databases'] else "✗",
            "✓" if user['can_login'] else "✗",
            str(user['connection_limit']) if user['connection_limit'] else "Unlimited",
            str(user['valid_until']) if user['valid_until'] else "Never"
        )

    console.print(table)


def display_table_preview(data_rows: list[dict[str, Any]], columns: list[str], table_name: str, database_name: str, schema: str = "public", limit: int = 10):
    """Display table content preview in a nice table format."""
    if not data_rows:
        console.print(f"[yellow]No data found in table {schema}.{table_name}[/yellow]")
        return

    # Create table with dynamic columns
    table = Table(title=f"Preview: {schema}.{table_name} in {database_name} (showing {len(data_rows)} of max {limit} records)")

    # Add columns dynamically
    for col in columns:
        # Determine column style based on common column names
        if col.lower() in ['id', 'pk', 'primary_key']:
            style = "bold blue"
        elif col.lower() in ['name', 'title', 'username']:
            style = "green"
        elif col.lower() in ['email', 'phone', 'contact']:
            style = "cyan"
        elif col.lower() in ['created_at', 'updated_at', 'timestamp']:
            style = "yellow"
        elif col.lower() in ['status', 'state', 'active']:
            style = "magenta"
        else:
            style = "white"

        # Truncate long column names for display
        display_name = col if len(col) <= 15 else col[:12] + "..."
        table.add_column(display_name, style=style, no_wrap=True, max_width=20)

    # Add data rows
    for row in data_rows:
        row_values = []
        for col in columns:
            value = row.get(col)
            if value is None:
                row_values.append("[dim]NULL[/dim]")
            else:
                # Truncate long values for display
                str_value = str(value)
                if len(str_value) > 20:
                    str_value = str_value[:17] + "..."
                row_values.append(str_value)

        table.add_row(*row_values)

    console.print(table)

    # Show summary info
    if len(data_rows) == limit:
        console.print(f"[dim]Note: Showing first {limit} records.[/dim]")
