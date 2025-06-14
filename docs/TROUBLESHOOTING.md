# Troubleshooting Guide

This document covers common issues and their solutions when using PostgreSQL Manager.

## Python Hash Algorithm Errors (blake2b/blake2s)

### Problem Description

When running PostgreSQL Manager, you may encounter error messages like:

```
ERROR:root:code for hash blake2b was not found.
Traceback (most recent call last):
  File "/Users/user/.pyenv/versions/3.11.9/lib/python3.11/hashlib.py", line 307, in <module>
    globals()[__func_name] = __get_hash(__func_name)
                             ^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/user/.pyenv/versions/3.11.9/lib/python3.11/hashlib.py", line 129, in __get_openssl_constructor
    return __get_builtin_constructor(name)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/user/.pyenv/versions/3.11.9/lib/python3.11/hashlib.py", line 123, in __get_builtin_constructor
    raise ValueError('unsupported hash type ' + name)
ValueError: unsupported hash type blake2b
```

### Why Homebrew Doesn't Fully Solve This

You're absolutely correct that **Homebrew is designed to provide isolated environments** and should resolve these issues. Here's what's happening and why it's not working perfectly:

#### What Homebrew Does Right

1. **Separate Installation Paths**:
   - ARM64 Homebrew: `/opt/homebrew/` (isolated from system)
   - Intel Homebrew: `/usr/local/` (unfortunately conflicts with system paths)

2. **Architecture-Specific Builds**:
   - Compiles packages for the correct architecture
   - Provides proper linking flags
   - Sets up isolated library paths

3. **Environment Management**:
   ```bash
   # Homebrew sets these automatically
   export HOMEBREW_PREFIX="/opt/homebrew"
   export HOMEBREW_CELLAR="/opt/homebrew/Cellar"
   export PATH="/opt/homebrew/bin:$PATH"
   export LDFLAGS="-L/opt/homebrew/lib"
   export CPPFLAGS="-I/opt/homebrew/include"
   ```

#### Where the Isolation Breaks Down

1. **pyenv/python-build Behavior**:
   ```bash
   # python-build searches these paths in order:
   /usr/local/lib          # ❌ System x86_64 libraries found first
   /opt/homebrew/lib       # ✅ ARM64 libraries (but searched second)
   /usr/lib                # System libraries
   ```

2. **Compiler Search Paths**:
   - Even with Homebrew's `LDFLAGS`, the compiler still searches standard system paths
   - `/usr/local/lib` is a **standard system path** that compilers check automatically
   - This happens **before** Homebrew's custom flags are applied

3. **Apple's Design Choice**:
   - Apple intentionally put Intel libraries in `/usr/local/` for Rosetta compatibility
   - This conflicts with the traditional Unix convention that Homebrew relies on
   - `/usr/local/` was supposed to be for "local" (user) installations, but Apple uses it for system compatibility

#### The Specific Problem with Blake2

```bash
# What should happen (Homebrew's intention):
pyenv install 3.11.9
# → Uses /opt/homebrew/lib/libb2.dylib (ARM64)
# → Builds _blake2 extension successfully

# What actually happens:
pyenv install 3.11.9
# → Finds /usr/local/lib/libintl.dylib (x86_64) first
# → Tries to link ARM64 Python with x86_64 libraries
# → _blake2 extension build fails
# → Python builds successfully but blake2 is broken
```

#### Why This is Hard for Homebrew to Fix

