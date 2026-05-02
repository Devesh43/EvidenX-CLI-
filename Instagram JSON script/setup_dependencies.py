import subprocess
import sys

def install_packages():
    """
    Installs the required Python packages for the Instagram Extractor project.
    """
    print(" Setting up the Python dependencies for Instagram Extractor...")
    
    required_packages = [
        "beautifulsoup4",
        "pyzipper", # For encrypted ZIP support
        "lxml",     # Often used by BeautifulSoup for faster parsing
    ]

    for package in required_packages:
        try:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f" Successfully installed {package}")
        except subprocess.CalledProcessError as e:
            print(f" Failed to install {package}. Error: {e}")
            print("Please ensure you have pip installed and try running this script again.")
            sys.exit(1)
        except Exception as e:
            print(f"An unexpected error occurred while installing {package}: {e}")
            sys.exit(1)
            
    print("\n🎉 All dependencies installed successfully!")
    print("You can now run the main Instagram Extractor script: python Instagram_Extractor.py")

if __name__ == "__main__":
    install_packages()

