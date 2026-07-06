#!/usr/bin/env python3
"""
Setup script to install required dependencies
Run this first before using the WhatsApp extractor with media support
"""

import subprocess
import sys
import os

def install_package(package):
    """Install a Python package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f" Successfully installed {package}")
        return True
    except subprocess.CalledProcessError as e:
        print(f" Failed to install {package}: {e}")
        return False

def install_wadecrypt():
    """Install wadecrypt tool for database decryption"""
    try:
        # Check if wadecrypt is already installed
        result = subprocess.run(["wadecrypt", "--help"], capture_output=True)
        if result.returncode == 0:
            print(" wadecrypt is already installed")
            return True
    except FileNotFoundError:
        pass
    
    print(" Installing wadecrypt...")
    
    # Install wadecrypt using pip
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "wadecrypt"])
        print(" Successfully installed wadecrypt")
        return True
    except subprocess.CalledProcessError:
        print(" Failed to install wadecrypt via pip, trying alternative method...")
        
        # Alternative installation method
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "git+https://github.com/ElDavoo/WhatsApp-Crypt14-Crypt15-Decryptor.git"])
            print(" Successfully installed wadecrypt from GitHub")
            return True
        except subprocess.CalledProcessError as e:
            print(f" Failed to install wadecrypt: {e}")
            print(" You may need to install it manually:")
            print("   pip install git+https://github.com/ElDavoo/WhatsApp-Crypt14-Crypt15-Decryptor.git")
            return False

def main():
    print("🔧 Setting up WhatsApp Data & Media Extractor dependencies...")
    print("=" * 60)
    
    # Required packages
    packages = [
        "pyzipper",
    ]
    
    # Install Python packages
    all_success = True
    for package in packages:
        if not install_package(package):
            all_success = False
    
    # Install wadecrypt
    if not install_wadecrypt():
        all_success = False
    
    print("=" * 60)
    if all_success:
        print(" All dependencies installed successfully!")
        print(" You can now run: python extract_whatsapp_data_with_media.py")
        print("🎬 This version will extract ALL media files to a 'whatsapp_media' folder!")
    else:
        print("⚠️ Some dependencies failed to install. Please install them manually.")
        print("📖 Required packages:")
        for package in packages + ["wadecrypt"]:
            print(f"   - {package}")

if __name__ == "__main__":
    main()
