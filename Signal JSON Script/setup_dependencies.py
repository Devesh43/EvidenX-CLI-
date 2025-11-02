#!/usr/bin/env python3
"""
Setup script to install required dependencies for Signal Database Extractor
Run this first before using the Signal database extractor
"""

import subprocess
import sys
import os

def install_package(package):
    """Install a Python package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ Successfully installed {package}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package}: {e}")
        return False

def install_pysqlcipher3():
    """Install pysqlcipher3 for SQLCipher support"""
    print("📦 Installing pysqlcipher3...")
    
    # Try different installation methods
    packages_to_try = [
        "pysqlcipher3",
        "sqlcipher3",
        "pysqlite3"
    ]
    
    for package in packages_to_try:
        if install_package(package):
            print(f"✅ Successfully installed {package}")
            return True
    
    print("⚠️ Failed to install SQLCipher support via pip")
    print("💡 Manual installation may be required:")
    print("   - Ubuntu/Debian: sudo apt-get install sqlcipher libsqlcipher-dev")
    print("   - macOS: brew install sqlcipher")
    print("   - Then: pip install pysqlcipher3")
    return False

def main():
    print("🔧 Setting up Signal Database Extractor dependencies...")
    print("=" * 50)
    
    # Required packages
    packages = [
        "cryptography>=3.4.0",
        "pyzipper>=0.3.6",
        "lxml>=4.6.0",
        "xmltodict>=0.12.0",
    ]
    
    # Install Python packages
    all_success = True
    for package in packages:
        if not install_package(package):
            all_success = False
    
    # Try to install SQLCipher support
    sqlcipher_success = install_pysqlcipher3()
    
    print("=" * 50)
    if all_success and sqlcipher_success:
        print("✅ All dependencies installed successfully!")
        print("🚀 You can now run: python extract_signal_db.py")
    else:
        print("⚠️ Some dependencies failed to install.")
        if not sqlcipher_success:
            print("⚠️ SQLCipher support is required for database decryption")
        print("📖 Required packages:")
        for package in packages + ["pysqlcipher3"]:
            print(f"   - {package}")

if __name__ == "__main__":
    main()
