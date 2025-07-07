#!/usr/bin/env python3
"""
Test script to verify database layer and configuration setup
"""
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_configuration():
    """Test configuration loading"""
    print("🔧 Testing configuration...")
    try:
        from config import TradingConfig, settings
        
        # Test basic config loading
        config = TradingConfig(debug=True)
        print(f"✅ Configuration loaded successfully")
        print(f"   - Debug: {config.debug}")
        print(f"   - Database URL: {config.database_url}")
        print(f"   - Max Position Size: {config.max_position_size}")
        
        # Test config validation
        masked_config = config.mask_secrets()
        print(f"✅ Secret masking works")
        
        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


def test_database_models():
    """Test database models"""
    print("\n📊 Testing database models...")
    try:
        from models.trade_models import (
            Trade, Signal, Performance, Position, 
            EarningsEvent, Portfolio, MarketData, RiskMetrics
        )
        from database import Base
        
        # Check that all models are properly defined
        models = [Trade, Signal, Performance, Position, EarningsEvent, Portfolio, MarketData, RiskMetrics]
        for model in models:
            print(f"✅ Model {model.__name__} loaded successfully")
            
        print(f"✅ All {len(models)} database models loaded")
        return True
    except Exception as e:
        print(f"❌ Database models test failed: {e}")
        return False


def test_database_connection():
    """Test database connection and table creation"""
    print("\n🗄️  Testing database connection...")
    try:
        from database import db_manager, test_database_connection
        
        # Test connection
        if test_database_connection():
            print("✅ Database connection successful")
        else:
            print("❌ Database connection failed")
            return False
        
        # Test table creation
        db_manager.create_tables()
        print("✅ Database tables created successfully")
        
        # Get table info
        table_info = db_manager.get_table_info()
        print(f"✅ Found {len(table_info)} tables:")
        for table_name, info in table_info.items():
            print(f"   - {table_name}: {info['columns']} columns, {info['indexes']} indexes")
        
        return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False


def test_encryption_utilities():
    """Test encryption utilities"""
    print("\n🔐 Testing encryption utilities...")
    try:
        from utils.encryption import encrypt_data, decrypt_data, generate_key
        
        # Generate a test key
        key = generate_key()
        print("✅ Encryption key generated")
        
        # Test encryption/decryption
        test_data = "sensitive_api_key_12345"
        encrypted = encrypt_data(test_data, key)
        decrypted = decrypt_data(encrypted, key)
        
        if decrypted == test_data:
            print("✅ Encryption/decryption working correctly")
        else:
            print("❌ Encryption/decryption failed")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Encryption test failed: {e}")
        return False


def test_validators():
    """Test validation utilities"""
    print("\n✅ Testing validation utilities...")
    try:
        from utils.validators import (
            validate_symbol, validate_price, validate_quantity,
            validate_trading_config, validate_order_params
        )
        
        # Test symbol validation
        is_valid, error = validate_symbol("RELIANCE")
        if is_valid:
            print("✅ Symbol validation working")
        else:
            print(f"❌ Symbol validation failed: {error}")
            return False
        
        # Test price validation
        is_valid, error = validate_price(100.50)
        if is_valid:
            print("✅ Price validation working")
        else:
            print(f"❌ Price validation failed: {error}")
            return False
        
        # Test quantity validation
        is_valid, error = validate_quantity(10)
        if is_valid:
            print("✅ Quantity validation working")
        else:
            print(f"❌ Quantity validation failed: {error}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Validation test failed: {e}")
        return False


def test_logging_setup():
    """Test logging configuration"""
    print("\n📝 Testing logging setup...")
    try:
        from utils.logging_config import setup_logging, get_logger, TradingLogger
        
        # Setup logging
        setup_logging(log_level="INFO", enable_structured_logging=False)
        print("✅ Logging setup completed")
        
        # Test regular logger
        logger = get_logger(__name__)
        logger.info("Test log message")
        print("✅ Regular logger working")
        
        # Test trading logger
        trading_logger = TradingLogger(__name__)
        trading_logger.log_trade_entry("RELIANCE", 10, 2500.0, "earnings_gap")
        print("✅ Trading logger working")
        
        return True
    except Exception as e:
        print(f"❌ Logging test failed: {e}")
        return False


def test_database_session():
    """Test database session management"""
    print("\n🔄 Testing database session management...")
    try:
        from database import db_manager
        from models.trade_models import Portfolio
        
        # Test session context manager
        with db_manager.session_scope() as session:
            # Try to query existing tables
            portfolios = session.query(Portfolio).all()
            print(f"✅ Session query successful, found {len(portfolios)} portfolios")
        
        print("✅ Session context manager working correctly")
        return True
    except Exception as e:
        print(f"❌ Database session test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("🚀 Starting Database & Configuration Test Suite")
    print("=" * 60)
    
    tests = [
        ("Configuration", test_configuration),
        ("Database Models", test_database_models),
        ("Database Connection", test_database_connection),
        ("Encryption Utilities", test_encryption_utilities),
        ("Validators", test_validators),
        ("Logging Setup", test_logging_setup),
        ("Database Sessions", test_database_session),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Database layer setup is complete.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)