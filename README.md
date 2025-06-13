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
pip install -e .
pgsqlmgr --help
```

## 💻 Usage

### Configuration
Create a configuration file at `~/.pgsqlmgr/config.yaml`:

```yaml
hosts:
  local:
    type: local
    pg_user: postgres
    pg_port: 5432
    pg_host: localhost

  production-server:
    type: ssh
    ssh_alias: prod-server
    pg_user: postgres
    pg_port: 5432

  staging-server:
    type: ssh
    ssh_alias: staging
    pg_user: admin
    pg_port: 5432
```

### Basic Commands
```bash
# List configured hosts
pgsqlmgr list-hosts

# Check PostgreSQL installation
pgsqlmgr check-install production-server

# Install PostgreSQL on remote host
pgsqlmgr install production-server

# Sync database between hosts
pgsqlmgr sync-db local myapp_db production-server

# Generate .pgpass file
pgsqlmgr generate-pgpass

# Delete database (with confirmation)
pgsqlmgr delete-db staging-server old_db
```

## 🛠️ Requirements

- **Python**: 3.10 or higher
- **Local PostgreSQL**: For local database operations
- **SSH Access**: For remote server management (passwordless SSH recommended)
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