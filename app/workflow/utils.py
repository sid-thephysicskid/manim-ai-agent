import re
import tempfile
import logging
from pathlib import Path
from app.core.config import GENERATED_DIR, LOGS_DIR, RUN_TIMESTAMP

def log_state_transition(node_name: str, input_state: dict, output_state: dict):
    """Log the state transition for a node, showing what changed."""
    logger = logging.getLogger(__name__)
    logger.info(f"\n{'='*50}\nNode: {node_name}")
    
    # Log input state
    logger.info("Input State:")
    for k, v in input_state.items():
        if k in ['generated_code', 'plan'] and v:
            logger.info(f"  {k}: <{len(str(v))} chars>")
        else:
            logger.info(f"  {k}: {v}")
    
    # Log changes between input and output states
    logger.info("Changes:")
    for k in output_state:
        if k in input_state:
            if output_state[k] != input_state[k]:
                if k in ['generated_code', 'plan']:
                    logger.info(f"  {k}: <updated - {len(str(output_state[k]))} chars>")
                else:
                    logger.info(f"  {k}: {input_state[k]} -> {output_state[k]}")
        else:
            logger.info(f"  + {k}: {output_state[k]}")
    
    # Log error if present
    if output_state.get('error'):
        logger.error(f"Error in {node_name}: {output_state['error']}")
    
    logger.info(f"{'='*50}\n")
    return output_state

def create_temp_dir():
    """Create a temporary directory for Manim operations."""
    temp_dir = tempfile.mkdtemp(prefix="manim_")
    logging.getLogger(__name__).info(f"Created temporary directory at: {temp_dir}")
    return temp_dir

def extract_concept(text: str) -> str:
    """Extract the underlying concept from a user input string."""
    text = text.lower().strip()
    prefixes = ["how to", "what is", "explain", "describe", "why is", "tell me", "show me"]
    for prefix in prefixes:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
            break
    text = re.sub(r'[^\w\s]', '', text)
    concept = re.sub(r'\s+', '_', text)
    return concept

def generate_scene_filename(topic: str) -> str:
    """Generate a unique scene filename from the user input."""
    concept = extract_concept(topic)
    timestamp = RUN_TIMESTAMP[:13]
    filename = f"{concept}_{timestamp}.py"
    return str(GENERATED_DIR / filename)

def setup_question_logger(question: str) -> logging.Logger:
    """Set up a dedicated logger for each question."""
    safe_name = re.sub(r'[^\w\s-]', '', question.lower())
    safe_name = re.sub(r'[-\s]+', '_', safe_name)
    timestamp = RUN_TIMESTAMP
    log_file = LOGS_DIR / f"{safe_name}_{timestamp}.log"
    
    logger = logging.getLogger(f"question_{safe_name}")
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
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