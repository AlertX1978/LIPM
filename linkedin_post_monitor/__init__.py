"""
LinkedIn Post Monitor - Package Initialization
"""

__version__ = "1.0.0"
__author__ = "LIPM Development Team"
__description__ = "Automated LinkedIn company page monitoring with AI commentary and Telegram approval workflow"

from .encryption import EncryptionManager
from .config_manager import ConfigManager
from .linkedin_scraper import LinkedInScraper
from .ai_commentary import AICommentaryGenerator
from .telegram_bot import TelegramBotHandler
from .post_database import PostDatabase
from .monitor import LinkedInMonitor

__all__ = [
    "EncryptionManager",
    "ConfigManager",
    "LinkedInScraper",
    "AICommentaryGenerator",
    "TelegramBotHandler",
    "PostDatabase",
    "LinkedInMonitor",
]
