
import subprocess
import os

def build_exe():
    # Main script path
    main_script = "main.py"

    # Check if the file exists
    if not os.path.exists(main_script):
        print(f"Error: {main_script} not found.")
        return

    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--onefile",  # Create a single executable file
        "--windowed",  # No console (for GUI apps)
        "--name=JOSM_Tagger",  # Executable name
        f"--icon=resources/josm_tagger.ico",  # Icon
        "--add-data", "resources;resources",  # Include the resources folder
        "--add-data", "codes.json;.",  # Include codes.json
        "--add-data", "config.json;.",  # Include config.json
        main_script
    ]

    try:
        print("Starting build with PyInstaller...")
        subprocess.run(cmd, check=True)
        print("Build completed! The executable is in the 'dist' folder.")
    except subprocess.CalledProcessError as e:
        print(f"Error during build: {e}")
    except FileNotFoundError:
        print("PyInstaller not found. Make sure it is installed (pip install pyinstaller).")

if __name__ == "__main__":
    build_exe()
