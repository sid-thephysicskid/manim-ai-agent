import logging
from datetime import datetime
from pathlib import Path
from app.core.config import LOGS_DIR
from pythonjsonlogger.json import JsonFormatter

def setup_question_logger(question: str) -> logging.Logger:
    """Setup a logger for a specific question."""
    logger = logging.getLogger(f"question_{hash(question)}")
    if not logger.handlers:  # Only add handler if none exists
        # Create a sanitized filename from the question
        safe_name = question.lower()
        safe_name = "".join(c if c.isalnum() else "_" for c in safe_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = LOGS_DIR / f"{safe_name}_{timestamp}.log"
        
        # Create a new logger
        logger.setLevel(logging.INFO)
        
        # Remove any existing handlers
        logger.handlers = []
        # create a json formatter for structured logging
        formatter = JsonFormatter('%(asctime)s - %(levelname)s - %(message)s')
        # Add file handler
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.INFO)
        # fh.setFormatter(logging.Formatter(
        #     '%(asctime)s - %(levelname)s - %(message)s',
        #     datefmt='%Y-%m-%d %H:%M:%S'
        # ))
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
        # Add console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        # ch.setFormatter(logging.Formatter(
        #     '%(asctime)s - %(levelname)s - %(message)s',
        #     datefmt='%Y-%m-%d %H:%M:%S'
        # ))
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    
    return logger

# Setup root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
) 