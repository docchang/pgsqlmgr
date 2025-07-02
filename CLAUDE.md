# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Package Installation
```bash
# Install in editable mode with development dependencies
pip install -e ".[dev]"

# Verify installation
pgsqlmgr --help
pgsqlmgr --version
```

### Code Quality and Testing
```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/

# Run tests
pytest

# Run tests with coverage
pytest --cov=pgsqlmgr

# Run specific test file
pytest tests/test_config.py -v
```

### CLI Testing
```bash
# Initialize sample configuration
pgsqlmgr init-config

# Test configuration validation
pgsqlmgr validate-config

# List configured hosts
pgsqlmgr list-hosts

# Check PostgreSQL installation
pgsqlmgr check-install local

# List databases (requires working PostgreSQL)
pgsqlmgr list-databases local

# Run database sync (dry run)
pgsqlmgr sync-db local mydb remote --dry-run
```

## Architecture Overview

PostgreSQL Manager is a modular CLI tool built around a clean separation of concerns:

### Core Components

**Configuration Layer (`config.py`)**
- Pydantic-based validation with inheritance hierarchy
- Host types: LOCAL, SSH, CLOUD with type-specific configurations
- YAML configuration with comprehensive error reporting
- Automatic SSH config validation

**CLI Interface (`main.py`)**
- Typer-based command structure with Rich UI components
- 15+ commands covering installation, listing, sync, and deletion
- Comprehensive error handling with actionable user guidance
- Dry-run capabilities for destructive operations

**Database Operations (`db.py`)**
- `DatabaseManager`: Core database CRUD operations
- `PostgreSQLManager`: Installation and service management
- Cross-platform support (macOS Homebrew, Linux apt/yum/dnf)
- `.pgpass` authentication integration

**Database Listing (`listing.py`)**
- `PostgreSQLLister`: Read-only database introspection
- Rich table displays for databases, tables, users, and content previews
- Intelligent formatting and column truncation

**Database Synchronization (`sync.py`)**
- `DatabaseSyncManager`: pg_dump/restore-based database migration
- Progress tracking with Rich progress bars
- Multiple sync modes: full, schema-only, data-only
- Automatic cleanup and comprehensive error handling

**SSH Operations (`ssh.py`)**
- Infrastructure for remote operations via SSH config shortcuts
- Conditional Fabric dependency for development flexibility
- Future-ready for connection pooling and file transfers

**Cloud Integration (`cloud.py`)**
- Extensible architecture for cloud providers (v2.0 feature)
- Factory pattern for provider-specific implementations

### Key Design Patterns

1. **Strategy Pattern**: Different implementations for Local vs SSH vs Cloud hosts
2. **Factory Pattern**: Host configuration and cloud manager creation
3. **Template Method**: Installation workflows and sync operations
4. **Builder Pattern**: Command construction for different platforms

### Authentication Architecture

- **Local hosts**: Direct PostgreSQL connection
- **SSH hosts**: SSH config shortcuts + `.pgpass` for PostgreSQL auth
- **PostgreSQL auth**: Standard `.pgpass` file with helpful error guidance
- **SSH auth**: Key-based authentication via `~/.ssh/config` entries

## Common Development Patterns

### Host Configuration Access
```python
from .config import get_host_config, HostType

# Get host configuration
host_config = get_host_config("production", config_path)

# Type-specific operations
if host_config.type == HostType.SSH:
    # SSH-specific logic
    ssh_config = host_config.ssh_config
elif host_config.type == HostType.LOCAL:
    # Local-specific logic
    pass
```

### Database Operations
```python
from .db import DatabaseManager, PostgreSQLManager

# Database CRUD operations
db_manager = DatabaseManager(host_config)
db_info = db_manager.get_database_info("mydb")
success, message = db_manager.drop_database("olddb")

# PostgreSQL installation management
pg_manager = PostgreSQLManager(host_config)
is_installed, status, version = pg_manager.check_postgresql_installation()
```

### Rich UI Components
```python
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

# Create progress indicators
console.print("[blue]🔍 Checking installation...[/blue]")

# Display results in panels
console.print(Panel(
    f"✅ {message}",
    title=f"Status: {host}",
    style="green"
))
```

## Configuration Management

### Configuration File Structure
- Default location: `~/.pgsqlmgr/config.yaml`
- Pydantic validation with comprehensive error messages
- Host inheritance with type-specific fields

### Example Host Configurations
```yaml
hosts:
  local:
    type: local
    host: localhost
    port: 5432
    superuser: postgres
    description: "Local PostgreSQL instance"
  
  production:
    type: ssh
    ssh_config: production  # References ~/.ssh/config
    host: localhost
    port: 5432
    superuser: postgres
    description: "Production server via SSH"
```

### SSH Configuration Requirements
```
# ~/.ssh/config
Host production
    HostName production.example.com
    User admin
    IdentityFile ~/.ssh/id_rsa
```

### PostgreSQL Authentication
```
# ~/.pgpass format: hostname:port:database:username:password
localhost:5432:*:postgres:local_password
localhost:5433:*:postgres:production_password  # SSH tunnel
```

## Error Handling Philosophy

1. **Configuration Errors**: Detailed validation messages with field paths
2. **Connection Errors**: Actionable guidance for SSH and PostgreSQL setup
3. **Operation Errors**: User-friendly messages with suggested fixes
4. **Authentication Errors**: Specific guidance for `.pgpass` and SSH key setup

## Testing Architecture

- **Unit Tests**: Configuration validation, command parsing
- **Integration Tests**: Database operations (127 tests total)
- **SSH Tests**: Remote operation simulation
- **Mock-based**: External dependencies mocked for reliable testing

## Module Responsibilities

- `main.py`: CLI interface and command orchestration
- `config.py`: Configuration loading, validation, and host management
- `db.py`: PostgreSQL installation, service management, and database operations
- `listing.py`: Database introspection and Rich display formatting
- `sync.py`: Database migration with pg_dump/restore
- `ssh.py`: Remote execution infrastructure
- `cloud.py`: Future cloud provider integrations

## Important Rules

1. **Never hardcode passwords**: Use `.pgpass` file integration
2. **SSH via config shortcuts**: Always use `~/.ssh/config` entries
3. **Comprehensive error messages**: Provide actionable guidance
4. **Progress indicators**: Use Rich components for long operations
5. **Type safety**: Full type hints with Pydantic validation
6. **Cross-platform**: Consider macOS, Linux, and future Windows support