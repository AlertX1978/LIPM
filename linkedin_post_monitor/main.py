"""
Main Entry Point - LinkedIn Post Monitor Application
"""

import sys
import os
from pathlib import Path

# Add package to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from linkedin_post_monitor.gui import LinkedInMonitorGUI
from linkedin_post_monitor.utils import logger


def check_browser_availability():
    """Check if Chrome browser is available."""
    import os
    
    if getattr(sys, 'frozen', False):
        # Running as executable - check for Chrome
        chrome_paths = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ]
        
        chrome_found = any(os.path.exists(path) for path in chrome_paths)
        
        if not chrome_found:
            logger.warning("=" * 60)
            logger.warning("⚠️ Google Chrome not detected on this system")
            logger.warning("LIPM requires Chrome to automate LinkedIn")
            logger.warning("Please install Chrome from: https://www.google.com/chrome/")
            logger.warning("=" * 60)
            return False
    
    return True


def main():
    """
    Main application entry point.
    """
    try:
        logger.info("=" * 60)
        logger.info("LinkedIn Post Monitor v1.0.0")
        logger.info("=" * 60)
        
        # Check browser availability
        check_browser_availability()
        
        # Create and run GUI
        app = LinkedInMonitorGUI()
        app.run()
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ Application interrupted by user")
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
