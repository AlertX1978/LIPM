"""
Encryption Manager - AES-256-GCM encryption for sensitive credentials
"""

import os
import base64
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from typing import Optional


class EncryptionManager:
    """Handles encryption and decryption of sensitive data using AES-256-GCM."""
    
    def __init__(self, passphrase: str):
        """
        Initialize encryption manager with a passphrase.
        
        Args:
            passphrase: Master passphrase for encryption/decryption
        """
        self.passphrase = passphrase
        self._key = self._derive_key(passphrase)
    
    def _derive_key(self, passphrase: str) -> bytes:
        """
        Derive a 256-bit encryption key from passphrase using PBKDF2.
        
        Args:
            passphrase: The passphrase to derive key from
            
        Returns:
            32-byte encryption key
        """
        # Use SHA-256 to create a deterministic 32-byte key
        return hashlib.sha256(passphrase.encode('utf-8')).digest()
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string using AES-256-GCM.
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Base64-encoded encrypted string (includes nonce)
        """
        if not plaintext:
            return ""
        
        # Generate a random 96-bit nonce (12 bytes)
        nonce = os.urandom(12)
        
        # Create AESGCM cipher
        aesgcm = AESGCM(self._key)
        
        # Encrypt the plaintext
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        
        # Combine nonce + ciphertext and encode as base64
        encrypted_data = nonce + ciphertext
        return base64.b64encode(encrypted_data).decode('utf-8')
    
    def decrypt(self, encrypted: str) -> Optional[str]:
        """
        Decrypt encrypted string using AES-256-GCM.
        
        Args:
            encrypted: Base64-encoded encrypted string
            
        Returns:
            Decrypted plaintext string, or None if decryption fails
        """
        if not encrypted:
            return ""
        
        try:
            # Decode from base64
            encrypted_data = base64.b64decode(encrypted.encode('utf-8'))
            
            # Extract nonce (first 12 bytes) and ciphertext
            nonce = encrypted_data[:12]
            ciphertext = encrypted_data[12:]
            
            # Create AESGCM cipher
            aesgcm = AESGCM(self._key)
            
            # Decrypt the ciphertext
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode('utf-8')
            
        except (InvalidTag, ValueError, Exception) as e:
            # Invalid passphrase or corrupted data
            return None
    
    def verify_passphrase(self, test_encrypted: str) -> bool:
        """
        Verify if the passphrase is correct by attempting decryption.
        
        Args:
            test_encrypted: An encrypted string to test against
            
        Returns:
            True if passphrase is correct, False otherwise
        """
        if not test_encrypted:
            return True  # No data to verify against
        
        result = self.decrypt(test_encrypted)
        return result is not None


# Helper function for quick encryption/decryption
def encrypt_data(plaintext: str, passphrase: str) -> str:
    """Quick encrypt helper."""
    em = EncryptionManager(passphrase)
    return em.encrypt(plaintext)


def decrypt_data(encrypted: str, passphrase: str) -> Optional[str]:
    """Quick decrypt helper."""
    em = EncryptionManager(passphrase)
    return em.decrypt(encrypted)


if __name__ == "__main__":
    # Test encryption
    test_passphrase = "!Paralax1"
    test_data = "my_secret_password_123"
    
    em = EncryptionManager(test_passphrase)
    
    # Encrypt
    encrypted = em.encrypt(test_data)
    print(f"Encrypted: {encrypted}")
    
    # Decrypt
    decrypted = em.decrypt(encrypted)
    print(f"Decrypted: {decrypted}")
    
    # Verify
    assert decrypted == test_data, "Encryption/Decryption failed!"
    print("✅ Encryption test passed!")
    
    # Test wrong passphrase
    em_wrong = EncryptionManager("wrong_password")
    wrong_decrypt = em_wrong.decrypt(encrypted)
    assert wrong_decrypt is None, "Should fail with wrong passphrase!"
    print("✅ Wrong passphrase test passed!")
