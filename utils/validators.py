"""
Data validation utilities for trading system
"""
import re
from typing import Union, Optional, List
from datetime import datetime, time
from decimal import Decimal, ROUND_HALF_UP


def validate_symbol(symbol: str) -> tuple[bool, str]:
    """
    Validate stock symbol format
    
    Args:
        symbol: Stock symbol to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not symbol:
        return False, "Symbol cannot be empty"
    
    # Remove .NS suffix if present
    clean_symbol = symbol.replace('.NS', '')
    
    # Check length (NSE symbols are typically 1-10 characters)
    if len(clean_symbol) < 1 or len(clean_symbol) > 10:
        return False, "Symbol must be 1-10 characters long"
    
    # Check format (alphanumeric, possibly with & or -)
    if not re.match(r'^[A-Z0-9&-]+$', clean_symbol):
        return False, "Symbol must contain only uppercase letters, numbers, & or -"
    
    # Check for common NSE symbols patterns
    valid_patterns = [
        r'^[A-Z]{2,10}$',  # Standard symbols like RELIANCE, TCS
        r'^[A-Z]+\d+$',    # Symbols with numbers like M&M
        r'^[A-Z]+&[A-Z]+$' # Symbols with & like M&MFIN
    ]
    
    if not any(re.match(pattern, clean_symbol) for pattern in valid_patterns):
        return False, "Invalid symbol format"
    
    return True, ""


def validate_price(price: Union[float, str, Decimal]) -> tuple[bool, str]:
    """
    Validate price value
    
    Args:
        price: Price to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        price_decimal = Decimal(str(price))
    except (ValueError, TypeError):
        return False, "Price must be a valid number"
    
    if price_decimal <= 0:
        return False, "Price must be positive"
    
    if price_decimal > Decimal('100000'):
        return False, "Price cannot exceed ₹100,000"
    
    # Check decimal places (NSE allows up to 2 decimal places)
    if price_decimal.as_tuple().exponent < -2:
        return False, "Price cannot have more than 2 decimal places"
    
    return True, ""


def validate_quantity(quantity: Union[int, str]) -> tuple[bool, str]:
    """
    Validate quantity value
    
    Args:
        quantity: Quantity to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        qty = int(quantity)
    except (ValueError, TypeError):
        return False, "Quantity must be a valid integer"
    
    if qty <= 0:
        return False, "Quantity must be positive"
    
    if qty > 100000:
        return False, "Quantity cannot exceed 100,000 shares"
    
    return True, ""


def validate_percentage(percentage: Union[float, str, Decimal], min_val: float = 0, max_val: float = 100) -> tuple[bool, str]:
    """
    Validate percentage value
    
    Args:
        percentage: Percentage to validate
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        pct = float(percentage)
    except (ValueError, TypeError):
        return False, "Percentage must be a valid number"
    
    if pct < min_val:
        return False, f"Percentage cannot be less than {min_val}%"
    
    if pct > max_val:
        return False, f"Percentage cannot exceed {max_val}%"
    
    return True, ""


def validate_email(email: str) -> tuple[bool, str]:
    """
    Validate email address format
    
    Args:
        email: Email address to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return False, "Email cannot be empty"
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email):
        return False, "Invalid email format"
    
    if len(email) > 254:
        return False, "Email address too long"
    
    return True, ""


def validate_phone_number(phone: str) -> tuple[bool, str]:
    """
    Validate phone number format (Indian format)
    
    Args:
        phone: Phone number to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not phone:
        return False, "Phone number cannot be empty"
    
    # Remove spaces, dashes, and brackets
    clean_phone = re.sub(r'[\s\-\(\)]', '', phone)
    
    # Check for Indian phone number patterns
    indian_patterns = [
        r'^\+91[6-9]\d{9}$',  # +91 followed by 10 digits starting with 6-9
        r'^91[6-9]\d{9}$',    # 91 followed by 10 digits starting with 6-9
        r'^[6-9]\d{9}$'       # 10 digits starting with 6-9
    ]
    
    if not any(re.match(pattern, clean_phone) for pattern in indian_patterns):
        return False, "Invalid Indian phone number format"
    
    return True, ""


def validate_telegram_chat_id(chat_id: str) -> tuple[bool, str]:
    """
    Validate Telegram chat ID format
    
    Args:
        chat_id: Telegram chat ID to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not chat_id:
        return False, "Chat ID cannot be empty"
    
    # Telegram chat IDs are typically negative integers for groups/channels
    # or positive integers for users
    if not re.match(r'^-?\d+$', chat_id):
        return False, "Invalid Telegram chat ID format"
    
    chat_id_int = int(chat_id)
    
    # Basic range validation
    if abs(chat_id_int) > 10**12:  # Arbitrary large number
        return False, "Chat ID out of valid range"
    
    return True, ""


def validate_api_key(api_key: str, min_length: int = 16) -> tuple[bool, str]:
    """
    Validate API key format
    
    Args:
        api_key: API key to validate
        min_length: Minimum length requirement
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not api_key:
        return False, "API key cannot be empty"
    
    if len(api_key) < min_length:
        return False, f"API key must be at least {min_length} characters"
    
    if len(api_key) > 100:
        return False, "API key too long"
    
    # Check for reasonable characters (alphanumeric and common special chars)
    if not re.match(r'^[a-zA-Z0-9_\-\.]+$', api_key):
        return False, "API key contains invalid characters"
    
    return True, ""


