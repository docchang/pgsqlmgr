# Development Setup Guide

This guide will help you set up the PostgreSQL Manager project for development.

## Prerequisites

- **Python 3.10+** (required)
- **Git** (for version control)
- **PostgreSQL** (for testing, optional but recommended)

## Initial Setup

### 1. Clone the Repository

```bash
git clone https://github.com/docchang/pgsqlmgr.git
cd pgsqlmgr
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install the package in editable mode with development dependencies
pip install -e ".[dev]"
```

This will install:
- **Core dependencies**: `typer`, `rich`, `pydantic`, `pyyaml`, `fabric`, `psycopg2-binary`
- **Development dependencies**: `pytest`, `pytest-cov`, `black`, `ruff`, `mypy`, `types-PyYAML`

### 4. Verify Installation

```bash
# Test that the CLI is working
pgsqlmgr --help
pgsqlmgr --version
```

## Development Workflow

### Code Formatting and Linting

The project uses modern Python tooling for code quality:

```bash
# Format code with Black
black src/ tests/

# Lint code with Ruff
ruff check src/ tests/

# Type checking with MyPy
mypy src/
```

### Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=pgsqlmgr

# Run specific test file
pytest tests/test_config.py

# Run tests with verbose output
pytest -v
```

### Testing the CLI

```bash
# Initialize a sample configuration
pgsqlmgr init-config

# List configured hosts (after editing config)
pgsqlmgr list-hosts

# Show configuration for a specific host
pgsqlmgr show-config local

# Test placeholder commands
pgsqlmgr check-install local
pgsqlmgr sync-db local mydb remote
```

## Project Structure

```
pgsql-manager/
├── src/
│   └── pgsqlmgr/           # Main package
│       ├── __init__.py     # Package initialization
│       ├── main.py         # CLI entry point and commands
│       ├── config.py       # Configuration loading and validation
│       ├── ssh.py          # SSH connection utilities
│       ├── db.py           # Database operations
│       ├── sync.py         # Database synchronization logic
│       └── cloud.py        # Cloud provider integrations
├── tests/                  # Test suite
│   ├── __init__.py
│   ├── test_config.py      # Configuration tests
│   ├── test_ssh.py         # SSH functionality tests
│   └── test_sync.py        # Synchronization tests
├── docs/                   # Documentation
├── pyproject.toml          # Modern packaging configuration
├── README.md               # Project overview
├── .gitignore              # Git ignore patterns
└── DEVELOPMENT.md          # This file
```

## Configuration File

The CLI uses a YAML configuration file at `~/.pgsqlmgr/config.yaml`. You can initialize a sample configuration:

```bash
pgsqlmgr init-config
```

Then edit `~/.pgsqlmgr/config.yaml` to match your setup:

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
    ssh_config: production
    host: localhost
    port: 5432
    user: postgres
    password: production_password
    description: Production server via SSH (uses ~/.ssh/config)
```

**Important**: For SSH hosts, you must configure SSH access in your `~/.ssh/config` file first:

```
# ~/.ssh/config
Host production
    HostName your-server.com
    User deploy
    IdentityFile ~/.ssh/id_rsa
    Port 22

Host staging
    HostName staging.example.com
    User ubuntu
    IdentityFile ~/.ssh/staging_key
    Port 22
```

This allows you to connect with `ssh production` or `ssh staging` directly.

## Development Milestones

We're currently implementing **Milestone 0** (Project Setup & Modern Python Packaging):
- ✅ Modern Python package structure with `src` layout
- ✅ `pyproject.toml` with proper packaging configuration
- ✅ CLI boilerplate with Typer and Rich
- ✅ Configuration loading with Pydantic validation
- ✅ Basic test structure
- ✅ Package modules scaffolding

**Next milestones:**
- **Milestone 1**: Complete config validation and CLI commands
- **Milestone 2**: PostgreSQL installation checking
- **Milestone 3**: Database synchronization between local/SSH hosts
- **Milestone 4**: Database deletion functionality
- **Milestone 5**: `.pgpass` automation

## Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature-name`
3. **Make your changes**
4. **Run tests**: `pytest`
5. **Format code**: `black src/ tests/`
6. **Lint code**: `ruff check src/ tests/`
7. **Type check**: `mypy src/`
8. **Commit changes**: `git commit -am 'Add some feature'`
9. **Push to branch**: `git push origin feature/your-feature-name`
10. **Create Pull Request**

## Debugging

### Common Issues

1. **Import errors**: Make sure you installed the package in editable mode (`pip install -e .`)
2. **CLI not found**: Ensure your virtual environment is activated
3. **Configuration errors**: Check YAML syntax in `~/.pgsqlmgr/config.yaml`

### Debug Mode

You can add debug output to any command by modifying the console output:

```python
# In any module
from rich.console import Console
console = Console()
console.print("[yellow]Debug: This is debug output[/yellow]")
```

## IDE Setup

### VS Code
Recommended extensions:
- Python
- Pylance
- Black Formatter
- Ruff

### PyCharm
- Enable Python support
- Configure Black as external tool
- Set up pytest as test runner

## Environment Variables

You can set these environment variables for development:

```bash
export PGSQLMGR_CONFIG_PATH="./dev-config.yaml"  # Custom config path
export PGSQLMGR_DEBUG="1"                        # Enable debug mode (future)
```

## Next Steps

1. **Test the current implementation**:
   ```bash
   pgsqlmgr init-config
   pgsqlmgr list-hosts
   ```

2. **Run the test suite**:
   ```bash
   pytest -v
   ```

3. **Start implementing Milestone 1** (config validation completion)

4. **Add more comprehensive tests**

5. **Begin SSH functionality implementation**

---

Happy coding! 🚀 