"""
API Key Manager for encrypted storage of OpenAI API keys.

Provides secure encryption and decryption of API keys using Fernet symmetric encryption.
Keys are stored encrypted in the data/config directory.
"""

import os
import base64
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import logging

logger = logging.getLogger(__name__)


class APIKeyManager:
    """
    Manages encrypted storage and retrieval of OpenAI API keys.
    
    Uses Fernet symmetric encryption with a key derived from a master password.
    The master password is derived from a combination of machine-specific and
    application-specific data to ensure security while allowing persistence.
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize API Key Manager.
        
        Args:
            config_dir: Directory to store encrypted key file. If None, uses data/config/
        """
        if config_dir is None:
            # Get data directory
            project_root = Path(__file__).parent.parent.parent
            config_dir = project_root / "data" / "config"
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.encrypted_key_file = self.config_dir / "encrypted_api_key.dat"
        self._cipher_suite = None
    
    def _get_encryption_key(self) -> bytes:
        """
        Generate encryption key from machine-specific and application-specific data.
        
        This creates a deterministic key that is unique to this machine/application
        but doesn't require user to remember a password.
        
        Returns:
            bytes: Encryption key for Fernet
        """
        # Use combination of machine-specific and application-specific data
        # This ensures key is unique per machine but doesn't require user password
        salt_data = b"stat_test_build_nl_sql_api_key_manager_v1"
        
        # Get some machine-specific data (username, home directory)
        machine_data = (
            os.getenv("USER", "default_user").encode() +
            str(Path.home()).encode() +
            salt_data
        )
        
        # Derive key using PBKDF2HMAC
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt_data,
            iterations=100000,
            backend=default_backend()
        )
        
        key = kdf.derive(machine_data)
        return base64.urlsafe_b64encode(key)
    
    def _get_cipher_suite(self) -> Fernet:
        """Get or create Fernet cipher suite."""
        if self._cipher_suite is None:
            key = self._get_encryption_key()
            self._cipher_suite = Fernet(key)
        return self._cipher_suite
    
    def save_api_key(self, api_key: str) -> bool:
        """
        Encrypt and save API key to disk.
        
        Args:
            api_key: OpenAI API key to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not api_key or not api_key.strip():
                logger.warning("Attempted to save empty API key")
                return False
            
            # Encrypt the API key
            cipher_suite = self._get_cipher_suite()
            encrypted_key = cipher_suite.encrypt(api_key.encode('utf-8'))
            
            # Save to file
            with open(self.encrypted_key_file, 'wb') as f:
                f.write(encrypted_key)
            
            logger.info("API key saved successfully (encrypted)")
            return True
        except Exception as e:
            logger.error(f"Failed to save API key: {e}", exc_info=True)
            return False
    
    def load_api_key(self) -> Optional[str]:
        """
        Load and decrypt API key from disk.
        
        Returns:
            Decrypted API key, or None if not found or error occurred
        """
        try:
            if not self.encrypted_key_file.exists():
                logger.debug("No saved API key found")
                return None
            
            # Read encrypted key
            with open(self.encrypted_key_file, 'rb') as f:
                encrypted_key = f.read()
            
            # Decrypt
            cipher_suite = self._get_cipher_suite()
            decrypted_key = cipher_suite.decrypt(encrypted_key)
            
            api_key = decrypted_key.decode('utf-8')
            logger.info("API key loaded successfully (decrypted)")
            return api_key
        except Exception as e:
            logger.error(f"Failed to load API key: {e}", exc_info=True)
            return None
    
    def has_saved_key(self) -> bool:
        """
        Check if a saved API key exists.
        
        Returns:
            True if encrypted key file exists, False otherwise
        """
        return self.encrypted_key_file.exists()
    
    def clear_api_key(self) -> bool:
        """
        Delete saved API key.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.encrypted_key_file.exists():
                self.encrypted_key_file.unlink()
                logger.info("API key cleared successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to clear API key: {e}", exc_info=True)
            return False
