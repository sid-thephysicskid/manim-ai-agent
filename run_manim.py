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
        process = subprocess.Popen(
            [sys.executable, "-m", "manim", "-qh", scene_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Stream output in real-time
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
                
        return_code = process.poll()
        return return_code == 0
        
    except Exception as e:
        print(f"Error running Manim: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_manim.py <scene_file>")
        sys.exit(1)
    
    scene_file = sys.argv[1]
    success = run_manim(scene_file)
    sys.exit(0 if success else 1)