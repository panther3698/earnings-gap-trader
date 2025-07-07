# Test Suite - Earnings Gap Trading System

This directory contains comprehensive test suites for all components of the Earnings Gap Trading System.

## Test Files Overview

### Core Component Tests
- **`test_strategy.py`** - Earnings gap detection strategy tests
- **`test_earnings_scanner.py`** - Comprehensive earnings scanner tests  
- **`test_risk_manager.py`** - Risk management and position sizing tests
- **`test_order_engine.py`** - Order execution and GTT/OCO tests
- **`test_market_data.py`** - Market data service and API integration tests
- **`test_telegram_service.py`** - Telegram bot functionality tests

### System Tests
- **`test_database_setup.py`** - Database models and setup validation
- **`test_execution.py`** - Trade execution workflow tests
- **`test_integration.py`** - End-to-end integration testing

## Running Tests

### Run All Tests
```bash
# From project root
pytest tests/ -v

# With coverage report
pytest tests/ --cov=. --cov-report=html
```

### Run Specific Test Categories
```bash
# Core component tests
pytest tests/test_strategy.py -v
pytest tests/test_risk_manager.py -v
pytest tests/test_order_engine.py -v

# Integration tests
pytest tests/test_integration.py -v

# Database tests
pytest tests/test_database_setup.py -v
```

### Run Tests with Paper Trading
```bash
# Set paper trading mode
export PAPER_TRADING=True
pytest tests/test_integration.py -v
```

## Test Categories

### Unit Tests
- **Strategy Logic**: Gap detection, signal generation
- **Risk Management**: Position sizing, circuit breakers
- **Order Engine**: Order placement, GTT/OCO handling
- **Market Data**: Data fetching, validation, failover
- **Telegram Bot**: Commands, notifications, approvals

### Integration Tests  
- **End-to-End Workflows**: Signal → Risk Check → Execution → Monitoring
- **Component Interactions**: Market data → Scanner → Risk → Orders
- **WebSocket Communication**: Real-time updates and broadcasting
- **Database Operations**: CRUD operations and data integrity

### Performance Tests
- **Execution Speed**: Signal-to-order timing
- **API Latency**: External service response times
- **Memory Usage**: Resource consumption monitoring
- **Concurrent Operations**: Multi-threading and async handling

## Test Configuration

### Environment Variables for Testing
```bash
# Test database (optional)
TEST_DATABASE_URL=sqlite:///./test_earnings_gap_trader.db

# Paper trading mode
PAPER_TRADING=True

# Test API keys (mock/sandbox)
ZERODHA_API_KEY=test_api_key
TELEGRAM_BOT_TOKEN=test_bot_token

# Logging level for tests
LOG_LEVEL=DEBUG
```

### Test Data Setup
Tests use mock data and sandbox APIs where possible:
- Mock earnings announcements
- Simulated market data feeds
- Test Telegram bot interactions
- In-memory database for speed

## Coverage Goals

Target test coverage by component:
- **Strategy Logic**: 95%+
- **Risk Management**: 95%+  
- **Order Engine**: 90%+
- **Market Data**: 85%+
- **Telegram Bot**: 80%+
- **Integration**: 90%+

## Best Practices

### Writing New Tests
1. **Isolation**: Each test should be independent
2. **Mocking**: Mock external APIs and services
3. **Data Cleanup**: Clean up test data after each test
4. **Assertions**: Clear, specific assertions
5. **Documentation**: Document complex test scenarios

### Test Organization
- Group related tests in classes
- Use descriptive test method names
- Add docstrings for complex tests
- Use fixtures for common setup
- Parametrize tests for multiple scenarios

### Performance Testing
- Measure execution times for critical paths
- Test with realistic data volumes
- Monitor memory usage during tests
- Test concurrent access scenarios

## Continuous Integration

Tests are automatically run on:
- Every commit to main branch
- Pull request submissions
- Scheduled daily runs
- Before production deployments

### CI Requirements
- All tests must pass
- Coverage must meet minimum thresholds
- No new linting errors
- Performance benchmarks met

## Debugging Failed Tests

### Common Issues
1. **API Rate Limits**: Use mocks for external APIs
2. **Timing Issues**: Add proper waits for async operations
3. **Database State**: Ensure clean database state
4. **Configuration**: Check environment variables

### Debug Commands
```bash
# Run specific test with verbose output
pytest tests/test_strategy.py::TestEarningsScanner::test_gap_detection -v -s

# Run with debugger
pytest tests/test_strategy.py --pdb

# Run with profiling
pytest tests/test_strategy.py --profile
```

## Test Maintenance

### Regular Tasks
- Update test data with market changes
- Review and update mock responses
- Performance benchmark updates
- Test environment cleanup
- Documentation updates

### Quarterly Reviews
- Test coverage analysis
- Performance regression testing
- Test data refresh
- CI/CD pipeline optimization

---

**Note**: Always run tests in paper trading mode when testing with real APIs to avoid unintended trades.

**Last Updated**: July 2024  
**Test Suite Version**: 1.0