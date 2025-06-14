# PostgreSQL Manager (pgsqlmgr)

A modern CLI tool for managing PostgreSQL instances across local and remote environments with seamless database synchronization capabilities.

## 🎯 Overview

PostgreSQL Manager (`pgsqlmgr`) is a Python-based command-line tool designed to simplify PostgreSQL database management across multiple environments. Whether you're working with local installations or remote servers via SSH, this tool provides a unified interface for common database operations.

## ✨ Features

### ✅ Implemented Features (Current)
- 🔧 **Installation Management**: Check and install PostgreSQL on local and remote (SSH) hosts
- 🔄 **Database Synchronization**: Seamless sync between local and SSH instances using `pg_dump`/`pg_restore`
- 🗑️ **Database Deletion**: Safe database deletion with confirmation prompts and backup options
- ⚙️ **Configuration Management**: Unified YAML configuration with inheritance-based host types
- 📊 **Database Listing**: List all databases with sizes, owners, and access privileges
- 📋 **Table Listing**: List tables across databases with schema, size, and row count information
- 🔍 **Table Content Preview**: View actual table data (10 records per table, integrated with table listing)
- 👥 **User Management**: List PostgreSQL users/roles with detailed permission information
- 🎨 **Rich CLI Interface**: Beautiful command-line interface with colored tables and progress indicators
- 🔐 **Credential Management**: Support for password-based authentication
- 🏗️ **Type-Safe Configuration**: Enum-based host types with inheritance for maintainability
- ✅ **Configuration Validation**: Comprehensive config file validation with detailed error reporting

### Phase 2 (v2.0) - Future Enhancements
- ☁️ **Cloud Integration**: Support for Supabase, AWS RDS, and other cloud providers
- 🚀 **Advanced Sync Options**: Incremental sync, schema-only sync, and more
- 📊 **Monitoring Dashboard**: Optional web interface for database monitoring
- 🔐 **Advanced Security**: `.pgpass` file generation and SSH key management

## 🏗️ Project Status

**Current Status**: 🚀 **Active Development - Core Features Complete**

The project has implemented all core database management functionality including listing, synchronization, and deletion with comprehensive testing coverage (133 tests passing). The foundation is solid with modern Python packaging standards and robust error handling.

**Recent Additions**:
- ✅ **Database Deletion Functionality**: Safe deletion with confirmation prompts and backup options
- ✅ Complete listing functionality (databases, tables, users)
- ✅ Table content preview with intelligent column styling
- ✅ Simple preview option (--preview for 10 records)
- ✅ Rich table displays with color coding
- ✅ Inheritance-based configuration system
- ✅ Type-safe enum system for host types
- ✅ Comprehensive test suite (133 tests passing)

## 🚀 Installation

### End Users (when v1.0 is released)
```bash
pip install pgsql-manager
pgsqlmgr --help
```

### Developers

#### Standard Setup
```bash
git clone https://github.com/docchang/pgsqlmgr.git
cd pgsqlmgr
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e . --use-pep517
pgsqlmgr --help
```

#### Apple Silicon (M1/M2/M3) Setup
If you encounter cryptography/hashlib errors on Apple Silicon:

**Quick Setup (Recommended)**:
```bash
git clone https://github.com/docchang/pgsqlmgr.git
cd pgsqlmgr
chmod +x setup_arm64.sh
./setup_arm64.sh
```

**Manual Setup**:
```bash
git clone https://github.com/docchang/pgsqlmgr.git
cd pgsqlmgr
source simple-fix/setup_arm64_homebrew.sh
create_arm64_venv .venv
source .venv/bin/activate
pip install -e .
pgsqlmgr --help
```

## 🚀 Quick Start

1. **Install the package** (developers):
   ```bash
   git clone https://github.com/docchang/pgsqlmgr.git
   cd pgsqlmgr
   python -m venv .venv && source .venv/bin/activate
   pip install -e .
   ```

2. **Set up SSH config** (for remote hosts):
   ```bash
   # Add entries to ~/.ssh/config
   Host production
       HostName your-server.com
       User your-username
       IdentityFile ~/.ssh/id_rsa
   ```

3. **Initialize configuration**:
   ```bash
   pgsqlmgr init-config
   ```

4. **List your hosts**:
   ```bash
   pgsqlmgr list-hosts
   ```

5. **Explore your databases**:
   ```bash
   pgsqlmgr list-databases localhost
   pgsqlmgr list-tables localhost --database myapp_db
   pgsqlmgr list-users localhost
   ```

## 💻 Usage

### Prerequisites

**SSH Configuration**: Before using SSH features, configure your `~/.ssh/config` file:

```bash
# ~/.ssh/config
Host production
    HostName production.example.com
    User admin
    IdentityFile ~/.ssh/id_rsa

Host staging
    HostName staging.example.com
    User deploy
    IdentityFile ~/.ssh/id_rsa
```

### Configuration

Initialize your configuration:
```bash
pgsqlmgr init-config
```

Or manually create `~/.pgsqlmgr/config.yaml`:

