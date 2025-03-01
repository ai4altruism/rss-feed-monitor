# src/utils.py

import os
import logging

def setup_logger():
    """
    Sets up a logger to log to both the console and a file in the logs directory.
    
    Returns:
        logger (logging.Logger): Configured logger instance.
    """
    logger = logging.getLogger("RSSFeedMonitor")
    logger.setLevel(logging.INFO)
    
    # Create logs directory if it doesn't exist
    if not os.path.exists("logs"):
        os.makedirs("logs")
    
    # File handler for logging to a file
    file_handler = logging.FileHandler("logs/app.log")
    file_handler.setLevel(logging.INFO)
    
    # Console handler for logging to the console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Formatter to include timestamp, module, level, and message
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add both handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
