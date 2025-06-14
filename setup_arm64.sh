#!/bin/bash
# Quick setup script for pgsql-manager on Apple Silicon
# This script sets up ARM64 environment and installs the package

set -e

echo "🚀 Setting up pgsql-manager for Apple Silicon (ARM64)"
echo "====================================================="

# Check if we're on Apple Silicon
if [ "$(uname -m)" != "arm64" ]; then
    echo "❌ This script is for Apple Silicon Macs only"
    echo "   Use standard setup: python -m venv .venv && source .venv/bin/activate && pip install -e ."
    exit 1
fi

# Set up ARM64 environment
echo "🔧 Configuring ARM64 environment..."
source simple-fix/setup_arm64_homebrew.sh

# Create ARM64 virtual environment
echo "🔧 Creating ARM64 virtual environment..."
create_arm64_venv .venv

# Activate and install
echo "📦 Installing pgsql-manager..."
source .venv/bin/activate
pip install -e .

# Test installation
echo "✅ Testing installation..."
pgsqlmgr --version

echo ""
echo "🎉 Setup complete!"
echo ""
echo "To use pgsql-manager:"
echo "  source .venv/bin/activate"
echo "  pgsqlmgr --help"
echo ""
echo "To make ARM64 environment permanent:"
echo "  echo 'source $(pwd)/simple-fix/setup_arm64_homebrew.sh' >> ~/.zshrc" 