```yaml
hosts:
  local:
    type: local
    host: localhost
    port: 5432
    superuser: postgres
    password: your_password_here
    description: Local PostgreSQL instance

  production:
    type: ssh
    ssh_config: production  # References ~/.ssh/config entry
    host: localhost
    port: 5432
    superuser: postgres
    password: production_password
    description: Production server via SSH

  staging:
    type: ssh
    ssh_config: staging  # References ~/.ssh/config entry
    host: localhost
    port: 5432
    superuser: admin
    password: staging_password
    description: Staging server via SSH

  cloud_db:
    type: cloud
    host: db.example.com
    port: 5432
    superuser: admin
    password: cloud_password
    description: Cloud PostgreSQL instance
```

### Available Commands

#### Core Management Commands
```bash
# Show help and available commands
pgsqlmgr --help

# Show version information
pgsqlmgr --version

# Initialize sample configuration file
pgsqlmgr init-config

# List all configured hosts with connection details
pgsqlmgr list-hosts

# Show detailed configuration for a specific host
pgsqlmgr show-config <host_name>
pgsqlmgr show-config production

# Validate configuration file
pgsqlmgr validate-config
```

#### Database Listing Commands
```bash
# List user databases (excludes system databases)
pgsqlmgr list-databases localhost

# List all databases including system databases
pgsqlmgr list-databases localhost --include-system

# List tables in a specific database
pgsqlmgr list-tables localhost --database myapp_db

# List tables with content preview (10 records per table)
pgsqlmgr list-tables localhost --database myapp_db --preview

# List tables across all user databases with preview
pgsqlmgr list-tables localhost --preview

# List tables including system tables
pgsqlmgr list-tables localhost --include-system

# Preview specific table content (standalone command, 10 records)
pgsqlmgr preview-table localhost myapp_db users

# List PostgreSQL users and their permissions
pgsqlmgr list-users localhost
```

#### Installation & Service Commands
```bash
# Check PostgreSQL installation status
pgsqlmgr check-install production

# Install PostgreSQL on a host
pgsqlmgr install production

# Start PostgreSQL service
pgsqlmgr start-service production
```

#### Database Synchronization Commands
```bash
# Sync database between hosts
pgsqlmgr sync-db source_host database_name destination_host

# Sync with options
pgsqlmgr sync-db local myapp_db production --drop-existing --auto-install

# Schema-only sync
pgsqlmgr sync-db local myapp_db staging --schema-only

# Data-only sync
pgsqlmgr sync-db local myapp_db staging --data-only
```

#### Database Deletion Commands
```bash
# Delete database with confirmation prompt
pgsqlmgr delete-db localhost old_database

# Delete database with backup before deletion
pgsqlmgr delete-db localhost old_database --backup

# Delete database with custom backup location
pgsqlmgr delete-db localhost old_database --backup --backup-path /backups/

# Force delete without confirmation (for automation)
pgsqlmgr delete-db localhost old_database --force

# Delete database on SSH host with backup
pgsqlmgr delete-db production old_database --backup
```

#### Command Options
Most commands support these global options:
```bash
# Use custom configuration file location
pgsqlmgr --config /path/to/config.yaml list-hosts

# Get help for specific commands
pgsqlmgr show-config --help
pgsqlmgr list-databases --help
```

#### Example Output

**List Databases:**
```bash
$ pgsqlmgr list-databases localhost
📊 Listing databases on localhost...
                           Databases on localhost                            
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃ Database Name ┃ Owner     ┃ Encoding  ┃ Size    ┃ Access Privileges ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━┩
│ myapp_db      │ postgres  │ UTF8      │ 15 MB   │ None              │
│ analytics     │ postgres  │ UTF8      │ 128 MB  │ None              │
│ staging_db    │ admin     │ UTF8      │ 5 MB    │ None              │
└───────────────┴───────────┴───────────┴─────────┴───────────────────┘
```

**List Tables:**
```bash
$ pgsqlmgr list-tables localhost --database myapp_db
📋 Listing tables in database 'myapp_db' on localhost...
                    Tables in database 'myapp_db' on localhost                     
┏━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Schema  ┃ Table Name   ┃ Owner     ┃ Size     ┃ Est. Rows ┃
┡━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━┩
│ public  │ users        │ postgres  │ 1024 kB  │ 1500      │
│ public  │ orders       │ postgres  │ 2048 kB  │ 3200      │
│ public  │ products     │ postgres  │ 512 kB   │ 450       │
└─────────┴──────────────┴───────────┴──────────┴───────────┘
```

**List Users:**
```bash
$ pgsqlmgr list-users localhost
👥 Listing users on localhost...
                          PostgreSQL Users on localhost                           
┏━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Username   ┃ Superuser  ┃ Create Roles ┃ Create DBs ┃ Can Login ┃ Connection Limit  ┃ Valid Until ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ postgres   │ ✓          │ ✓            │ ✓          │ ✓         │ Unlimited         │ Never       │
│ app_user   │ ✗          │ ✗            │ ✗          │ ✓         │ 10                │ Never       │
│ readonly   │ ✗          │ ✗            │ ✗          │ ✓         │ 5                 │ Never       │
└────────────┴────────────┴──────────────┴────────────┴───────────┴───────────────────┴─────────────┘
```

