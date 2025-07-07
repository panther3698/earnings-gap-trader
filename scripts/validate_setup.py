#!/usr/bin/env python3
"""
Setup Validation Script for Earnings Gap Trading System
Validates that all components are properly installed and configured
"""

import os
import sys
import json
import sqlite3
import importlib
from pathlib import Path
from typing import Dict, List, Tuple, Any
import urllib.request
import subprocess

# ANSI Color Codes
class Colors:
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    HEADER = '\033[95m'

class ValidationResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.results = []
    
    def add_result(self, test_name: str, status: str, message: str):
        self.results.append({
            'test': test_name,
            'status': status,
            'message': message
        })
        
        if status == 'PASS':
            self.passed += 1
        elif status == 'FAIL':
            self.failed += 1
        elif status == 'WARN':
            self.warnings += 1

class SetupValidator:
    """Validates trading system setup"""
    
    def __init__(self):
        self.project_dir = Path.cwd()
        self.results = ValidationResult()
    
    def print_colored(self, text: str, color: str):
        print(f"{color}{text}{Colors.ENDC}")
    
    def print_header(self, text: str):
        print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}{text.center(60)}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.ENDC}\n")
    
    def run_test(self, test_name: str, test_func, critical: bool = True):
        """Run a validation test"""
        try:
            print(f"Testing {test_name}...", end=" ")
            result, message = test_func()
            
            if result:
                self.print_colored("✅ PASS", Colors.OKGREEN)
                self.results.add_result(test_name, 'PASS', message)
            else:
                if critical:
                    self.print_colored("❌ FAIL", Colors.FAIL)
                    self.results.add_result(test_name, 'FAIL', message)
                else:
                    self.print_colored("⚠️  WARN", Colors.WARNING)
                    self.results.add_result(test_name, 'WARN', message)
                
                if message:
                    print(f"    {message}")
            
        except Exception as e:
            self.print_colored("❌ ERROR", Colors.FAIL)
            self.results.add_result(test_name, 'FAIL', f"Exception: {str(e)}")
    
    def validate_python_version(self) -> Tuple[bool, str]:
        """Validate Python version"""
        version = sys.version_info
        required = (3, 9)
        
        if version >= required:
            return True, f"Python {version.major}.{version.minor}.{version.micro}"
        else:
            return False, f"Python {version.major}.{version.minor} (requires 3.9+)"
    
    def validate_project_structure(self) -> Tuple[bool, str]:
        """Validate project directory structure"""
        required_files = [
            'main.py',
            'config.py',
            'database.py',
            'requirements.txt',
            '.env.example',
            'README.md'
        ]
        
        required_dirs = [
            'core',
            'models',
            'utils',
            'frontend',
            'tests'
        ]
        
        missing_files = []
        missing_dirs = []
        
        for file in required_files:
            if not (self.project_dir / file).exists():
                missing_files.append(file)
        
        for dir_name in required_dirs:
            if not (self.project_dir / dir_name).is_dir():
                missing_dirs.append(dir_name)
        
        if missing_files or missing_dirs:
            missing = missing_files + missing_dirs
            return False, f"Missing: {', '.join(missing)}"
        
        return True, "All required files and directories present"
    
    def validate_virtual_environment(self) -> Tuple[bool, str]:
        """Validate virtual environment"""
        venv_dir = self.project_dir / 'venv'
        
        if not venv_dir.exists():
            return False, "Virtual environment not found"
        
        # Check for Python executable
        if sys.platform == 'win32':
            python_exe = venv_dir / 'Scripts' / 'python.exe'
        else:
            python_exe = venv_dir / 'bin' / 'python'
        
        if not python_exe.exists():
            return False, "Python executable not found in venv"
        
        return True, f"Virtual environment found at {venv_dir}"
    
    def validate_dependencies(self) -> Tuple[bool, str]:
        """Validate Python dependencies"""
        required_packages = [
            'fastapi',
            'uvicorn',
            'sqlalchemy',
            'kiteconnect',
            'telegram',
            'pandas',
            'numpy',
            'yfinance',
            'cryptography',
            'python-dotenv',
            'jinja2',
            'aiofiles',
            'pytest'
        ]
        
        missing_packages = []
        
        for package in required_packages:
            try:
                importlib.import_module(package.replace('-', '_'))
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            return False, f"Missing packages: {', '.join(missing_packages)}"
        
        return True, f"All {len(required_packages)} required packages installed"
    
    def validate_configuration(self) -> Tuple[bool, str]:
        """Validate configuration files"""
        env_file = self.project_dir / '.env'
        
        if not env_file.exists():
            return False, ".env file not found"
        
        # Check for required environment variables
        required_vars = [
            'SECRET_KEY',
            'DATABASE_URL',
            'KITE_API_KEY',
            'KITE_API_SECRET'
        ]
        
        missing_vars = []
        
        try:
            with open(env_file, 'r') as f:
                content = f.read()
                
                for var in required_vars:
                    if f"{var}=" not in content:
                        missing_vars.append(var)
            
            if missing_vars:
                return False, f"Missing variables: {', '.join(missing_vars)}"
            
            return True, "Configuration file properly formatted"
            
        except Exception as e:
            return False, f"Error reading .env file: {e}"
    
    def validate_database(self) -> Tuple[bool, str]:
        """Validate database setup"""
        db_file = self.project_dir / 'trading_system.db'
        
        if not db_file.exists():
            return False, "Database file not found"
        
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # Check for required tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = ['trades', 'signals', 'performance', 'market_data']
            missing_tables = [table for table in required_tables if table not in tables]
            
            conn.close()
            
            if missing_tables:
                return False, f"Missing tables: {', '.join(missing_tables)}"
            
            return True, f"Database with {len(tables)} tables"
            
        except Exception as e:
            return False, f"Database error: {e}"
    
    def validate_file_permissions(self) -> Tuple[bool, str]:
        """Validate file permissions"""
        try:
            # Test write permissions
            test_file = self.project_dir / 'test_write.tmp'
            
            with open(test_file, 'w') as f:
                f.write('test')
            
            # Test read permissions
            with open(test_file, 'r') as f:
                content = f.read()
            
            # Cleanup
            test_file.unlink()
            
            if content == 'test':
                return True, "Read/write permissions OK"
            else:
                return False, "File content mismatch"
                
        except Exception as e:
            return False, f"Permission error: {e}"
    
    def validate_network_connectivity(self) -> Tuple[bool, str]:
        """Validate network connectivity"""
        test_urls = [
            'https://api.kite.zerodha.com',
            'https://api.telegram.org',
            'https://query1.finance.yahoo.com'
        ]
        
        accessible_urls = 0
        
        for url in test_urls:
            try:
                urllib.request.urlopen(url, timeout=5)
                accessible_urls += 1
            except:
                continue
        
        if accessible_urls == len(test_urls):
            return True, "All external APIs accessible"
        elif accessible_urls > 0:
            return True, f"{accessible_urls}/{len(test_urls)} APIs accessible"
        else:
            return False, "No external APIs accessible"
    
    def validate_port_availability(self) -> Tuple[bool, str]:
        """Validate port availability"""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', 8000))
            sock.close()
            
            if result != 0:
                return True, "Port 8000 available"
            else:
                return False, "Port 8000 already in use"
                
        except Exception as e:
            return False, f"Port check error: {e}"
    
    def validate_imports(self) -> Tuple[bool, str]:
        """Validate that main modules can be imported"""
        try:
            # Test importing main modules
            sys.path.insert(0, str(self.project_dir))
            
            import config
            import database
            
            return True, "Main modules import successfully"
            
        except Exception as e:
            return False, f"Import error: {e}"
    
    def validate_api_credentials_format(self) -> Tuple[bool, str]:
        """Validate API credentials format"""
        env_file = self.project_dir / '.env'
        
        if not env_file.exists():
            return False, ".env file not found"
        
        try:
            with open(env_file, 'r') as f:
                content = f.read()
            
            # Check for credential patterns
            checks = []
            
            # API Key should be alphanumeric
            if 'KITE_API_KEY=' in content:
                api_key_line = [line for line in content.split('\n') if 'KITE_API_KEY=' in line][0]
                api_key = api_key_line.split('=')[1].strip()
                if api_key and len(api_key) >= 10:
                    checks.append("API Key format OK")
                else:
                    checks.append("API Key format issue")
            
            # Check for Bot Token format (if present)
            if 'TELEGRAM_BOT_TOKEN=' in content:
                token_line = [line for line in content.split('\n') if 'TELEGRAM_BOT_TOKEN=' in line][0]
                token = token_line.split('=')[1].strip()
                if ':' in token and len(token) > 20:
                    checks.append("Telegram token format OK")
                else:
                    checks.append("Telegram token format issue")
            
            if "issue" in ' '.join(checks):
                return False, '; '.join(checks)
            
            return True, '; '.join(checks) if checks else "No credentials to validate"
            
        except Exception as e:
            return False, f"Credential validation error: {e}"
    
    def run_all_validations(self):
        """Run all validation tests"""
        self.print_header("TRADING SYSTEM SETUP VALIDATION")
        
        print("🔍 Running comprehensive system validation...\n")
        
        # Critical tests (must pass)
        self.run_test("Python Version", self.validate_python_version, critical=True)
        self.run_test("Project Structure", self.validate_project_structure, critical=True)
        self.run_test("Virtual Environment", self.validate_virtual_environment, critical=True)
        self.run_test("Dependencies", self.validate_dependencies, critical=True)
        self.run_test("Configuration", self.validate_configuration, critical=True)
        self.run_test("Database", self.validate_database, critical=True)
        self.run_test("File Permissions", self.validate_file_permissions, critical=True)
        self.run_test("Module Imports", self.validate_imports, critical=True)
        
        # Non-critical tests (warnings only)
        self.run_test("Network Connectivity", self.validate_network_connectivity, critical=False)
        self.run_test("Port Availability", self.validate_port_availability, critical=False)
        self.run_test("Credential Formats", self.validate_api_credentials_format, critical=False)
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print validation summary"""
        total_tests = self.results.passed + self.results.failed + self.results.warnings
        
        print(f"\n{Colors.BOLD}VALIDATION SUMMARY:{Colors.ENDC}")
        print(f"{'='*50}")
        
        print(f"✅ Passed: {self.results.passed}")
        print(f"❌ Failed: {self.results.failed}")
        print(f"⚠️  Warnings: {self.results.warnings}")
        print(f"📊 Total: {total_tests}")
        
        # Overall status
        if self.results.failed == 0:
            if self.results.warnings == 0:
                self.print_colored("\n🎉 VALIDATION PASSED! System is ready.", Colors.OKGREEN)
                print("Your trading system is properly configured and ready to use.")
            else:
                self.print_colored("\n✅ VALIDATION MOSTLY PASSED with warnings.", Colors.WARNING)
                print("System should work but consider addressing warnings.")
        else:
            self.print_colored("\n❌ VALIDATION FAILED!", Colors.FAIL)
            print("Please fix the failed tests before using the system.")
        
        # Failed tests details
        if self.results.failed > 0:
            print(f"\n{Colors.FAIL}FAILED TESTS:{Colors.ENDC}")
            for result in self.results.results:
                if result['status'] == 'FAIL':
                    print(f"  ❌ {result['test']}: {result['message']}")
        
        # Warnings details
        if self.results.warnings > 0:
            print(f"\n{Colors.WARNING}WARNINGS:{Colors.ENDC}")
            for result in self.results.results:
                if result['status'] == 'WARN':
                    print(f"  ⚠️  {result['test']}: {result['message']}")
        
        # Next steps
        print(f"\n{Colors.BOLD}NEXT STEPS:{Colors.ENDC}")
        if self.results.failed == 0:
            print("1. Start the trading system: python main.py")
            print("2. Open dashboard: http://localhost:8000")
            print("3. Test paper trading functionality")
            print("4. Review configuration settings")
        else:
            print("1. Fix failed validation tests")
            print("2. Re-run validation: python scripts/validate_setup.py")
            print("3. Check setup logs for detailed error information")
            print("4. Refer to QUICK_START.md for troubleshooting")

def main():
    """Main entry point"""
    validator = SetupValidator()
    validator.run_all_validations()
    
    # Return exit code based on results
    if validator.results.failed > 0:
        return 1
    else:
        return 0

if __name__ == "__main__":
    sys.exit(main())