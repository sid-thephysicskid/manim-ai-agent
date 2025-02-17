"""
Templates package for Manim code generation.

This package contains:
1. Example Manim scenes (templates/examples/) used for one-shot learning
2. API documentation (templates/api_docs/) used for context in prompts
"""

from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent
EXAMPLES_DIR = TEMPLATES_DIR / "examples"
API_DOCS_DIR = TEMPLATES_DIR / "api_docs"

# Ensure directories exist
EXAMPLES_DIR.mkdir(exist_ok=True)
API_DOCS_DIR.mkdir(exist_ok=True)

def get_example_template(name: str) -> str:
    """Read an example template file."""
    path = EXAMPLES_DIR / f"{name}.py"
    try:
        return path.read_text()
    except FileNotFoundError:
        raise ValueError(f"Template {name}.py not found in {EXAMPLES_DIR}")

def get_api_doc(name: str) -> str:
    """Read an API documentation file."""
    path = API_DOCS_DIR / f"{name}.py"
    try:
        return path.read_text()
    except FileNotFoundError:
        raise ValueError(f"API doc {name}.py not found in {API_DOCS_DIR}") 