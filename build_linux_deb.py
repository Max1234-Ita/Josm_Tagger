# Build a .deb package for Linux Ubuntu/Mint to install Josm Tagger as a regular app


import argparse
import os
import platform
import ast
import re
import shutil
import subprocess
import sys
from pathlib import Path


APP_NAME = "JOSM Tagger"
PACKAGE_NAME = "josm-tagger"
EXECUTABLE_NAME = "JOSM_Tagger"
BIN_NAME = "josm-tagger"
PROJECT_ROOT = Path(__file__).resolve().parent
BUILD_ROOT = PROJECT_ROOT / "build" / "linux_deb"
DIST_ROOT = PROJECT_ROOT / "dist" / "linux"


def run(cmd, cwd=PROJECT_ROOT):
    print(" ".join(str(part) for part in cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def read_version():
    def _read_version_from_text(path, variable_names):
        text = path.read_text(encoding="utf-8")

        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError:
            tree = None

        if tree is not None:
            constants = {}
            imports = {}

            for node in ast.walk(tree):
                if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    target = node.targets[0].id
                    value = node.value
                    if isinstance(value, ast.Constant) and isinstance(value.value, str):
                        constants[target] = value.value
                    elif isinstance(value, ast.Name) and value.id in constants:
                        constants[target] = constants[value.id]
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        imports[alias.asname or alias.name] = (node.module, alias.name)

            for name in variable_names:
                if name in constants:
                    return constants[name]

            for name in variable_names:
                if name in imports:
                    module, imported_name = imports[name]
                    if module == "app_metadata" and imported_name == "APP_VERSION":
                        return _read_version_from_text(PROJECT_ROOT / "app_metadata.py", ("APP_VERSION",))

        for name in variable_names:
            match = re.search(
                rf"^{re.escape(name)}\s*=\s*['\"]([^'\"]+)['\"]",
                text,
                re.MULTILINE,
            )
            if match:
                return match.group(1)

        raise RuntimeError(f"Cannot find version in {path.name}")

    for candidate, names in (
        (PROJECT_ROOT / "main.py", ("appversion",)),
        (PROJECT_ROOT / "app_metadata.py", ("APP_VERSION",)),
    ):
        if candidate.exists():
            try:
                return _read_version_from_text(candidate, names)
            except RuntimeError:
                continue

    raise RuntimeError("Cannot find app version in main.py or app_metadata.py")


def detect_arch():
    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        return "amd64"
    if machine in ("aarch64", "arm64"):
        return "arm64"
    if machine.startswith("arm"):
        return "armhf"
    return machine


def require_tool(name):
    if shutil.which(name) is None:
        raise RuntimeError(f"Required tool not found: {name}")


def pyinstaller_cmd():
    try:
        subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        return [sys.executable, "-m", "PyInstaller"]
    except subprocess.CalledProcessError:
        pass

    if shutil.which("pyinstaller") is not None:
        return ["pyinstaller"]

    raise RuntimeError(
        "PyInstaller not found. Install it with: "
        f"{sys.executable} -m pip install pyinstaller"
    )


def pyinstaller_add_data(source, target):
    return f"{source}:{target}"


def clean():
    shutil.rmtree(BUILD_ROOT, ignore_errors=True)
    DIST_ROOT.mkdir(parents=True, exist_ok=True)


def build_pyinstaller():
    # Trova la libreria Python condivisa usata dall'ambiente di build
    python_lib_path = None
    try:
        # Questo comando cerca il percorso della libreria condivisa di Python
        # che l'interprete corrente sta usando.
        result = subprocess.run(
            [sys.executable, "-c", "import sysconfig; print(sysconfig.get_config_var('LIBDIR'))"],
            capture_output=True, text=True, check=True
        )
        lib_dir = result.stdout.strip()
        
        result = subprocess.run(
            [sys.executable, "-c", "import sysconfig; print(sysconfig.get_config_var('LDLIBRARY'))"],
            capture_output=True, text=True, check=True
        )
        lib_name = result.stdout.strip()

        if lib_dir and lib_name:
            candidate_path = Path(lib_dir) / lib_name
            if candidate_path.exists():
                python_lib_path = candidate_path
            else: # Fallback per nomi di libreria comuni (es. libpython3.14.so.1.0)
                python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
                candidate_path = Path(lib_dir) / f"libpython{python_version}.so.1.0"
                if candidate_path.exists():
                    python_lib_path = candidate_path
                else:
                    candidate_path = Path(lib_dir) / f"libpython{python_version}.so"
                    if candidate_path.exists():
                        python_lib_path = candidate_path

    except Exception as e:
        print(f"Warning: Could not determine Python shared library path: {e}")
    
    if python_lib_path:
        print(f"Detected Python shared library: {python_lib_path}")
    else:
        print("Warning: Python shared library not found. PyInstaller might link dynamically.")


    cmd = [
        *pyinstaller_cmd(),
        "--clean",
        "--noconfirm",
        "--onefile",
        "--windowed",
        f"--name={EXECUTABLE_NAME}",
        "--icon=resources/josm_tagger.ico",
        "--add-data",
        pyinstaller_add_data("resources", "resources"),
        "--add-data",
        pyinstaller_add_data("codes.json", "."),
        "--add-data",
        pyinstaller_add_data("config.json", "."),
        "--add-data",
        pyinstaller_add_data("app_metadata.py", "."), # Aggiunto per includere app_metadata.py
        "--hidden-import", "gi._gi_cairo", # Aggiunto per risolvere il warning
        "--hidden-import", "gi._option", # Aggiunto per risolvere il warning
        "--hidden-import", "pynput.keyboard._xorg", # Forzare l'inclusione del backend Xorg di pynput
        "--hidden-import", "pynput.keyboard._wayland", # Forzare l'inclusione del backend Wayland di pynput
        "main.py",
    ]

    if python_lib_path:
        # Aggiungi la libreria Python condivisa come binary
        cmd.extend(["--add-binary", f"{python_lib_path}:."])

    run(cmd)


def write_file(path, content, mode=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if mode is not None:
        path.chmod(mode)


def copy_file(source, target, mode=None):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    if mode is not None:
        target.chmod(mode)


def normalize_package_permissions(package_root):
    package_root.chmod(0o755)
    for path in package_root.rglob("*"):
        if path.is_dir():
            path.chmod(0o755)


def package_deb(version, arch):
    require_tool("dpkg-deb")

    package_root = BUILD_ROOT / f"{PACKAGE_NAME}_{version}_{arch}"
    debian_dir = package_root / "DEBIAN"
    app_dir = package_root / "usr" / "lib" / PACKAGE_NAME
    share_dir = package_root / "usr" / "share" / PACKAGE_NAME
    bin_dir = package_root / "usr" / "bin"
    desktop_dir = package_root / "usr" / "share" / "applications"
    icon_dir = package_root / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps"
    doc_dir = package_root / "usr" / "share" / "doc" / PACKAGE_NAME

    executable = PROJECT_ROOT / "dist" / EXECUTABLE_NAME
    if not executable.exists():
        raise RuntimeError(f"PyInstaller output not found: {executable}")

    copy_file(executable, app_dir / f"{EXECUTABLE_NAME}.bin", 0o755)
    copy_file(PROJECT_ROOT / "codes.json", share_dir / "codes.json", 0o644)
    copy_file(PROJECT_ROOT / "config.json", share_dir / "config.json", 0o644)
    copy_file(PROJECT_ROOT / "resources" / "josm_tagger.png", icon_dir / "josm-tagger.png", 0o644)

    write_file(
        bin_dir / BIN_NAME,
        f"""#!/bin/sh
set -eu

APP_CONFIG_DIR="${{XDG_CONFIG_HOME:-$HOME/.config}}/{PACKAGE_NAME}"
mkdir -p "$APP_CONFIG_DIR"

if [ ! -f "$APP_CONFIG_DIR/codes.json" ]; then
    cp "/usr/share/{PACKAGE_NAME}/codes.json" "$APP_CONFIG_DIR/codes.json"
fi

if [ ! -f "$APP_CONFIG_DIR/config.json" ]; then
    cp "/usr/share/{PACKAGE_NAME}/config.json" "$APP_CONFIG_DIR/config.json"
fi

cd "$APP_CONFIG_DIR"
exec "/usr/lib/{PACKAGE_NAME}/{EXECUTABLE_NAME}.bin" "$@"
""",
        0o755,
    )

    write_file(
        desktop_dir / f"{PACKAGE_NAME}.desktop",
        f"""[Desktop Entry]
Type=Application
Name={APP_NAME}
Comment=Speed up JOSM tagging
Exec={BIN_NAME}
Icon=josm-tagger
Terminal=false
Categories=Utility;Geography;
StartupNotify=true
""",
        0o644,
    )

    # AGGIORNAMENTO: Aggiunta di dipendenze di sistema comuni senza versione specifica
    control = f"""Package: {PACKAGE_NAME}
Version: {version}
Section: utils
Priority: optional
Architecture: {arch}
Depends: wmctrl, xdotool, xclip, kbd, libayatana-appindicator3-1 | libappindicator3-1, python3-xlib, python3-gi, python3-tk
Recommends: josm
Maintainer: Max1234-Ita <max1234ita@gmail.com>
Description: Fast tagging helper for JOSM
 JOSM Tagger is a productivity tool for OpenStreetMap contributors.
 It applies preset tags to the current JOSM selection.
"""
    write_file(debian_dir / "control", control, 0o644)

    write_file(
        doc_dir / "copyright",
        """Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Source: https://github.com/Max1234-Ita/Josm_Tagger
License: GPL-3.0-only
""",
        0o644,
    )

    normalize_package_permissions(package_root)

    deb_path = DIST_ROOT / f"{PACKAGE_NAME}_{version}_{arch}.deb"
    run(["dpkg-deb", "--build", "--root-owner-group", str(package_root), str(deb_path)])
    print(f"Linux package created: {deb_path}")


def main():
    parser = argparse.ArgumentParser(description="Build Linux PyInstaller binary and Debian package.")
    parser.add_argument("--skip-pyinstaller", action="store_true", help="Only rebuild the .deb from an existing dist/JOSM_Tagger binary.")
    parser.add_argument("--version", default=read_version(), help="Package version. Defaults to appversion in main.py.")
    parser.add_argument("--arch", default=detect_arch(), help="Debian architecture. Defaults to the current machine.")
    args = parser.parse_args()

    if os.name != "posix":
        raise SystemExit("This script must be run on Linux.")

    clean()
    if not args.skip_pyinstaller:
        build_pyinstaller()
    package_deb(args.version, args.arch)


if __name__ == "__main__":
    main()