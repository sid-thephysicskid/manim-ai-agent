import os
import sys
from pathlib import Path
import subprocess

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def main():
    if len(sys.argv) < 2:
        print("Usage: python render_scene.py <scene_file>")
        sys.exit(1)
    
    scene_file = sys.argv[1]
    quality = sys.argv[2] if len(sys.argv) > 2 else "-ql"
    
    # Run manim with the correct Python path
    subprocess.run([
        "manim",
        quality,
        scene_file
    ], env={**os.environ, "PYTHONPATH": f"{os.environ.get('PYTHONPATH', '')}:{project_root}"})

if __name__ == "__main__":
    main() 