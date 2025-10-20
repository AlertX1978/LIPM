"""
Utilities and Helper Functions
"""

import logging
import colorlog
import sys
import os
from pathlib import Path
from typing import Optional
from datetime import datetime


def get_app_directory() -> Path:
    """
    Get the application directory.
    
    When running as PyInstaller executable, returns the directory containing the .exe
    When running as Python script, returns the parent directory of the package
    
    Returns:
        Path to application directory
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return Path(sys.executable).parent
    else:
        # Running as Python script
        return Path(__file__).parent.parent


def setup_logger(name: str, log_file: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    """
    Set up a colored logger with file and console handlers.
    
    Args:
        name: Logger name
        log_file: Optional log file path (relative to app directory if not absolute)
        level: Logging level
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Console handler with colors
    console_handler = colorlog.StreamHandler()
    console_handler.setLevel(level)
    console_formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        
        # Make path absolute relative to app directory if it's relative
        if not log_path.is_absolute():
            log_path = get_app_directory() / log_path
        
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


def format_timestamp(dt: datetime) -> str:
    """Format datetime for display."""
    return dt.strftime("%B %d, %Y at %I:%M %p")


def truncate_text(text: str, max_length: int = 200) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def sanitize_filename(filename: str) -> str:
    """Remove invalid characters from filename."""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename


def generate_request_id() -> str:
    """Generate a unique request ID."""
    import uuid
    return str(uuid.uuid4())[:8]


# Global logger instance
logger = setup_logger('LIPM', log_file='logs/lipm.log')


if __name__ == "__main__":
    # Test logger
    test_logger = setup_logger('TestLogger')
    test_logger.debug("Debug message")
    test_logger.info("Info message")
    test_logger.warning("Warning message")
    test_logger.error("Error message")
    print("✅ Logger test passed!")
