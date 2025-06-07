import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path

def setup_logging(log_level=logging.INFO):
    """
    Configure the logging system with both file and console handlers.
    
    Args:
        log_level (int): The logging level to use (default: logging.INFO)
    
    Returns:
        logger: Configured logger instance
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Generate log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d")
    log_file = log_dir / f"taxonomy_audit_{timestamp}.log"
    
    # Create logger
    logger = logging.getLogger("TaxonomyAudit")
    logger.setLevel(log_level)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(module)s:%(lineno)d | %(funcName)s | %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s'
    )
    
    # File Handler - Rotating file handler to manage log file size
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(log_level)
    
    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(log_level)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Log initial message
    logger.info("Logging system initialized")
    
    return logger

# Custom log levels for different types of messages
AUDIT = 25  # Custom level between INFO and WARNING
logging.addLevelName(AUDIT, "AUDIT")

def audit(self, message, *args, **kwargs):
    """
    Custom audit log level method
    """
    if self.isEnabledFor(AUDIT):
        self._log(AUDIT, message, args, **kwargs)

# Add audit method to Logger class
logging.Logger.audit = audit

# Exception logging decorator
def log_exceptions(logger):
    """
    Decorator to log exceptions in functions
    
    Args:
        logger: Logger instance to use for logging
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Exception in {func.__name__}: {str(e)}")
                raise
        return wrapper
    return decorator 