def validate_time_range(start_time: str, end_time: str) -> tuple[bool, str]:
    """
    Validate time range format and logic
    
    Args:
        start_time: Start time in HH:MM format
        end_time: End time in HH:MM format
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    time_pattern = r'^([01]?\d|2[0-3]):([0-5]?\d)$'
    
    if not re.match(time_pattern, start_time):
        return False, "Invalid start time format (use HH:MM)"
    
    if not re.match(time_pattern, end_time):
        return False, "Invalid end time format (use HH:MM)"
    
    try:
        start = datetime.strptime(start_time, '%H:%M').time()
        end = datetime.strptime(end_time, '%H:%M').time()
        
        if start >= end:
            return False, "Start time must be before end time"
        
        return True, ""
        
    except ValueError:
        return False, "Invalid time values"


def validate_trading_config(config: dict) -> tuple[bool, List[str]]:
    """
    Validate complete trading configuration
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Validate required fields
    required_fields = [
        'max_position_size',
        'risk_per_trade', 
        'stop_loss_percentage',
        'target_percentage',
        'max_daily_loss',
        'max_open_positions'
    ]
    
    for field in required_fields:
        if field not in config:
            errors.append(f"Missing required field: {field}")
    
    # Validate numeric fields
    if 'max_position_size' in config:
        if not isinstance(config['max_position_size'], (int, float)) or config['max_position_size'] <= 0:
            errors.append("Max position size must be a positive number")
    
    if 'risk_per_trade' in config:
        is_valid, error = validate_percentage(config['risk_per_trade'] * 100, 0.1, 10)
        if not is_valid:
            errors.append(f"Risk per trade: {error}")
    
    if 'stop_loss_percentage' in config:
        is_valid, error = validate_percentage(config['stop_loss_percentage'] * 100, 0.5, 20)
        if not is_valid:
            errors.append(f"Stop loss percentage: {error}")
    
    if 'target_percentage' in config:
        is_valid, error = validate_percentage(config['target_percentage'] * 100, 1, 50)
        if not is_valid:
            errors.append(f"Target percentage: {error}")
    
    if 'max_daily_loss' in config:
        if not isinstance(config['max_daily_loss'], (int, float)) or config['max_daily_loss'] <= 0:
            errors.append("Max daily loss must be a positive number")
    
    if 'max_open_positions' in config:
        if not isinstance(config['max_open_positions'], int) or config['max_open_positions'] <= 0:
            errors.append("Max open positions must be a positive integer")
    
    # Validate logical relationships
    if 'stop_loss_percentage' in config and 'target_percentage' in config:
        if config['target_percentage'] <= config['stop_loss_percentage']:
            errors.append("Target percentage should be greater than stop loss percentage")
    
    return len(errors) == 0, errors


def validate_order_params(order_params: dict) -> tuple[bool, List[str]]:
    """
    Validate order parameters
    
    Args:
        order_params: Order parameters dictionary
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Validate symbol
    if 'symbol' in order_params:
        is_valid, error = validate_symbol(order_params['symbol'])
        if not is_valid:
            errors.append(f"Symbol: {error}")
    else:
        errors.append("Symbol is required")
    
    # Validate quantity
    if 'quantity' in order_params:
        is_valid, error = validate_quantity(order_params['quantity'])
        if not is_valid:
            errors.append(f"Quantity: {error}")
    else:
        errors.append("Quantity is required")
    
    # Validate price (if provided)
    if 'price' in order_params and order_params['price'] is not None:
        is_valid, error = validate_price(order_params['price'])
        if not is_valid:
            errors.append(f"Price: {error}")
    
    # Validate order type
    valid_order_types = ['MARKET', 'LIMIT', 'SL', 'SL-M']
    if 'order_type' in order_params:
        if order_params['order_type'] not in valid_order_types:
            errors.append(f"Order type must be one of: {', '.join(valid_order_types)}")
    
    # Validate transaction type
    valid_transaction_types = ['BUY', 'SELL']
    if 'transaction_type' in order_params:
        if order_params['transaction_type'] not in valid_transaction_types:
            errors.append(f"Transaction type must be one of: {', '.join(valid_transaction_types)}")
    
    return len(errors) == 0, errors


def sanitize_input(input_str: str, max_length: int = 255) -> str:
    """
    Sanitize user input by removing potentially harmful characters
    
    Args:
        input_str: Input string to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not input_str:
        return ""
    
    # Remove control characters and excessive whitespace
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', input_str)
    sanitized = re.sub(r'\s+', ' ', sanitized)
    sanitized = sanitized.strip()
    
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized


def validate_json_schema(data: dict, required_fields: List[str], optional_fields: List[str] = None) -> tuple[bool, List[str]]:
    """
    Validate JSON data against a simple schema
    
    Args:
        data: Data to validate
        required_fields: List of required field names
        optional_fields: List of optional field names
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    if not isinstance(data, dict):
        return False, ["Data must be a dictionary"]
    
    # Check required fields
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")
    
    # Check for unexpected fields
    allowed_fields = set(required_fields + (optional_fields or []))
    unexpected_fields = set(data.keys()) - allowed_fields
    
    if unexpected_fields:
        errors.append(f"Unexpected fields: {', '.join(unexpected_fields)}")
    
    return len(errors) == 0, errors