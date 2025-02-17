import os
from pathlib import Path
from dotenv import load_dotenv
from cachetools import TTLCache
from datetime import datetime

# Load environment variables
load_dotenv()

# Global Constants
OPENAI_MODEL = "o3-mini"
MANIM_QUALITY = "-ql"  # Low quality for faster rendering
EXECUTION_TIMEOUT = 180  # seconds

# Cache Configuration
# TODO: Replace with more robust caching mechanism (e.g., Redis) for production
ERROR_CACHE = TTLCache(maxsize=100, ttl=3600)  # 1 hour cache

# Directory Configuration
BASE_DIR = Path(__file__).parent.parent.parent
GENERATED_DIR = BASE_DIR / "generated"
LOGS_DIR = GENERATED_DIR / "logs"

# Ensure directories exist
GENERATED_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Valid Colors (for Manim)
VALID_COLORS = [
    "blue", "teal", "green", "yellow", "gold", "red", "maroon", 
    "purple", "pink", "light_pink", "orange", "light_brown", 
    "dark_brown", "gray_brown", "white", "black", "lighter_gray", 
    "light_gray", "gray", "dark_gray", "darker_gray", "blue_a", 
    "blue_b", "blue_c", "blue_d", "blue_e", "pure_blue"
]

# Run timestamp
RUN_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