1. **System Path Priority**: `/usr/local/` is hardcoded into many build systems as a standard search path
2. **Apple's Rosetta Design**: Apple needs Intel libraries in `/usr/local/` for compatibility
3. **Build Tool Limitations**: Many build tools (including Python's) don't fully respect custom library paths
4. **Backward Compatibility**: Changing this would break existing software

### Homebrew's Partial Solutions

Homebrew **does** provide some workarounds:

#### 1. Keg-Only Packages
```bash
# Some packages are "keg-only" to avoid conflicts
brew install openssl@3  # Installs to /opt/homebrew/opt/openssl@3/
# Not symlinked to /opt/homebrew/lib to avoid conflicts
```

#### 2. Environment Variables
```bash
# Homebrew provides these for manual use:
export PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig"
export LDFLAGS="-L/opt/homebrew/lib"
export CPPFLAGS="-I/opt/homebrew/include"
```

#### 3. Explicit Paths in Formulas
```ruby
# In Homebrew formulas, they often specify explicit paths:
system "./configure", "--with-openssl=#{Formula["openssl@3"].opt_prefix}"
```

### Why pyenv Doesn't Use Homebrew's Solutions

1. **pyenv is independent** - it doesn't know about Homebrew's environment setup
2. **python-build uses autotools** - which has its own library search logic
3. **Legacy compatibility** - python-build tries to work on all Unix systems, not just Homebrew-managed ones

### The Real Solution Homebrew Recommends

Homebrew's official recommendation for Python is actually:

```bash
# Use Homebrew's Python directly (not pyenv)
brew install python@3.11
# This Python is properly compiled with Homebrew's environment
```

**Why this works:**
- ✅ Compiled entirely within Homebrew's environment
- ✅ Uses only ARM64 libraries
- ✅ No system path conflicts
- ✅ Homebrew controls the entire build process

### The Definitive Fix: Custom Environment for pyenv

You can absolutely fix this by forcing pyenv to use Homebrew's environment exclusively. Here's the complete solution:

#### Step 1: Set Up Homebrew Environment Variables

Create a script to set up the proper environment:

```bash
# Create ~/bin/setup-homebrew-python-env.sh
mkdir -p ~/bin
cat > ~/bin/setup-homebrew-python-env.sh << 'EOF'
#!/bin/bash
# Force pyenv to use only Homebrew ARM64 libraries

# Homebrew paths
export HOMEBREW_PREFIX="/opt/homebrew"
export HOMEBREW_CELLAR="/opt/homebrew/Cellar"

# Override system paths - this is the key!
export PATH="/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Force compiler to use only Homebrew libraries
export LDFLAGS="-L/opt/homebrew/lib"
export CPPFLAGS="-I/opt/homebrew/include"
export PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig"

# Explicitly exclude system library paths
export LIBRARY_PATH="/opt/homebrew/lib"
export C_INCLUDE_PATH="/opt/homebrew/include"
export CPLUS_INCLUDE_PATH="/opt/homebrew/include"

# Python build configuration
export PYTHON_CONFIGURE_OPTS="--enable-shared --enable-optimizations"

# Force architecture
export ARCHFLAGS="-arch arm64"
export CFLAGS="-arch arm64"
export CXXFLAGS="-arch arm64"

echo "✅ Homebrew ARM64 environment configured"
echo "📍 HOMEBREW_PREFIX: $HOMEBREW_PREFIX"
echo "📍 PATH: $PATH"
echo "📍 LDFLAGS: $LDFLAGS"
EOF

chmod +x ~/bin/setup-homebrew-python-env.sh
```

#### Step 2: Install Required Homebrew Packages

```bash
# Source the environment
source ~/bin/setup-homebrew-python-env.sh

# Install all required packages for Python compilation
brew install \
  libb2 \
  openssl@3 \
  readline \
  sqlite \
  xz \
  zlib \
  bzip2 \
  libffi \
  ncurses \
  gdbm \
  tcl-tk
```

#### Step 3: Clean and Reinstall pyenv

```bash
# Remove existing pyenv installation
brew uninstall --ignore-dependencies pyenv 2>/dev/null || true
rm -rf ~/.pyenv

# Install pyenv with clean environment
source ~/bin/setup-homebrew-python-env.sh
brew install pyenv

# Set up pyenv in shell
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
```

#### Step 4: Install Python with Custom Environment

```bash
# Source the environment (critical step!)
source ~/bin/setup-homebrew-python-env.sh

# Set up pyenv
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

# Install Python with forced Homebrew environment
env \
  PYTHON_CONFIGURE_OPTS="--enable-shared --enable-optimizations" \
  LDFLAGS="-L/opt/homebrew/lib" \
  CPPFLAGS="-I/opt/homebrew/include" \
  PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig" \
  LIBRARY_PATH="/opt/homebrew/lib" \
  C_INCLUDE_PATH="/opt/homebrew/include" \
  ARCHFLAGS="-arch arm64" \
  pyenv install 3.11.9 --force

# Set as global version
pyenv global 3.11.9
```

#### Step 5: Verify the Fix

```bash
# Test the installation
python3 -c "
import platform
import hashlib
import sys

print('🔍 System Information:')
print(f'  Python: {sys.version}')
print(f'  Architecture: {platform.machine()}')
print(f'  Executable: {sys.executable}')

print('\n🧪 Blake2 Test:')
try:
    h = hashlib.blake2b(b'test')
    print('  ✅ blake2b: Working perfectly!')
except Exception as e:
    print(f'  ❌ blake2b: {e}')

try:
    h = hashlib.blake2s(b'test')
    print('  ✅ blake2s: Working perfectly!')
except Exception as e:
    print(f'  ❌ blake2s: {e}')

print(f'\n📊 Available algorithms: {len(hashlib.algorithms_available)}')
print('🎉 If you see no errors above, blake2 is fixed!')
"
```

#### Step 6: Automate for Future Use

Add to your `~/.zshrc` or `~/.bash_profile`:

```bash
# Add to ~/.zshrc
cat >> ~/.zshrc << 'EOF'

# Homebrew Python Environment (for pyenv)
setup_homebrew_python() {
    source ~/bin/setup-homebrew-python-env.sh
    export PYENV_ROOT="$HOME/.pyenv"
    export PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init -)"
    echo "🍺 Homebrew Python environment ready"
}

# Alias for easy access
alias pyenv-brew="setup_homebrew_python"
EOF
```

### Why This Works

1. **Explicit Path Control**: We override `PATH` to exclude `/usr/local/bin` during compilation
2. **Library Path Override**: `LIBRARY_PATH` and `LDFLAGS` force the linker to use only Homebrew libraries
3. **Include Path Control**: `C_INCLUDE_PATH` and `CPPFLAGS` ensure headers come from Homebrew
4. **Architecture Enforcement**: `ARCHFLAGS` and `CFLAGS` force ARM64 compilation
5. **Complete Isolation**: We exclude system library paths entirely during the build

### Alternative: One-Line Fix for Existing Installation

If you already have pyenv installed and just want to fix the current Python:

```bash
# Quick fix for existing installation
source ~/bin/setup-homebrew-python-env.sh && \
export PYENV_ROOT="$HOME/.pyenv" && \
export PATH="$PYENV_ROOT/bin:$PATH" && \
eval "$(pyenv init -)" && \
env LDFLAGS="-L/opt/homebrew/lib" \
    CPPFLAGS="-I/opt/homebrew/include" \
    PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig" \
    LIBRARY_PATH="/opt/homebrew/lib" \
    ARCHFLAGS="-arch arm64" \
    pyenv install 3.11.9 --force
```

### Root Cause Analysis

This is a **complex architecture mismatch issue** on Apple Silicon Macs. Here's what's happening:

#### The Core Problem
1. **Apple Silicon Macs ship with Intel x86_64 libraries** in `/usr/local/` for Rosetta compatibility
2. **Python compilation** tries to link against available libraries during build
3. **Mixed architecture linking** occurs when ARM64 Python tries to use x86_64 libraries
4. **Blake2 extension module** (`_blake2`) fails to build properly due to architecture conflicts

#### System Architecture Analysis
On Apple Silicon Macs, you typically have:

```
/usr/local/          # Intel x86_64 libraries (shipped with macOS)
├── lib/             # x86_64 libraries for Rosetta compatibility
└── include/         # Headers that may reference x86_64 symbols

/opt/homebrew/       # ARM64 native libraries (user-installed)
├── lib/             # ARM64 libraries
└── include/         # ARM64-compatible headers

/System/Library/     # Apple's system libraries (universal or ARM64)
```

#### Why This Happens
1. **pyenv/python-build** searches standard library paths during compilation
2. **Compiler finds x86_64 libraries first** if `/usr/local` is in the search path
3. **Linker attempts to link ARM64 Python with x86_64 libraries**
4. **Blake2 extension fails** because it can't find compatible symbols
5. **Python builds successfully** but with broken blake2 support

### Impact Assessment

- **Functionality**: ✅ Application works normally (blake2 is optional)
- **Security**: ✅ No security impact (other hash algorithms available)
- **Performance**: ✅ No performance degradation
- **User Experience**: ❌ Confusing error messages on startup
- **Development**: ⚠️ May affect packages that specifically require blake2

### Solutions (In Order of Preference)

#### Solution 1: Use System Python (Recommended for Most Users)

The simplest solution is to use the system Python that Apple provides, which is properly compiled for your architecture:

```bash
# Check system Python
/usr/bin/python3 --version
python3 -c "import hashlib; print('blake2b works:', hasattr(hashlib, 'blake2b'))"

# Create virtual environment with system Python
/usr/bin/python3 -m venv venv
source venv/bin/activate
```

**Pros:**
- ✅ No architecture conflicts
- ✅ Properly compiled for Apple Silicon
- ✅ No complex setup required
- ✅ Maintained by Apple

**Cons:**
- ❌ Limited to Python versions Apple provides
- ❌ Less control over Python version

#### Solution 2: Clean pyenv Installation (Advanced Users)

For users who need specific Python versions:

```bash
# 1. Remove all conflicting installations
brew uninstall --ignore-dependencies pyenv
rm -rf ~/.pyenv

# 2. Clean environment variables
unset PYENV_ROOT
export PATH="/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# 3. Install pyenv with ARM64 Homebrew only
/opt/homebrew/bin/brew install pyenv

# 4. Set up environment for ARM64 compilation
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

# 5. Install Python with explicit ARM64 environment
env PYTHON_CONFIGURE_OPTS="--enable-shared" \
    CC=clang \
    LDFLAGS="-L/opt/homebrew/lib" \
    CPPFLAGS="-I/opt/homebrew/include" \
    PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig" \
    pyenv install 3.11.9
```

**Pros:**
- ✅ Full control over Python versions
- ✅ Proper ARM64 compilation
- ✅ Resolves blake2 issues

**Cons:**
- ❌ Complex setup process
- ❌ Requires understanding of build systems
- ❌ May break with system updates

#### Solution 3: Suppress Error Messages (Temporary Workaround)

If rebuilding Python is not feasible, suppress the error messages:

```python
import logging
import warnings

# Suppress blake2 hash errors
class Blake2Filter(logging.Filter):
    def filter(self, record):
        return not (record.levelname == 'ERROR' and 
                   'code for hash blake2' in record.getMessage())

logging.getLogger().addFilter(Blake2Filter())
warnings.filterwarnings('ignore', message='.*blake2.*')
```

### What NOT to Do

❌ **Don't remove system libraries in `/usr/local/`** - These are part of macOS and needed for Rosetta compatibility

❌ **Don't force x86_64 architecture** - This defeats the purpose of Apple Silicon performance

❌ **Don't mix Intel and ARM64 Homebrew** - This creates more conflicts

### Understanding the Limitations

#### Why This is Hard to Fix Completely

1. **Apple's Design**: macOS ships with x86_64 libraries for backward compatibility
2. **Build System Behavior**: Python's build system searches standard paths first
3. **Compiler Defaults**: Standard compiler flags may pick up wrong architecture libraries
4. **Dynamic Linking**: Runtime library resolution can still find wrong architecture

#### When to Accept the Error

The blake2 error is **cosmetic** in most cases. Consider accepting it when:
- ✅ Your application doesn't specifically need blake2 hashing
- ✅ Other hash algorithms (SHA, MD5) work fine
- ✅ The complexity of fixing outweighs the benefit
- ✅ You're using the application temporarily

### Verification Commands

After applying any solution, verify the fix:

```bash
# Test Python architecture
python3 -c "import platform; print('Architecture:', platform.machine())"

# Test blake2 functionality
python3 -c "
import hashlib
try:
    h = hashlib.blake2b(b'test')
    print('✅ blake2b: Working')
except Exception as e:
    print(f'❌ blake2b: {e}')

try:
    h = hashlib.blake2s(b'test')
    print('✅ blake2s: Working')
except Exception as e:
    print(f'❌ blake2s: {e}')

print(f'Available algorithms: {len(hashlib.algorithms_available)}')
"

# Check library architecture
otool -L $(python3 -c "import _hashlib; print(_hashlib.__file__)") 2>/dev/null || echo "No _hashlib module"
```

### Prevention for New Setups

1. **Use system Python when possible**
2. **If using pyenv, install with clean ARM64 environment**
3. **Avoid mixing package managers**
4. **Document your Python setup for team members**

## Related Issues

- [pyenv/pyenv#2573](https://github.com/pyenv/pyenv/issues/2573) - Original issue report
- [python/cpython#101148](https://github.com/python/cpython/issues/101148) - CPython issue tracker
- [Homebrew/homebrew-core#127316](https://github.com/Homebrew/homebrew-core/issues/127316) - Homebrew issue

---

**Note**: This issue affects many Python installations on Apple Silicon Macs. The error is primarily cosmetic and doesn't affect most applications' functionality.

## Other Common Issues

### Database Connection Issues

[Add other troubleshooting sections as needed]

---

**Note**: This troubleshooting guide is maintained as issues are discovered and resolved. If you encounter a new issue, please document it here for future reference.

## Apple Silicon (M1/M2/M3) Setup Issues

### Blake2b Hash Function Errors

If you encounter cryptography or hashlib errors on Apple Silicon Macs, use the ARM64 environment fix:

```bash
# 1. Set up ARM64 environment
source simple-fix/setup_arm64_homebrew.sh

# 2. Create ARM64 virtual environment
create_arm64_venv venv

# 3. Activate and install dependencies
source venv/bin/activate
pip install -e .
```

This ensures complete ARM64 library isolation and resolves mixed-architecture issues.

### Making ARM64 Setup Permanent

To avoid running the setup script each time:

```bash
echo 'source /Users/docchang/Development/creational.ai/pgsql-manager/simple-fix/setup_arm64_homebrew.sh' >> ~/.zshrc
```

## SSH Connection Issues

### Authentication Failures
- Ensure SSH keys are properly configured in `~/.ssh/config`
- Test SSH connection manually: `ssh hostname`
- Check if the target user exists on the remote system

### PostgreSQL User Issues
- Remote PostgreSQL installations may not have a `postgres` superuser
- Use the system user that installed PostgreSQL
- Check with: `ssh hostname "whoami"`

## Database Connection Issues

### Local Connection Failures
- Ensure PostgreSQL service is running: `brew services list | grep postgresql`
- Check if the database exists: `psql -l`
- Verify user permissions

### Remote Connection Issues
- Ensure PostgreSQL is configured to accept connections
- Check `pg_hba.conf` for authentication settings
- Verify firewall settings allow PostgreSQL port (default 5432)

## Installation Issues

### Homebrew PostgreSQL
- Update Homebrew: `brew update`
- Check available versions: `brew search postgresql`
- Install specific version: `brew install postgresql@15`

### Service Management
- Start service: `brew services start postgresql@15`
- Stop service: `brew services stop postgresql@15`
- Restart service: `brew services restart postgresql@15` 