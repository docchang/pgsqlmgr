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
    validate_config_file,
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


class TestEnhancedValidation:
    """Test enhanced validation features for Milestone 1."""
    
    def test_validate_config_file_valid(self):
        """Test validating a valid configuration file."""
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
            is_valid, errors = validate_config_file(config_path)
            assert is_valid is True
            assert len(errors) == 0
        finally:
            config_path.unlink()
    
    def test_validate_config_file_invalid_yaml(self):
        """Test validating a file with invalid YAML."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            config_path = Path(f.name)
        
        try:
            is_valid, errors = validate_config_file(config_path)
            assert is_valid is False
            assert len(errors) > 0
            assert "Invalid YAML syntax" in errors[0]
        finally:
            config_path.unlink()
    
    def test_validate_config_file_empty(self):
        """Test validating an empty configuration file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("")
            config_path = Path(f.name)
        
        try:
            is_valid, errors = validate_config_file(config_path)
            assert is_valid is False
            assert len(errors) > 0
            assert "empty" in errors[0].lower()
        finally:
            config_path.unlink()
    
    def test_validate_config_file_missing(self):
        """Test validating a non-existent configuration file."""
        config_path = Path("/nonexistent/config.yaml")
        is_valid, errors = validate_config_file(config_path)
        assert is_valid is False
        assert len(errors) > 0
        assert "not found" in errors[0]
    
    def test_invalid_host_name_characters(self):
        """Test that invalid characters in host names are rejected.""" 
        config_data = {
            "hosts": {
                "test@host": {  # Invalid character @
                    "type": "local",
                    "user": "postgres"
                }
            }
        }
        
        with pytest.raises(ValidationError) as exc_info:
            PostgreSQLManagerConfig(**config_data)
        
        assert "invalid characters" in str(exc_info.value).lower()
    
    def test_host_name_too_long(self):
        """Test that host names longer than 50 characters are rejected."""
        long_name = "a" * 51  # 51 characters
        config_data = {
            "hosts": {
                long_name: {
                    "type": "local",
                    "user": "postgres"
                }
            }
        }
        
        with pytest.raises(ValidationError) as exc_info:
            PostgreSQLManagerConfig(**config_data)
        
        assert "too long" in str(exc_info.value).lower()
    
    def test_valid_host_name_characters(self):
        """Test that valid host names are accepted."""
        config_data = {
            "hosts": {
                "test-host_123": {  # Valid characters
                    "type": "local",
                    "user": "postgres"
                }
            }
        }
        
        # Should not raise an exception
        config = PostgreSQLManagerConfig(**config_data)
        assert "test-host_123" in config.hosts
    
    def test_enhanced_yaml_error_messages(self):
        """Test that YAML errors include line and column information."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            # Write invalid YAML with specific line/column error
            f.write("hosts:\n  test:\n    type: local\n    user: postgres\n    invalid: [unclosed")
            config_path = Path(f.name)
        
        try:
            with pytest.raises(yaml.YAMLError) as exc_info:
                load_config(config_path)
            
            error_msg = str(exc_info.value)
            # Should contain line information
            assert "line" in error_msg or "column" in error_msg
        finally:
            config_path.unlink()
    
    def test_enhanced_validation_error_messages(self):
        """Test that validation errors provide detailed field information."""
        config_data = {
            "hosts": {
                "test": {
                    "type": "local",
                    # Missing required 'user' field
                    "port": 5432
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)
        
        try:
            with pytest.raises(ValueError) as exc_info:
                load_config(config_path)
            
            error_msg = str(exc_info.value)
            # Should contain field path information
            assert "hosts -> test -> user" in error_msg or "user" in error_msg
        finally:
            config_path.unlink() 