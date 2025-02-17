import logging
from datetime import datetime
from pathlib import Path
from .config import LOGS_DIR

def setup_question_logger(question: str) -> logging.Logger:
    """Set up a dedicated logger for each question."""
    # Create a sanitized filename from the question
    safe_name = question.lower()
    safe_name = "".join(c if c.isalnum() else "_" for c in safe_name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOGS_DIR / f"{safe_name}_{timestamp}.log"
    
    # Create a new logger
    logger = logging.getLogger(f"question_{safe_name}")
    logger.setLevel(logging.INFO)
    
    # Remove any existing handlers
    logger.handlers = []
    
    # Add file handler
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(fh)
    
    # Add console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(ch)
    
    return logger

# Setup root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
) 