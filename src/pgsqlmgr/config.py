"""Configuration loading and validation for PostgreSQL Manager."""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator, ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

# Configuration file paths
DEFAULT_CONFIG_DIR = Path.home() / ".pgsqlmgr"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.yaml"


class LocalHost(BaseModel):
    """Configuration for a local PostgreSQL instance."""
    
    type: Literal["local"] = "local"
    host: str = "localhost"
    port: int = Field(default=5432, ge=1, le=65535)
    user: str
    password: Optional[str] = None
    database: Optional[str] = None
    description: Optional[str] = None


class SSHHost(BaseModel):
    """Configuration for a remote PostgreSQL instance via SSH."""
    
    type: Literal["ssh"] = "ssh"
    ssh_config: str  # SSH config shortcut name (e.g., 'production', 'staging')
    host: str = "localhost"  # PostgreSQL host on remote server (usually localhost)
    port: int = Field(default=5432, ge=1, le=65535)
    user: str
    password: Optional[str] = None
    database: Optional[str] = None
    description: Optional[str] = None
    
    @field_validator('ssh_config')
    @classmethod
    def validate_ssh_config(cls, v):
        """Validate SSH config shortcut exists in ~/.ssh/config."""
        if v is not None:
            # Check if SSH config entry exists
            ssh_config_path = Path.home() / ".ssh" / "config"
            if ssh_config_path.exists():
                with open(ssh_config_path, 'r') as f:
                    config_content = f.read()
                    # Look for "Host <shortcut>" entry
                    if f"Host {v}" not in config_content:
                        console.print(f"[yellow]⚠️  SSH config entry 'Host {v}' not found in ~/.ssh/config[/yellow]")
                        console.print(f"[yellow]   Add this entry to ~/.ssh/config to use SSH connection[/yellow]")
            else:
                console.print(f"[yellow]⚠️  No ~/.ssh/config file found for SSH config '{v}'[/yellow]")
                console.print(f"[yellow]   Create ~/.ssh/config with 'Host {v}' entry for SSH connection[/yellow]")
        return v


class CloudHost(BaseModel):
    """Configuration for a cloud PostgreSQL instance (future use)."""
    
    type: Literal["cloud"] = "cloud"
    provider: str  # e.g., "supabase", "aws", "gcp"
    connection_string: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = Field(default=5432, ge=1, le=65535)
    user: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None
    description: Optional[str] = None
    # Provider-specific settings would go here


# Union type for all host configurations
HostConfig = Union[LocalHost, SSHHost, CloudHost]


class PostgreSQLManagerConfig(BaseModel):
    """Main configuration model for PostgreSQL Manager."""
    
    hosts: Dict[str, HostConfig] = Field(default_factory=dict)
    
    @field_validator('hosts')
    @classmethod
    def validate_hosts_not_empty(cls, v):
        """Ensure at least one host is configured."""
        if not v:
            raise ValueError("At least one host must be configured")
        return v
    
    @field_validator('hosts')
    @classmethod
    def validate_host_names(cls, v):
        """Validate host names contain only valid characters."""
        for host_name in v.keys():
            if not re.match(r'^[a-zA-Z0-9_-]+$', host_name):
                raise ValueError(f"Host name '{host_name}' contains invalid characters. Use only letters, numbers, underscore, and dash.")
            if len(host_name) > 50:
                raise ValueError(f"Host name '{host_name}' is too long (max 50 characters)")
        return v


