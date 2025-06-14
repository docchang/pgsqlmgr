#!/bin/bash
# Permanent ARM64 Homebrew Environment Setup
# This script ensures complete ARM64 library isolation on Apple Silicon Macs

set -e

echo "🍺 Setting up ARM64 Homebrew Environment for Apple Silicon"
echo "=================================================="

# Verify we're on Apple Silicon
if [ "$(uname -m)" != "arm64" ]; then
    echo "❌ This script is designed for Apple Silicon Macs (arm64)"
    echo "   Current architecture: $(uname -m)"
    exit 1
fi

# Check for ARM64 Homebrew
if [ ! -f "/opt/homebrew/bin/brew" ]; then
    echo "❌ ARM64 Homebrew not found at /opt/homebrew/"
    echo "   Please install Homebrew first:"
    echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    exit 1
fi

echo "✅ ARM64 Homebrew found"

# Set up environment variables
export HOMEBREW_PREFIX="/opt/homebrew"
export HOMEBREW_CELLAR="/opt/homebrew/Cellar"
export HOMEBREW_REPOSITORY="/opt/homebrew"

# Critical: Force ARM64 architecture
export ARCHFLAGS="-arch arm64"
export CFLAGS="-arch arm64"
export CXXFLAGS="-arch arm64"

# Override PATH to exclude Intel paths during builds
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/bin:/bin:/usr/sbin:/sbin"

# Force ARM64 library and include paths
export LDFLAGS="-L/opt/homebrew/lib"
export CPPFLAGS="-I/opt/homebrew/include"
export PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig:/opt/homebrew/share/pkgconfig"

# Critical: Override library search paths
export LIBRARY_PATH="/opt/homebrew/lib"
export C_INCLUDE_PATH="/opt/homebrew/include"
export CPLUS_INCLUDE_PATH="/opt/homebrew/include"

# Dynamic linker configuration
export DYLD_LIBRARY_PATH="/opt/homebrew/lib"
unset DYLD_FALLBACK_LIBRARY_PATH

# Python configuration
export PYTHON_CONFIGURE_OPTS="--enable-shared --enable-optimizations"

# Function to create isolated virtual environment
create_arm64_venv() {
    local venv_name="$1"
    if [ -z "$venv_name" ]; then
        echo "Usage: create_arm64_venv <venv_name>"
        return 1
    fi
    
    echo "🔧 Creating ARM64 isolated virtual environment: $venv_name"
    
    # Use ARM64 Python
    /opt/homebrew/bin/python3 -m venv "$venv_name"
    
    echo "✅ Virtual environment '$venv_name' created with ARM64 isolation"
    echo "   Activate with: source $venv_name/bin/activate"
}

# Export the function
export -f create_arm64_venv

echo "✅ ARM64 Homebrew environment configured successfully"
echo ""
echo "🔧 Available commands:"
echo "   create_arm64_venv <name>  - Create ARM64 isolated virtual environment"
echo ""
echo "📋 Environment summary:"
echo "   HOMEBREW_PREFIX: $HOMEBREW_PREFIX"
echo "   PATH: $PATH"
echo "   LDFLAGS: $LDFLAGS"
echo "   LIBRARY_PATH: $LIBRARY_PATH"
echo ""