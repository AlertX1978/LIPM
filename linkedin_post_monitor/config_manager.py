"""
Configuration Manager - Handles encrypted settings with JSON persistence
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from .encryption import EncryptionManager


class ConfigManager:
    """Manages application configuration with encrypted sensitive fields."""
    
    # Default configuration template
    DEFAULT_CONFIG = {
        "linkedin": {
            "username": "",
            "password_encrypted": "",
            "company_page_url": "https://www.linkedin.com/company/industrialization-energy-services-co/posts/",
            "profile_url": "https://www.linkedin.com/in/aleksey-tkachyov-47852417/"
        },
        "telegram": {
            "bot_token_encrypted": "",
            "chat_id": "-4940774611"
        },
        "openai": {
            "api_key_encrypted": "",
            "model": "gpt-4o-mini",
            "system_prompt": "You are a professional LinkedIn content expert. Generate thoughtful, professional repost commentary that adds value and insights to the original post. Keep it concise (2-3 sentences), engaging, and appropriate for a professional LinkedIn audience.\n\nOriginal Post:\n[Text]\n\nGenerate professional commentary:"
        },
        "workflow": {
            "polling_frequency_minutes": 10,
            "posts_per_check": 3,
            "posts_lookback": 10,
            "auto_approve": False
        },
        "app": {
            "passphrase_test_encrypted": "",  # Used to verify passphrase
            "first_run": True
        }
    }
    
    # Encrypted field names
    ENCRYPTED_FIELDS = [
        "linkedin.password_encrypted",
        "telegram.bot_token_encrypted",
        "openai.api_key_encrypted",
        "app.passphrase_test_encrypted"
    ]
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to config JSON file (default: ./config.json)
        """
        if config_path is None:
            # Store config in same directory as the script
            self.config_path = Path(__file__).parent.parent / "config.json"
        else:
            self.config_path = Path(config_path)
        
        self.config: Dict[str, Any] = {}
        self.encryption_manager: Optional[EncryptionManager] = None
        self._load_or_create_config()
    
    def _load_or_create_config(self):
        """Load existing config or create default one."""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = self.DEFAULT_CONFIG.copy()
            self._save_config()
    
    def _save_config(self):
        """Save configuration to disk."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)
    
    def _get_nested_value(self, path: str) -> Any:
        """Get nested config value using dot notation."""
        keys = path.split('.')
        value = self.config
        for key in keys:
            value = value.get(key, {})
        return value
    
    def _set_nested_value(self, path: str, value: Any):
        """Set nested config value using dot notation."""
        keys = path.split('.')
        config_ref = self.config
        
        for key in keys[:-1]:
            if key not in config_ref:
                config_ref[key] = {}
            config_ref = config_ref[key]
        
        config_ref[keys[-1]] = value
    
    def unlock(self, passphrase: str) -> bool:
        """
        Unlock configuration with passphrase.
        
        Args:
            passphrase: Master passphrase for encryption
            
        Returns:
            True if passphrase is correct, False otherwise
        """
        self.encryption_manager = EncryptionManager(passphrase)
        
        # Verify passphrase if test data exists
        test_encrypted = self._get_nested_value("app.passphrase_test_encrypted")
        
        if test_encrypted:
            # Try to decrypt test data
            if not self.encryption_manager.verify_passphrase(test_encrypted):
                self.encryption_manager = None
                return False
        else:
            # First run - create test data
            test_string = "passphrase_valid"
            encrypted_test = self.encryption_manager.encrypt(test_string)
            self._set_nested_value("app.passphrase_test_encrypted", encrypted_test)
            self._set_nested_value("app.first_run", False)
            self._save_config()
        
        return True
    
    def is_unlocked(self) -> bool:
        """Check if configuration is unlocked."""
        return self.encryption_manager is not None
    
    def get(self, path: str, decrypt: bool = False) -> Optional[str]:
        """
        Get configuration value.
        
        Args:
            path: Dot-notation path (e.g., "linkedin.username")
            decrypt: Whether to decrypt the value
            
        Returns:
            Configuration value or None
        """
        value = self._get_nested_value(path)
        
        if decrypt and self.encryption_manager and value:
            return self.encryption_manager.decrypt(value)
        
        return value
    
    def set(self, path: str, value: str, encrypt: bool = False):
        """
        Set configuration value.
        
        Args:
            path: Dot-notation path (e.g., "linkedin.username")
            value: Value to set
            encrypt: Whether to encrypt the value
        """
        if not self.is_unlocked() and encrypt:
            raise RuntimeError("Configuration must be unlocked to encrypt values")
        
        if encrypt and self.encryption_manager:
            value = self.encryption_manager.encrypt(value)
        
        self._set_nested_value(path, value)
        self._save_config()
    
    def get_linkedin_credentials(self) -> Dict[str, str]:
        """Get decrypted LinkedIn credentials."""
        if not self.is_unlocked():
            raise RuntimeError("Configuration must be unlocked")
        
        return {
            "username": self.get("linkedin.username"),
            "password": self.get("linkedin.password_encrypted", decrypt=True),
            "company_page_url": self.get("linkedin.company_page_url"),
            "profile_url": self.get("linkedin.profile_url")
        }
    
    def get_telegram_credentials(self) -> Dict[str, str]:
        """Get decrypted Telegram credentials."""
        if not self.is_unlocked():
            raise RuntimeError("Configuration must be unlocked")
        
        return {
            "bot_token": self.get("telegram.bot_token_encrypted", decrypt=True),
            "chat_id": self.get("telegram.chat_id")
        }
    
    def get_openai_credentials(self) -> Dict[str, str]:
        """Get decrypted OpenAI credentials."""
        if not self.is_unlocked():
            raise RuntimeError("Configuration must be unlocked")
        
        api_key = self.get("openai.api_key_encrypted", decrypt=True)
        model = self.get("openai.model")
        system_prompt = self.get("openai.system_prompt")
        
        # Debug logging
        from .utils import logger
        if not api_key or not api_key.strip():
            logger.warning("⚠️ OpenAI API key is empty in configuration")
        else:
            logger.info(f"OpenAI API key retrieved: {api_key[:10]}... (length: {len(api_key)})")
        
        return {
            "api_key": api_key or "",
            "model": model or "gpt-4o-mini",
            "system_prompt": system_prompt or ""
        }
    
    def get_workflow_settings(self) -> Dict[str, Any]:
        """Get workflow settings."""
        # Helper to convert to int with fallback
        def to_int(value, default):
            try:
                return int(value) if value is not None else default
            except (ValueError, TypeError):
                return default
        
        return {
            "polling_frequency_minutes": to_int(self.get("workflow.polling_frequency_minutes"), 10),
            "posts_per_check": to_int(self.get("workflow.posts_per_check"), 3),
            "posts_lookback": to_int(self.get("workflow.posts_lookback"), 10),
            "auto_approve": self.get("workflow.auto_approve") or False
        }
    
    def update_linkedin_credentials(self, username: str, password: str, company_page_url: str):
        """Update LinkedIn credentials."""
        self.set("linkedin.username", username)
        self.set("linkedin.password_encrypted", password, encrypt=True)
        self.set("linkedin.company_page_url", company_page_url)
    
    def update_telegram_credentials(self, bot_token: str, chat_id: str):
        """Update Telegram credentials."""
        self.set("telegram.bot_token_encrypted", bot_token, encrypt=True)
        self.set("telegram.chat_id", chat_id)
    
    def update_openai_credentials(self, api_key: str, model: str = None, system_prompt: str = None):
        """Update OpenAI credentials."""
        self.set("openai.api_key_encrypted", api_key, encrypt=True)
        if model:
            self.set("openai.model", model)
        if system_prompt:
            self.set("openai.system_prompt", system_prompt)
    
    def is_configured(self) -> bool:
        """Check if all required credentials are configured."""
        if not self.is_unlocked():
            return False
        
        try:
            linkedin = self.get_linkedin_credentials()
            telegram = self.get_telegram_credentials()
            openai = self.get_openai_credentials()
            
            return all([
                linkedin["username"],
                linkedin["password"],
                linkedin["company_page_url"],
                telegram["bot_token"],
                telegram["chat_id"],
                openai["api_key"]
            ])
        except:
            return False


if __name__ == "__main__":
    # Test configuration manager
    import tempfile
    
    test_config_path = Path(tempfile.gettempdir()) / "test_config.json"
    
    # Create config manager
    config = ConfigManager(str(test_config_path))
    
    # Unlock with passphrase
    assert config.unlock("!Paralax1"), "Failed to unlock config"
    print("✅ Config unlocked")
    
    # Set some values
    config.update_linkedin_credentials(
        username="test@example.com",
        password="secret_password",
        company_page_url="https://linkedin.com/company/test"
    )
    print("✅ LinkedIn credentials set")
    
    # Retrieve values
    creds = config.get_linkedin_credentials()
    assert creds["username"] == "test@example.com"
    assert creds["password"] == "secret_password"
    print("✅ Credentials retrieved correctly")
    
    # Test wrong passphrase
    config2 = ConfigManager(str(test_config_path))
    assert not config2.unlock("wrong_password"), "Should fail with wrong passphrase"
    print("✅ Wrong passphrase test passed")
    
    # Cleanup
    test_config_path.unlink()
    print("✅ All tests passed!")
