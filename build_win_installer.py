import ast
import os
import subprocess
import sys
import shutil
import re
from pathlib import Path

try:
    import winreg
except ImportError:  # pragma: no cover - non-Windows platforms
    winreg = None


def read_app_version(metadata_path: Path) -> str:
    tree = ast.parse(metadata_path.read_text(encoding="utf-8"), filename=str(metadata_path))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "APP_VERSION":
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        return node.value.value
                    raise ValueError("APP_VERSION must be a string literal")
    raise ValueError("APP_VERSION not found in app_metadata.py")


def resolve_iscc() -> str | None:
    env_override = os.environ.get("INNO_SETUP_ISCC")
    if env_override:
        return env_override

    registry_path = resolve_iscc_from_registry()
    if registry_path:
        return registry_path

    for candidate in ("ISCC.exe", "ISCC"):
        found = shutil.which(candidate)
        if found:
            return found

    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    candidates = [
        Path(program_files) / "Inno Setup 6" / "ISCC.exe",
        Path(program_files_x86) / "Inno Setup 6" / "ISCC.exe",
        Path(program_files) / "Inno Setup 5" / "ISCC.exe",
        Path(program_files_x86) / "Inno Setup 5" / "ISCC.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return None


def resolve_iscc_from_registry() -> str | None:
    if winreg is None:
        return None

    uninstall_roots = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
    ]
    views = [0]
    if hasattr(winreg, "KEY_WOW64_64KEY"):
        views.extend([winreg.KEY_WOW64_64KEY, getattr(winreg, "KEY_WOW64_32KEY", 0)])

    for root_path in uninstall_roots:
        for view in views:
            try:
                root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, root_path, 0, winreg.KEY_READ | view)
            except OSError:
                continue

            with root:
                index = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(root, index)
                    except OSError:
                        break
                    index += 1

                    try:
                        with winreg.OpenKey(root, subkey_name) as subkey:
                            display_name = _reg_value(subkey, "DisplayName")
                            if not display_name or "inno setup" not in display_name.lower():
                                continue

                            install_location = _reg_value(subkey, "InstallLocation")
                            if install_location:
                                candidate = Path(install_location) / "ISCC.exe"
                                if candidate.exists():
                                    return str(candidate)

                            uninstall_string = _reg_value(subkey, "UninstallString")
                            if uninstall_string:
                                candidate = _extract_iscc_from_uninstall_string(uninstall_string)
                                if candidate:
                                    return candidate
                    except OSError:
                        continue

    return None


def _reg_value(key, name: str) -> str | None:
    try:
        value, _ = winreg.QueryValueEx(key, name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    except OSError:
        return None
    return None


def _extract_iscc_from_uninstall_string(uninstall_string: str) -> str | None:
    candidate = uninstall_string.strip().strip('"')
    if candidate.lower().endswith("unins000.exe"):
        candidate = str(Path(candidate).with_name("ISCC.exe"))
        if Path(candidate).exists():
            return candidate

    match = re.search(r'"([^"]*ISCC\.exe)"', uninstall_string, re.IGNORECASE)
    if match:
        candidate = match.group(1)
        if Path(candidate).exists():
            return candidate

    return None


def build_installer():
    root = Path(__file__).parent
    metadata_path = root / "app_metadata.py"
    iss_path = root / "make_setup.iss"

    if not metadata_path.exists():
        print(f"Error: {metadata_path} not found.")
        return 1
    if not iss_path.exists():
        print(f"Error: {iss_path} not found.")
        return 1

    version = read_app_version(metadata_path)
    print(f"Using AppVersion={version}")

    iscc = resolve_iscc()
    if not iscc:
        print(
            "ISCC not found. Download and install Inno Setup from "
            "https://jrsoftware.org/isdl.php/Inno-Setup-Downloads, then install it "
            "on this computer. You can also set INNO_SETUP_ISCC to the full path of "
            "ISCC.exe."
        )
        return 1

    cmd = [
        iscc,
        f"/DAppVersion={version}",
        str(iss_path),
    ]

    try:
        subprocess.run(cmd, check=True)
        return 0
    except FileNotFoundError:
        print(
            "ISCC not found. Download and install Inno Setup from "
            "https://jrsoftware.org/isdl.php/Inno-Setup-Downloads, then install it "
            "on this system. You can also set INNO_SETUP_ISCC to the full path of "
            "ISCC.exe."
        )
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"Installer build failed: {exc}")
        return exc.returncode or 1


if __name__ == "__main__":
    sys.exit(build_installer())
