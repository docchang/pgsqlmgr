# PostgreSQL Manager (pgsqlmgr)

A modern CLI tool for managing PostgreSQL instances across local and remote environments with seamless database synchronization capabilities.

## 🎯 Overview

PostgreSQL Manager (`pgsqlmgr`) is a Python-based command-line tool designed to simplify PostgreSQL database management across multiple environments. Whether you're working with local installations or remote servers via SSH, this tool provides a unified interface for common database operations.

## ✨ Features

### Phase 1 (v1.0) - Core Functionality
- 🔧 **Installation Management**: Check and install PostgreSQL on local and remote (SSH) hosts
- 🔄 **Database Synchronization**: Seamless sync between local and SSH instances using `pg_dump`/`pg_restore`
- ⚙️ **Configuration Management**: Unified YAML configuration for all your PostgreSQL hosts
- 🔐 **Credential Automation**: Automatic `.pgpass` file generation and management
- 🗑️ **Safe Database Deletion**: Controlled database removal with confirmation prompts
- 🎨 **Rich CLI Interface**: Beautiful command-line interface with progress indicators

### Phase 2 (v2.0) - Future Enhancements
- ☁️ **Cloud Integration**: Support for Supabase, AWS RDS, and other cloud providers
- 🚀 **Advanced Sync Options**: Incremental sync, schema-only sync, and more
- 📊 **Monitoring Dashboard**: Optional web interface for database monitoring

## 🏗️ Project Status

**Current Status**: 🚧 **In Development**

This project is currently in the design and early development phase. We're following modern Python packaging standards and building a robust foundation for PostgreSQL management.

**Roadmap**: See our [Milestones](docs/design/PostgreSQL%20Manager%20Milestones.md) for detailed development timeline.

## 🚀 Installation

### End Users (when v1.0 is released)
```bash
pip install pgsql-manager
pgsqlmgr --help
```

### Developers
```bash
git clone https://github.com/docchang/pgsqlmgr.git
cd pgsqlmgr
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e . --use-pep517
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

5. **View host details**:
   ```bash
   pgsqlmgr show-config production
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
    user: postgres
    password: your_password_here
    description: Local PostgreSQL instance

  production:
    type: ssh
    ssh_config: production  # References ~/.ssh/config entry
    host: localhost
    port: 5432
    user: postgres
    password: production_password
    description: Production server via SSH

  staging:
    type: ssh
    ssh_config: staging  # References ~/.ssh/config entry
    host: localhost
    port: 5432
    user: admin
    password: staging_password
    description: Staging server via SSH
```

### Available Commands

#### Core Commands
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
pgsqlmgr show-config local
```

#### Command Options
Most commands support these global options:
```bash
# Use custom configuration file location
pgsqlmgr --config /path/to/config.yaml list-hosts

# Get help for specific commands
pgsqlmgr show-config --help
pgsqlmgr list-hosts --help
```

#### Example Output

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
└────────────┴───────┴─────────────────────────────────┴────────────────────────────────────────────────┘
```

**Show Config:**
```bash
$ pgsqlmgr show-config production
╭─────── Host Configuration: production ────────╮
│ Type: ssh                                      │
│ SSH Command: ssh production                    │
│ Database Host: localhost:5432                  │
│ Database User: postgres                        │
│ Description: Production server via SSH         │
╰────────────────────────────────────────────────╯
```

**Help Output:**
```bash
$ pgsqlmgr --help

Usage: pgsqlmgr [OPTIONS] COMMAND [ARGS]...

PostgreSQL Manager - Manage PostgreSQL instances across local and remote environments

Commands:
  init-config       Initialize a sample configuration file.
  list-hosts        List all configured PostgreSQL hosts.
  show-config       Show configuration for a specific host.
  check-install     Check PostgreSQL installation on a host.
  install           Install PostgreSQL on a host.
  sync-db           Sync a database between two hosts.
  delete-db         Delete a database from a host.
  generate-pgpass   Generate .pgpass file from configuration.
```

#### Future Commands (Coming in v1.0)
```bash
# Check PostgreSQL installation
pgsqlmgr check-install production

# Install PostgreSQL on remote host
pgsqlmgr install production

# Sync database between hosts
pgsqlmgr sync-db local myapp_db production

# Generate .pgpass file
pgsqlmgr generate-pgpass

# Delete database (with confirmation)
pgsqlmgr delete-db staging old_db
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
├── tests/                  # Test suite
├── docs/                   # Documentation
├── pyproject.toml          # Modern Python packaging
└── README.md               # This file
```

## 🎯 Core Principles

- **Simplicity**: Easy to install, configure, and use
- **Safety**: Confirmation prompts for destructive operations
- **Modern**: Following 2025 Python packaging best practices
- **Reliable**: Comprehensive testing and error handling
- **Open**: MIT licensed and open-source

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋‍♂️ Support

- **Issues**: [GitHub Issues](https://github.com/docchang/pgsqlmgr/issues)
- **Discussions**: [GitHub Discussions](https://github.com/docchang/pgsqlmgr/discussions)

---

**Note**: This project is actively under development. APIs and features may change before the v1.0 release. See our [milestones](docs/design/PostgreSQL%20Manager%20Milestones.md) for current progress. 