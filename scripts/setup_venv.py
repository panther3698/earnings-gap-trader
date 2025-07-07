#!/usr/bin/env python3
"""
Virtual Environment Setup Script for Earnings Gap Trader
This script will create and configure a virtual environment with all dependencies
"""
import os
import sys
import subprocess
import platform
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"📝 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(f"   Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        print(f"   Error: {e.stderr.strip()}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    print("🐍 Checking Python version...")
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python {version.major}.{version.minor} is not supported. Please use Python 3.8 or higher.")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def create_virtual_environment():
    """Create virtual environment"""
    venv_name = "venv"
    
    if os.path.exists(venv_name):
        print(f"⚠️  Virtual environment '{venv_name}' already exists")
        response = input("Do you want to remove it and create a new one? (y/N): ")
        if response.lower() == 'y':
            import shutil
            shutil.rmtree(venv_name)
            print(f"🗑️  Removed existing virtual environment")
        else:
            print(f"📁 Using existing virtual environment")
            return True
    
    # Create virtual environment
    python_cmd = sys.executable
    return run_command(f"{python_cmd} -m venv {venv_name}", "Creating virtual environment")

def get_activation_command():
    """Get the command to activate virtual environment based on platform"""
    if platform.system() == "Windows":
        return "venv\\Scripts\\activate"
    else:
        return "source venv/bin/activate"

def install_dependencies():
    """Install dependencies in virtual environment"""
    print("📦 Installing dependencies...")
    
    # Get the pip command for the virtual environment
    if platform.system() == "Windows":
        pip_cmd = "venv\\Scripts\\pip"
        python_cmd = "venv\\Scripts\\python"
    else:
        pip_cmd = "venv/bin/pip"
        python_cmd = "venv/bin/python"
    
    # Check if pip exists
    if not os.path.exists(pip_cmd.replace("pip", "pip.exe") if platform.system() == "Windows" else pip_cmd):
        print(f"❌ Pip not found at {pip_cmd}")
        return False
    
    # Upgrade pip first
    if not run_command(f"{python_cmd} -m pip install --upgrade pip", "Upgrading pip"):
        return False
    
    # Install wheel for better package compilation
    if not run_command(f"{pip_cmd} install wheel", "Installing wheel"):
        print("⚠️  Warning: Could not install wheel, continuing anyway...")
    
    # Install requirements
    if os.path.exists("requirements.txt"):
        print("📋 Installing from requirements.txt...")
        # Install in chunks to handle potential issues
        
        # Core dependencies first
        core_deps = [
            "pydantic==2.5.0",
            "pydantic-settings==2.1.0",
            "python-dotenv==1.0.0",
            "sqlalchemy==2.0.23",
            "alembic==1.12.1",
            "fastapi==0.104.1",
            "uvicorn[standard]==0.24.0",
            "cryptography==41.0.7"
        ]
        
        print("📦 Installing core dependencies...")
        for dep in core_deps:
            if not run_command(f"{pip_cmd} install {dep}", f"Installing {dep}"):
                print(f"⚠️  Warning: Could not install {dep}")
        
        # Install remaining dependencies
        print("📦 Installing remaining dependencies...")
        success = run_command(f"{pip_cmd} install -r requirements.txt", "Installing all requirements")
        
        if not success:
            print("⚠️  Some packages may have failed to install. This is common and may not affect core functionality.")
            print("   You can install specific packages manually later if needed.")
        
        return True
    else:
        print("❌ requirements.txt not found")
        return False

def create_logs_directory():
    """Create logs directory"""
    logs_dir = Path("logs")
    if not logs_dir.exists():
        logs_dir.mkdir()
        print("✅ Created logs directory")
    else:
        print("📁 Logs directory already exists")

def copy_env_file():
    """Copy .env.example to .env if it doesn't exist"""
    if not os.path.exists(".env"):
        if os.path.exists(".env.example"):
            import shutil
            shutil.copy(".env.example", ".env")
            print("✅ Created .env file from .env.example")
            print("⚠️  Please edit .env file with your actual API keys and settings")
        else:
            print("❌ .env.example not found")
            return False
    else:
        print("📁 .env file already exists")
    return True

def generate_encryption_key():
    """Generate an encryption key for the .env file"""
    try:
        # Try to generate an encryption key
        from cryptography.fernet import Fernet
        key = Fernet.generate_key().decode()
        
        # Read current .env file
        env_content = ""
        if os.path.exists(".env"):
            with open(".env", "r") as f:
                env_content = f.read()
        
        # Replace the placeholder encryption key
        if "generate-a-secure-encryption-key-using-python-cryptography" in env_content:
            env_content = env_content.replace(
                "generate-a-secure-encryption-key-using-python-cryptography",
                key
            )
            
            with open(".env", "w") as f:
                f.write(env_content)
            
            print("✅ Generated and set encryption key in .env file")
        else:
            print(f"🔑 Generated encryption key: {key}")
            print("   Add this to your .env file as ENCRYPTION_KEY")
            
        return True
    except ImportError:
        print("⚠️  Could not generate encryption key (cryptography not installed)")
        return False
    except Exception as e:
        print(f"⚠️  Could not generate encryption key: {e}")
        return False

def test_installation():
    """Test if the installation works"""
    print("🧪 Testing installation...")
    
    # Get python command for virtual environment
    if platform.system() == "Windows":
        python_cmd = "venv\\Scripts\\python"
    else:
        python_cmd = "venv/bin/python"
    
    # Test basic imports
    test_script = '''
import sys
try:
    import pydantic
    import sqlalchemy
    import fastapi
    import cryptography
    print("✅ All core dependencies imported successfully")
    sys.exit(0)
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
'''
    
    try:
        result = subprocess.run(
            [python_cmd, "-c", test_script],
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout.strip())
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Installation test failed: {e.stderr.strip()}")
        return False

def print_next_steps():
    """Print next steps for the user"""
    activation_cmd = get_activation_command()
    
    print("\n" + "=" * 60)
    print("🎉 Virtual Environment Setup Complete!")
    print("=" * 60)
    
    print("\n📝 Next Steps:")
    print(f"1. Activate virtual environment:")
    if platform.system() == "Windows":
        print(f"   {activation_cmd}")
    else:
        print(f"   {activation_cmd}")
    
    print("\n2. Edit .env file with your API keys:")
    print("   - Add your Zerodha Kite API credentials")
    print("   - Add your Telegram bot token and chat ID")
    print("   - Review and adjust trading parameters")
    
    print("\n3. Initialize the database:")
    if platform.system() == "Windows":
        print('   venv\\Scripts\\python -c "from database import init_db; import asyncio; asyncio.run(init_db())"')
    else:
        print('   venv/bin/python -c "from database import init_db; import asyncio; asyncio.run(init_db())"')
    
    print("\n4. Test the setup:")
    if platform.system() == "Windows":
        print("   venv\\Scripts\\python test_database_setup.py")
    else:
        print("   venv/bin/python test_database_setup.py")
    
    print("\n5. Run the application:")
    if platform.system() == "Windows":
        print("   venv\\Scripts\\python main.py")
    else:
        print("   venv/bin/python main.py")
    
    print("\n📚 Documentation:")
    print("   - Check docs/SETUP.md for detailed setup instructions")
    print("   - Check docs/API_GUIDE.md for API documentation")
    
    print("\n🔧 Troubleshooting:")
    print("   - If some packages failed to install, you can install them individually")
    print("   - Some optional packages (like ta-lib) may require system dependencies")
    print("   - Run the verification script: python3 verify_setup.py")

def main():
    """Main setup function"""
    print("🚀 Earnings Gap Trader - Virtual Environment Setup")
    print("=" * 60)
    
    # Check Python version
    if not check_python_version():
        return 1
    
    steps = [
        ("Creating virtual environment", create_virtual_environment),
        ("Installing dependencies", install_dependencies),
        ("Creating logs directory", create_logs_directory),
        ("Setting up .env file", copy_env_file),
        ("Generating encryption key", generate_encryption_key),
        ("Testing installation", test_installation),
    ]
    
    failed_steps = []
    
    for step_name, step_func in steps:
        try:
            if not step_func():
                failed_steps.append(step_name)
        except Exception as e:
            print(f"❌ {step_name} failed with exception: {e}")
            failed_steps.append(step_name)
    
    if failed_steps:
        print(f"\n⚠️  Setup completed with {len(failed_steps)} warnings/errors:")
        for step in failed_steps:
            print(f"   - {step}")
        print("\nThe core functionality should still work. Check the messages above for details.")
    
    print_next_steps()
    
    return 0 if len(failed_steps) == 0 else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)