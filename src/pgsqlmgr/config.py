"""Configuration loading and validation for PostgreSQL Manager."""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator
from rich.console import Console

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
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Invalid YAML in configuration file: {e}")
    
    if raw_config is None:
        raw_config = {}
    
    return PostgreSQLManagerConfig(**raw_config)


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
            "production": {
                "type": "ssh",
                "ssh_config": "production",
                "host": "localhost",
                "port": 5432,
                "user": "postgres", 
                "password": "production_password",
                "description": "Production server via SSH (uses ~/.ssh/config)"
            },
            "staging": {
                "type": "ssh",
                "ssh_config": "staging",
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "description": "Staging server via SSH (uses ~/.ssh/config)"
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