def validate_config_file(config_path: Optional[Path] = None) -> tuple[bool, List[str]]:
    """
    Validate configuration file and return validation results.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_FILE
    
    errors = []
    
    # Check if file exists
    if not config_path.exists():
        errors.append(f"Configuration file not found: {config_path}")
        return False, errors
    
    # Check if file is readable
    try:
        with open(config_path, 'r') as f:
            raw_config = yaml.safe_load(f)
    except PermissionError:
        errors.append(f"Permission denied reading configuration file: {config_path}")
        return False, errors
    except yaml.YAMLError as e:
        errors.append(f"Invalid YAML syntax: {e}")
        return False, errors
    except Exception as e:
        errors.append(f"Error reading configuration file: {e}")
        return False, errors
    
    # Check if YAML is empty
    if raw_config is None:
        errors.append("Configuration file is empty")
        return False, errors
    
    # Validate against Pydantic model
    try:
        PostgreSQLManagerConfig(**raw_config)
    except ValidationError as e:
        for error in e.errors():
            field_path = " -> ".join(str(x) for x in error['loc'])
            errors.append(f"Validation error in {field_path}: {error['msg']}")
    except Exception as e:
        errors.append(f"Configuration validation error: {e}")
    
    return len(errors) == 0, errors


def load_config(config_path: Optional[Path] = None) -> PostgreSQLManagerConfig:
    """
    Load and validate configuration from YAML file.
    
    Args:
        config_path: Path to configuration file (defaults to ~/.pgsqlmgr/config.yaml)
        
    Returns:
        Validated configuration object
        
    Raises:
        FileNotFoundError: If configuration file doesn't exist
        yaml.YAMLError: If YAML is malformed
        pydantic.ValidationError: If configuration is invalid
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_FILE
    
    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}\n"
            f"Create a configuration file at {config_path} or run: pgsqlmgr init-config"
        )
    
    try:
        with open(config_path, 'r') as f:
            raw_config = yaml.safe_load(f)
    except PermissionError as e:
        raise PermissionError(f"Permission denied reading configuration file: {config_path}")
    except yaml.YAMLError as e:
        # Enhanced YAML error messages
        line_info = ""
        if hasattr(e, 'problem_mark'):
            mark = e.problem_mark
            line_info = f" (line {mark.line + 1}, column {mark.column + 1})"
        raise yaml.YAMLError(f"Invalid YAML syntax in configuration file{line_info}: {e}")
    
    if raw_config is None:
        raise ValueError("Configuration file is empty")
    
    try:
        return PostgreSQLManagerConfig(**raw_config)
    except ValidationError as e:
        # Enhanced validation error messages
        error_messages = []
        for error in e.errors():
            field_path = " -> ".join(str(x) for x in error['loc'])
            error_messages.append(f"  • {field_path}: {error['msg']}")
        
        raise ValueError(
            f"Configuration validation failed:\n" + "\n".join(error_messages)
        )


def create_sample_config(config_path: Optional[Path] = None) -> None:
    """
    Create a sample configuration file.
    
    Args:
        config_path: Path where to create the configuration file
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_FILE
    
    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    sample_config = {
        "hosts": {
            "local": {
                "type": "local",
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "your_password_here",
                "description": "Local PostgreSQL instance"
            },
            "genesis": {
                "type": "ssh",
                "ssh_config": "genesis",
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "genesis_password",
                "description": "Genesis server via SSH"
            },
            "skynet": {
                "type": "ssh",
                "ssh_config": "skynet",
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "description": "Skynet server via SSH"
            }
        }
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(sample_config, f, default_flow_style=False, indent=2)
    
    console.print(f"[green]✅ Sample configuration created at: {config_path}[/green]")
    console.print("[yellow]⚠️  Please edit the configuration file to match your setup[/yellow]")


def get_host_config(host_name: str, config_path: Optional[Path] = None) -> HostConfig:
    """
    Get configuration for a specific host.
    
    Args:
        host_name: Name of the host to get configuration for
        config_path: Path to configuration file
        
    Returns:
        Host configuration object
        
    Raises:
        KeyError: If host is not found in configuration
    """
    config = load_config(config_path)
    
    if host_name not in config.hosts:
        available_hosts = list(config.hosts.keys())
        raise KeyError(
            f"Host '{host_name}' not found in configuration. "
            f"Available hosts: {', '.join(available_hosts)}"
        )
    
    return config.hosts[host_name]


def list_hosts(config_path: Optional[Path] = None) -> List[str]:
    """
    List all configured host names.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        List of host names
    """
    config = load_config(config_path)
    return list(config.hosts.keys()) 