**Database Deletion:**
```bash
$ pgsqlmgr delete-db localhost old_database --backup
🗑️  Database Deletion Request
   Host: localhost
   Database: old_database
🔍 Gathering database information...

📊 Database Information:
Name                old_database
Owner               postgres
Size                25 MB
Encoding            UTF8
Active Connections  0

💾 Creating backup before deletion...
✅ Backup created: old_database_backup_20241220_143022.sql

⚠️  WARNING: This will permanently delete database 'old_database' from host 'localhost'!
💾 Backup saved to: old_database_backup_20241220_143022.sql
This action cannot be undone!

Are you sure you want to delete database 'old_database'? [y/N]: y

🗑️  Deleting database 'old_database'...
╭─────────────────────────────────────────── Deletion Complete ────────────────────────────────────────────╮
│ ✅ Database 'old_database' deleted successfully!                                                         │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────╯
💾 Backup available at: old_database_backup_20241220_143022.sql
```

**List Hosts:**
```bash
$ pgsqlmgr list-hosts
                                            Configured Hosts                                             
┏━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Host Name  ┃ Type  ┃ Connection                      ┃ Description                                    ┃
┡━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ local      │ local │ localhost:5432                  │ Local PostgreSQL instance                      │
│ production │ ssh   │ ssh production → localhost:5432 │ Production server via SSH (uses ~/.ssh/config) │
│ staging    │ ssh   │ ssh staging → localhost:5432    │ Staging server via SSH (uses ~/.ssh/config)    │
│ cloud_db   │ cloud │ db.example.com:5432             │ Cloud PostgreSQL instance                       │
└────────────┴───────┴─────────────────────────────────┴────────────────────────────────────────────────┘
```

#### Future Commands (Coming Soon)
```bash
# Generate .pgpass file
pgsqlmgr generate-pgpass
```

## 🛠️ Requirements

- **Python**: 3.10 or higher
- **Local PostgreSQL**: For local database operations
- **SSH Configuration**: Pre-configured `~/.ssh/config` entries for remote servers
- **SSH Key Authentication**: Passwordless SSH access to remote hosts
- **Operating System**: 
  - macOS (primary development platform)
  - Linux (Ubuntu/Debian for remote servers)
  - Windows (planned support)

## 📖 Documentation

- [Design Document](docs/design/PostgreSQL%20Manager%20Design.md) - Technical architecture and specifications
- [Development Milestones](docs/design/PostgreSQL%20Manager%20Milestones.md) - Detailed development roadmap

## 🧪 Testing

The project maintains comprehensive test coverage:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/pgsqlmgr

# Run specific test modules
pytest tests/test_listing.py -v
pytest tests/test_config.py -v
```

**Current Test Stats**: 133 tests passing, 13 skipped (integration tests)

## 🤝 Contributing

We welcome contributions! This project follows modern Python development practices:

### Development Setup
1. Fork the repository
2. Create a virtual environment: `python -m venv .venv`
3. Activate it: `source .venv/bin/activate`
4. Install in development mode: `pip install -e .`
5. Install development dependencies: `pip install -e ".[dev]"`
6. Run tests: `pytest`

### Code Standards
- **Formatting**: We use `black` and `ruff`
- **Type Checking**: `mypy` for type safety
- **Testing**: `pytest` with comprehensive coverage
- **Documentation**: Keep docs updated with changes

### Project Structure
```
pgsql-manager/
├── src/
│   └── pgsqlmgr/           # Main package
│       ├── config.py       # Configuration management with inheritance
│       ├── listing.py      # Database listing functionality
│       ├── main.py         # CLI interface
│       ├── db.py          # Database operations
│       ├── sync.py        # Database synchronization
│       └── ssh.py         # SSH operations
├── tests/                  # Comprehensive test suite
├── docs/                   # Documentation
├── pyproject.toml          # Modern Python packaging
└── README.md               # This file
```

## 🎯 Core Principles

- **Simplicity**: Easy to install, configure, and use
- **Safety**: Confirmation prompts for destructive operations
- **Modern**: Following 2025 Python packaging best practices
- **Reliable**: Comprehensive testing and error handling
- **Beautiful**: Rich CLI interface with colored output
- **Type-Safe**: Full type hints and enum-based configuration
- **Open**: MIT licensed and open-source

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋‍♂️ Support

- **Issues**: [GitHub Issues](https://github.com/docchang/pgsqlmgr/issues)
- **Discussions**: [GitHub Discussions](https://github.com/docchang/pgsqlmgr/discussions)

---

**Note**: This project is actively under development with core features implemented and tested. The listing functionality is complete and ready for use. See our [milestones](docs/design/PostgreSQL%20Manager%20Milestones.md) for upcoming features. 