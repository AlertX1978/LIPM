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


def main():
    """
    Main application entry point.
    """
    try:
        logger.info("=" * 60)
        logger.info("LinkedIn Post Monitor v1.0.0")
        logger.info("=" * 60)
        
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
