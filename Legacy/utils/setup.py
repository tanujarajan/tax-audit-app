# setup.py
# Contains setup functions

import logging
from .logging_setup import setup_logging

def initialize_environment():
    """
    Performs initial setup tasks including logging configuration.
    
    Returns:
        logger: Configured logger instance
    """
    # Initialize logging
    logger = setup_logging()
    logger.info("Initializing environment...")
    
    try:
        # Add any additional environment checks here
        # For example, checking Python version, required packages, etc.
        logger.info("Environment initialization completed successfully")
        return logger
    except Exception as e:
        logger.exception("Failed to initialize environment")
        raise
