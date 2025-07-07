#!/usr/bin/env python3
"""
Verification script for database layer and configuration setup
This script checks if all files are properly created and structured
"""
import os
import ast
import re

def check_file_exists(filepath, description):
    """Check if a file exists and print status"""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} (MISSING)")
        return False

def check_python_syntax(filepath):
    """Check if Python file has valid syntax"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        print(f"✅ Syntax check passed: {filepath}")
        return True
    except SyntaxError as e:
        print(f"❌ Syntax error in {filepath}: {e}")
        return False
    except Exception as e:
        print(f"❌ Error checking {filepath}: {e}")
        return False

def check_imports_in_file(filepath, expected_imports):
    """Check if file contains expected imports"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        found_imports = []
        missing_imports = []
        
        for imp in expected_imports:
            if f"import {imp}" in content or f"from {imp}" in content:
                found_imports.append(imp)
            else:
                missing_imports.append(imp)
        
        if missing_imports:
            print(f"⚠️  {filepath} missing imports: {missing_imports}")
        else:
            print(f"✅ All expected imports found in {filepath}")
        
        return len(missing_imports) == 0
    except Exception as e:
        print(f"❌ Error checking imports in {filepath}: {e}")
        return False

def check_class_definitions(filepath, expected_classes):
    """Check if file contains expected class definitions"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        found_classes = []
        missing_classes = []
        
        for cls in expected_classes:
            if f"class {cls}" in content:
                found_classes.append(cls)
            else:
                missing_classes.append(cls)
        
        if missing_classes:
            print(f"⚠️  {filepath} missing classes: {missing_classes}")
        else:
            print(f"✅ All expected classes found in {filepath}")
        
        return len(missing_classes) == 0
    except Exception as e:
        print(f"❌ Error checking classes in {filepath}: {e}")
        return False

def verify_config_file():
    """Verify config.py implementation"""
    print("\n🔧 Verifying Configuration Implementation...")
    
    filepath = "config.py"
    checks = []
    
    # Check file exists
    checks.append(check_file_exists(filepath, "Configuration file"))
    
    if os.path.exists(filepath):
        # Check syntax
        checks.append(check_python_syntax(filepath))
        
        # Check for TradingConfig class
        checks.append(check_class_definitions(filepath, ["TradingConfig"]))
        
        # Check for Pydantic imports
        checks.append(check_imports_in_file(filepath, ["pydantic"]))
        
        # Check for specific functionality
        with open(filepath, 'r') as f:
            content = f.read()
            
        if "BaseSettings" in content:
            print("✅ TradingConfig inherits from BaseSettings")
            checks.append(True)
        else:
            print("❌ TradingConfig does not inherit from BaseSettings")
            checks.append(False)
            
        if "SecretStr" in content:
            print("✅ Using SecretStr for sensitive data")
            checks.append(True)
        else:
            print("❌ SecretStr not used")
            checks.append(False)
    
    return all(checks)

def verify_database_models():
    """Verify trade_models.py implementation"""
    print("\n📊 Verifying Database Models...")
    
    filepath = "models/trade_models.py"
    checks = []
    
    # Check file exists
    checks.append(check_file_exists(filepath, "Trade models file"))
    
    if os.path.exists(filepath):
        # Check syntax
        checks.append(check_python_syntax(filepath))
        
        # Check for expected model classes
        expected_models = ["Trade", "Signal", "Performance", "Position", "Portfolio", "EarningsEvent"]
        checks.append(check_class_definitions(filepath, expected_models))
        
        # Check for SQLAlchemy imports
        checks.append(check_imports_in_file(filepath, ["sqlalchemy"]))
        
        # Check for Base class usage
        with open(filepath, 'r') as f:
            content = f.read()
            
        base_count = content.count("(Base):")
        if base_count >= 6:  # At least 6 models should inherit from Base
            print(f"✅ Found {base_count} models inheriting from Base")
            checks.append(True)
        else:
            print(f"❌ Only {base_count} models inherit from Base")
            checks.append(False)
    
    return all(checks)

def verify_database_layer():
    """Verify database.py implementation"""
    print("\n🗄️  Verifying Database Layer...")
    
    filepath = "database.py"
    checks = []
    
    # Check file exists
    checks.append(check_file_exists(filepath, "Database layer file"))
    
    if os.path.exists(filepath):
        # Check syntax
        checks.append(check_python_syntax(filepath))
        
        # Check for expected classes
        expected_classes = ["DatabaseManager", "MigrationManager"]
        checks.append(check_class_definitions(filepath, expected_classes))
        
        # Check for SQLAlchemy and Alembic imports
        checks.append(check_imports_in_file(filepath, ["sqlalchemy", "alembic"]))
        
        # Check for specific functionality
        with open(filepath, 'r') as f:
            content = f.read()
            
        if "session_scope" in content:
            print("✅ Session context manager implemented")
            checks.append(True)
        else:
            print("❌ Session context manager missing")
            checks.append(False)
            
        if "connection pooling" in content.lower():
            print("✅ Connection pooling implemented")
            checks.append(True)
        else:
            print("❌ Connection pooling not mentioned")
            checks.append(False)
    
    return all(checks)

def verify_utilities():
    """Verify utility files"""
    print("\n🔧 Verifying Utility Files...")
    
    utility_files = [
        ("utils/encryption.py", "Encryption utilities"),
        ("utils/validators.py", "Validation utilities"),
        ("utils/logging_config.py", "Logging configuration")
    ]
    
    checks = []
    
    for filepath, description in utility_files:
        checks.append(check_file_exists(filepath, description))
        if os.path.exists(filepath):
            checks.append(check_python_syntax(filepath))
    
    return all(checks)

def verify_requirements():
    """Verify requirements.txt"""
    print("\n📦 Verifying Requirements...")
    
    filepath = "requirements.txt"
    checks = []
    
    checks.append(check_file_exists(filepath, "Requirements file"))
    
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            content = f.read()
        
        required_packages = [
            "fastapi", "sqlalchemy", "alembic", "pydantic", "pydantic-settings",
            "cryptography", "python-dotenv", "structlog"
        ]
        
        missing_packages = []
        for package in required_packages:
            if package not in content.lower():
                missing_packages.append(package)
        
        if missing_packages:
            print(f"❌ Missing packages in requirements.txt: {missing_packages}")
            checks.append(False)
        else:
            print("✅ All required packages found in requirements.txt")
            checks.append(True)
        
        # Count total packages
        lines = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith('#')]
        package_lines = [line for line in lines if '==' in line]
        print(f"✅ Found {len(package_lines)} packages in requirements.txt")
    
    return all(checks)

def verify_project_structure():
    """Verify overall project structure"""
    print("\n📁 Verifying Project Structure...")
    
    required_dirs = [
        "models", "utils", "core", "tests", "docs", "frontend"
    ]
    
    required_files = [
        "main.py", "config.py", "database.py", "requirements.txt", "README.md"
    ]
    
    checks = []
    
    print("Required directories:")
    for directory in required_dirs:
        if os.path.exists(directory):
            print(f"✅ {directory}/")
            checks.append(True)
        else:
            print(f"❌ {directory}/ (MISSING)")
            checks.append(False)
    
    print("\nRequired files:")
    for file in required_files:
        checks.append(check_file_exists(file, f"Required file"))
    
    return all(checks)

def main():
    """Run verification checks"""
    print("🔍 Earnings Gap Trader - Database Layer Verification")
    print("=" * 60)
    
    verification_functions = [
        ("Project Structure", verify_project_structure),
        ("Configuration", verify_config_file),
        ("Database Models", verify_database_models),
        ("Database Layer", verify_database_layer),
        ("Utilities", verify_utilities),
        ("Requirements", verify_requirements),
    ]
    
    passed = 0
    total = len(verification_functions)
    
    for name, func in verification_functions:
        try:
            if func():
                passed += 1
                print(f"✅ {name} verification passed")
            else:
                print(f"❌ {name} verification failed")
        except Exception as e:
            print(f"❌ {name} verification crashed: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Verification Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All verifications passed! Database layer setup is properly implemented.")
        print("\n📝 Next steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Set up environment variables in .env file")
        print("3. Initialize database: python -c \"from database import init_db; import asyncio; asyncio.run(init_db())\"")
        print("4. Run the actual tests: python test_database_setup.py")
        return 0
    else:
        print("⚠️  Some verifications failed. Please check the issues above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)