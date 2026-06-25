
# -------------------------------------------------------------------------
# Build Windows executable with PyInstaller

import subprocess
import os
import sys

from pathlib import Path
import shutil


def build_exe():
    # Main script path

    main_script = "main.py"

    sourcedir = Path(__file__).parent
    print(f'Source directory: {sourcedir}')

    targetdir = Path(sourcedir / 'dist')
    targetdir_setup = Path(sourcedir / 'dist_installer')

    print(f'Target directory: {targetdir}')

    shutil.rmtree(targetdir, ignore_errors=True)
    shutil.rmtree(targetdir_setup, ignore_errors=True)

    # Check if the file exists
    if not os.path.exists(main_script):
        print(f"Error: {main_script} not found.")
        return

    build = False
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
        build = True
    except subprocess.CalledProcessError as e:
        print(f"Error during build: {e}")

    except FileNotFoundError:
        print("PyInstaller not found. Make sure it is installed (pip install pyinstaller).")

    # -------------------------------------------------------------------------
    # Copy additional files into dist folder
    if build:
        print('\nCopying additional files into dist folder')
        files_to_copy = [
            "codes.json",
            "config.json",
            "resources",
        ]

        for item in files_to_copy:
            src = sourcedir / item

            if not src.exists():
                print(f"Missing: {src}")
                continue

            if src.is_file():
                # Copy single file
                print(f"Copying file: {src} → {targetdir}")
                shutil.copy2(sourcedir / src, targetdir / src.name)
            else:
                dest = targetdir / src.name
                print(f"Copying directory: {src} → {dest}")
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(src, dest)

        print("All files copied successfully.")

        # -------------------------------------------------------------------------
        # Create ZIP archive
        dist_dir = Path(__file__).parent / "dist"
        zip_path = dist_dir / "Josm_Tagger"

        zip_temp = Path(__file__).parent / "Josm_Tagger"

        print(f"\nCreating ZIP archive: {zip_path}.zip")

        shutil.make_archive(
            base_name=str(zip_temp),  #  without .zip
            format="zip",
            root_dir=dist_dir  # zip everything inside dist folder.
        )

        final_zip = dist_dir / "Josm_Tagger.zip"
        shutil.move(f"{zip_temp}.zip", final_zip)   # This will be the .zip distro
        print(f"ZIP created successfully at: {final_zip}")

        # -------------------------------------------------------------------------
        # Build the installer
        print("\nBuilding the Windows installer...")
        installer_script = sourcedir / "build_win_installer.py"
        try:
            subprocess.run([sys.executable, str(installer_script)], check=True)
            print("Windows installer build completed.")
        except subprocess.CalledProcessError as e:
            print(f"Error during installer build: {e}")
        except FileNotFoundError:
            print(f"Error: {installer_script} not found.")

    else:
        print("Build failed. Please check the error messages above.")

if __name__ == "__main__":
    build_exe()
