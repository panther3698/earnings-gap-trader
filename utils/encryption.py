"""
Encryption utilities for sensitive data handling
"""
import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional, Union
import config


def generate_key() -> str:
    """Generate a new encryption key"""
    return Fernet.generate_key().decode()


def _get_fernet_instance(key: Optional[str] = None) -> Fernet:
    """Get Fernet instance with provided or default key"""
    if key is None:
        key = config.ENCRYPTION_KEY
    
    if not key:
        raise ValueError("No encryption key provided")
    
    # If key is a string, encode it
    if isinstance(key, str):
        key = key.encode()
    
    return Fernet(key)


def encrypt_data(data: Union[str, bytes], key: Optional[str] = None) -> str:
    """
    Encrypt data using Fernet symmetric encryption
    
    Args:
        data: Data to encrypt (string or bytes)
        key: Optional encryption key (uses config key if not provided)
        
    Returns:
        Base64 encoded encrypted data
    """
    try:
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        fernet = _get_fernet_instance(key)
        encrypted_data = fernet.encrypt(data)
        
        return base64.b64encode(encrypted_data).decode('utf-8')
        
    except Exception as e:
        raise ValueError(f"Encryption failed: {str(e)}")


def decrypt_data(encrypted_data: str, key: Optional[str] = None) -> str:
    """
    Decrypt data using Fernet symmetric encryption
    
    Args:
        encrypted_data: Base64 encoded encrypted data
        key: Optional encryption key (uses config key if not provided)
        
    Returns:
        Decrypted data as string
    """
    try:
        # Decode base64
        encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
        
        fernet = _get_fernet_instance(key)
        decrypted_data = fernet.decrypt(encrypted_bytes)
        
        return decrypted_data.decode('utf-8')
        
    except Exception as e:
        raise ValueError(f"Decryption failed: {str(e)}")


def encrypt_credentials(credentials: dict, key: Optional[str] = None) -> dict:
    """
    Encrypt sensitive credentials dictionary
    
    Args:
        credentials: Dictionary containing sensitive data
        key: Optional encryption key
        
    Returns:
        Dictionary with encrypted values
    """
    encrypted_creds = {}
    
    for field, value in credentials.items():
        if value and isinstance(value, str):
            encrypted_creds[field] = encrypt_data(value, key)
        else:
            encrypted_creds[field] = value
    
    return encrypted_creds


def decrypt_credentials(encrypted_credentials: dict, key: Optional[str] = None) -> dict:
    """
    Decrypt credentials dictionary
    
    Args:
        encrypted_credentials: Dictionary with encrypted values
        key: Optional encryption key
        
    Returns:
        Dictionary with decrypted values
    """
    decrypted_creds = {}
    
    for field, value in encrypted_credentials.items():
        if value and isinstance(value, str):
            try:
                decrypted_creds[field] = decrypt_data(value, key)
            except ValueError:
                # If decryption fails, assume value is not encrypted
                decrypted_creds[field] = value
        else:
            decrypted_creds[field] = value
    
    return decrypted_creds


def derive_key_from_password(password: str, salt: Optional[bytes] = None) -> tuple[str, bytes]:
    """
    Derive encryption key from password using PBKDF2
    
    Args:
        password: Password to derive key from
        salt: Optional salt (generates new if not provided)
        
    Returns:
        Tuple of (base64 encoded key, salt)
    """
    if salt is None:
        salt = os.urandom(16)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key.decode(), salt


def hash_sensitive_data(data: str) -> str:
    """
    Create a hash of sensitive data for verification purposes
    
    Args:
        data: Data to hash
        
    Returns:
        Base64 encoded hash
    """
    digest = hashes.Hash(hashes.SHA256())
    digest.update(data.encode('utf-8'))
    hash_bytes = digest.finalize()
    
    return base64.b64encode(hash_bytes).decode('utf-8')


def secure_compare(data1: str, data2: str) -> bool:
    """
    Securely compare two strings (constant time)
    
    Args:
        data1: First string
        data2: Second string
        
    Returns:
        True if strings match
    """
    if len(data1) != len(data2):
        return False
    
    result = 0
    for x, y in zip(data1, data2):
        result |= ord(x) ^ ord(y)
    
    return result == 0


class EncryptedConfig:
    """Helper class for managing encrypted configuration"""
    
    def __init__(self, key: Optional[str] = None):
        self.key = key or config.ENCRYPTION_KEY
        if not self.key:
            raise ValueError("Encryption key required")
    
    def encrypt_config(self, config_dict: dict) -> dict:
        """Encrypt sensitive fields in configuration"""
        sensitive_fields = [
            'kite_api_key',
            'kite_api_secret', 
            'kite_access_token',
            'telegram_bot_token',
            'email_password',
            'webhook_secret'
        ]
        
        encrypted_config = config_dict.copy()
        
        for field in sensitive_fields:
            if field in encrypted_config and encrypted_config[field]:
                encrypted_config[field] = encrypt_data(encrypted_config[field], self.key)
        
        return encrypted_config
    
    def decrypt_config(self, encrypted_config: dict) -> dict:
        """Decrypt sensitive fields in configuration"""
        sensitive_fields = [
            'kite_api_key',
            'kite_api_secret',
            'kite_access_token', 
            'telegram_bot_token',
            'email_password',
            'webhook_secret'
        ]
        
        decrypted_config = encrypted_config.copy()
        
        for field in sensitive_fields:
            if field in decrypted_config and decrypted_config[field]:
                try:
                    decrypted_config[field] = decrypt_data(decrypted_config[field], self.key)
                except ValueError:
                    # Field might not be encrypted
                    pass
        
        return decrypted_config
    
    def is_encrypted(self, data: str) -> bool:
        """Check if data appears to be encrypted"""
        try:
            base64.b64decode(data)
            # Try to decrypt
            decrypt_data(data, self.key)
            return True
        except Exception:
            return False


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a secure random token
    
    Args:
        length: Length of token in bytes
        
    Returns:
        Base64 encoded secure token
    """
    return base64.urlsafe_b64encode(os.urandom(length)).decode('utf-8')


def mask_sensitive_data(data: str, show_chars: int = 4) -> str:
    """
    Mask sensitive data for logging/display
    
    Args:
        data: Sensitive data to mask
        show_chars: Number of characters to show at start and end
        
    Returns:
        Masked string
    """
    if not data or len(data) <= show_chars * 2:
        return '*' * len(data) if data else ''
    
    return f"{data[:show_chars]}{'*' * (len(data) - show_chars * 2)}{data[-show_chars:]}"