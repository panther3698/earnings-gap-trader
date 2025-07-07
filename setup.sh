#!/bin/bash
# Automated Setup Script for Linux/Mac - Earnings Gap Trading System
# This script launches the Python setup wizard

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo
echo "================================================"
echo "  EARNINGS GAP TRADING SYSTEM - UNIX SETUP"
echo "================================================"
echo
echo "Starting automated setup wizard..."
echo

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    echo "Please install Python 3.9+ using your package manager:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    echo "  CentOS/RHEL:   sudo yum install python3 python3-pip"
    echo "  macOS:         brew install python3"
    echo "  Or download from: https://python.org/downloads/"
    exit 1
fi

# Show Python version
print_status "Python found"
python3 --version
echo

# Check Python version
python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
required_version="3.9"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)" 2>/dev/null; then
    print_error "Python 3.9+ required, found $python_version"
    echo "Please upgrade Python to version 3.9 or higher"
    exit 1
fi

# Check if setup script exists
if [ ! -f "scripts/setup_trading_system.py" ]; then
    print_error "scripts/setup_trading_system.py not found"
    echo "Please ensure you're running this from the project directory"
    exit 1
fi

print_info "Launching setup wizard..."
echo

# Make setup script executable
chmod +x scripts/setup_trading_system.py

# Run the setup script
if python3 scripts/setup_trading_system.py; then
    echo
    echo "================================================"
    echo "  SETUP COMPLETED SUCCESSFULLY!"
    echo "================================================"
    echo
    print_status "Your trading system is now ready."
    print_info "Dashboard URL: http://localhost:8000"
    echo
    
    # Ask if user wants to open browser
    read -p "Do you want to open the dashboard in your browser? (y/n): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Try to open browser
        if command -v xdg-open &> /dev/null; then
            xdg-open http://localhost:8000
        elif command -v open &> /dev/null; then
            open http://localhost:8000
        else
            print_warning "Could not open browser automatically"
            print_info "Please open http://localhost:8000 manually"
        fi
    fi
    
    echo
    print_status "Setup completed successfully!"
    
else
    echo
    echo "================================================"
    echo "  SETUP FAILED"
    echo "================================================"
    echo
    print_error "Setup failed. Please check the error messages above."
    print_info "For help, see QUICK_START.md or run: python3 scripts/validate_setup.py"
    echo
    exit 1
fi

echo
echo "For future reference:"
echo "  Start system: python3 main.py"
echo "  Run tests:    python3 -m pytest tests/"
echo "  Validate:     python3 scripts/validate_setup.py"
echo "  View logs:    tail -f trading_system.log"
echo