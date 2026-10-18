# src/utils.py

import os
import logging

def setup_logger():
    """
    Sets up a logger to log to both the console and a file in the logs directory.
    
    Returns:
        logger (logging.Logger): Configured logger instance.
    """
    # Create logs directory if it doesn't exist
    if not os.path.exists("logs"):
        os.makedirs("logs")

    # Configure the root logger, not just the named one: every module logs
    # through root `logging.info`. force=True replaces the default stderr
    # handler that the first root logging call installs, which otherwise
    # dropped module INFO lines and printed named-logger lines twice.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("logs/app.log"), logging.StreamHandler()],
        force=True,
    )
    logger = logging.getLogger("RSSFeedMonitor")
    logger.setLevel(logging.INFO)
    for h in list(logger.handlers):  # handlers from an earlier call would duplicate lines
        logger.removeHandler(h)
    return logger


# Model families that answer without hidden reasoning tokens. Every newer
# OpenAI family (gpt-5*, gpt-6*, o-series) reasons first, and that reasoning
# counts against max_completion_tokens: a cap sized for a direct answer
# comes back empty. Listing the old families, rather than the new ones,
# keeps the next family from silently hitting that trap.
NON_REASONING_PREFIXES = ("gpt-4", "gpt-3.5")


def is_reasoning_model(model):
    """Return True unless the model belongs to a known non-reasoning family."""
    return not model.startswith(NON_REASONING_PREFIXES)
