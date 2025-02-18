import os
import sys
import subprocess

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

def run_manim(scene_file):
    # Convert relative path to absolute path
    scene_file = os.path.abspath(scene_file)
    
    try:
        # Use sys.executable to ensure we use the Python from the virtual environment
        result = subprocess.run(
            [sys.executable, "-m", "manim", "-ql", scene_file],
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running Manim:\n{e.stdout}\n{e.stderr}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_manim.py <scene_file>")
        sys.exit(1)
    
    scene_file = sys.argv[1]
    success = run_manim(scene_file)
    sys.exit(0 if success else 1)