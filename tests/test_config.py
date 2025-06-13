"""Tests for configuration loading and validation."""

import pytest
import tempfile
import yaml
from pathlib import Path
from pydantic import ValidationError

from pgsqlmgr.config import (
    LocalHost,
    SSHHost,
    CloudHost,
    PostgreSQLManagerConfig,
    load_config,
    create_sample_config,
    get_host_config,
    list_hosts,
)


class TestLocalHost:
    """Test LocalHost configuration model."""
    
    def test_valid_local_host(self):
        """Test valid local host configuration."""
        config = LocalHost(user="postgres", password="test123")
        assert config.type == "local"
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.user == "postgres"
        assert config.password == "test123"
    
    def test_local_host_custom_port(self):
        """Test local host with custom port."""
        config = LocalHost(user="postgres", port=5433)
        assert config.port == 5433
    
    def test_local_host_invalid_port(self):
        """Test local host with invalid port."""
        with pytest.raises(ValidationError):
            LocalHost(user="postgres", port=70000)


class TestSSHHost:
    """Test SSHHost configuration model."""
    
    def test_valid_ssh_host(self):
        """Test valid SSH host configuration."""
        config = SSHHost(
            ssh_config="production",
            user="postgres"
        )
        assert config.type == "ssh"
        assert config.ssh_config == "production"
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.user == "postgres"
    
    def test_ssh_host_custom_port(self):
        """Test SSH host with custom PostgreSQL port."""
        config = SSHHost(
            ssh_config="staging",
            user="postgres",
            port=5433
        )
        assert config.ssh_config == "staging"
        assert config.port == 5433


class TestCloudHost:
    """Test CloudHost configuration model."""
    
    def test_valid_cloud_host(self):
        """Test valid cloud host configuration."""
        config = CloudHost(provider="supabase")
        assert config.type == "cloud"
        assert config.provider == "supabase"
        assert config.port == 5432


class TestPostgreSQLManagerConfig:
    """Test main configuration model."""
    
    def test_valid_config(self):
        """Test valid configuration with multiple hosts."""
        config_data = {
            "hosts": {
                "local": {
                    "type": "local", 
                    "user": "postgres"
                },
                "remote": {
                    "type": "ssh",
                    "ssh_config": "remote", 
                    "user": "postgres"
                }
            }
        }
        config = PostgreSQLManagerConfig(**config_data)
        assert len(config.hosts) == 2
        assert "local" in config.hosts
        assert "remote" in config.hosts
    
    def test_empty_hosts_invalid(self):
        """Test that empty hosts configuration is invalid."""
        with pytest.raises(ValidationError):
            PostgreSQLManagerConfig(hosts={})


class TestConfigLoading:
    """Test configuration file loading."""
    
    def test_load_valid_config_file(self):
        """Test loading a valid configuration file."""
        config_data = {
            "hosts": {
                "test": {
                    "type": "local",
                    "user": "postgres"
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)
        
        try:
            config = load_config(config_path)
            assert len(config.hosts) == 1
            assert "test" in config.hosts
        finally:
            config_path.unlink()
    
    def test_load_nonexistent_config_file(self):
        """Test loading a non-existent configuration file."""
        with pytest.raises(FileNotFoundError):
            load_config(Path("/nonexistent/config.yaml"))
    
    def test_create_sample_config(self):
        """Test creating a sample configuration file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.yaml"
            create_sample_config(config_path)
            
            assert config_path.exists()
            
            # Verify the sample config is valid
            config = load_config(config_path)
            assert len(config.hosts) >= 1
    
    def test_get_host_config(self):
        """Test getting configuration for a specific host."""
        config_data = {
            "hosts": {
                "test": {
                    "type": "local",
                    "user": "postgres"
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)
        
        try:
            host_config = get_host_config("test", config_path)
            assert host_config.type == "local"
            assert host_config.user == "postgres"
        finally:
            config_path.unlink()
    
    def test_get_nonexistent_host_config(self):
        """Test getting configuration for a non-existent host."""
        config_data = {
            "hosts": {
                "test": {
                    "type": "local",
                    "user": "postgres"
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)
        
        try:
            with pytest.raises(KeyError):
                get_host_config("nonexistent", config_path)
        finally:
            config_path.unlink()
    
    def test_list_hosts(self):
        """Test listing all configured hosts."""
        config_data = {
            "hosts": {
                "local": {"type": "local", "user": "postgres"},
                "remote": {"type": "ssh", "ssh_config": "remote", "user": "postgres"}
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)
        
        try:
            hosts = list_hosts(config_path)
            assert len(hosts) == 2
            assert "local" in hosts
            assert "remote" in hosts
        finally:
            config_path.unlink() 