"""
SpaceShooter Application Packaging Script
Builds a standalone, zero-dependency Windows desktop application using PyInstaller
and packages it into a distributable zip archive.
"""

import os
import sys
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"
ASSETS_DIR = ROOT_DIR / "assets"
ICON_PATH = ASSETS_DIR / "app_icon.ico"


def build_app(onefile: bool = False):
    print("=" * 60)
    print(" BUILDING SPACESHOOTER APPLICATION")
    print("=" * 60)

    mode_arg = "--onefile" if onefile else "--onedir"
    mode_name = "Single Executable (.exe)" if onefile else "Folder Package (Fast Launch)"
    print(f"Build Mode: {mode_name}")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconsole",
        "--name",
        "SpaceShooter",
        mode_arg,
        "--clean",
        "-y",
        "--add-data",
        f"{ASSETS_DIR};assets",
    ]

    if ICON_PATH.exists():
        cmd.extend(["--icon", str(ICON_PATH)])

    cmd.append(str(ROOT_DIR / "src" / "main.py"))

    print("\nExecuting PyInstaller command:")
    print(" ".join(cmd))
    print("-" * 60)

    result = subprocess.run(cmd, cwd=str(ROOT_DIR))
    if result.returncode != 0:
        print(f"\n[ERROR] Build failed with return code {result.returncode}")
        return False

    print("\n[SUCCESS] PyInstaller build completed successfully!")

    # Package as zip for distribution
    if not onefile:
        app_folder = DIST_DIR / "SpaceShooter"
        zip_path = DIST_DIR / "SpaceShooter-v1.0.0-Windows.zip"
        print(f"\nPackaging distributable zip: {zip_path.name}...")

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(app_folder):
                for f in files:
                    file_path = Path(root) / f
                    arcname = file_path.relative_to(DIST_DIR)
                    zf.write(file_path, arcname)

        print(f"[PACKAGE CREATED] {zip_path}")
        size_mb = zip_path.stat().st_size / (1024 * 1024)
        print(f"Archive Size: {size_mb:.2f} MB")
        print("\nReady to distribute: extract the ZIP, open the SpaceShooter folder, and run SpaceShooter.exe!")

    return True


if __name__ == "__main__":
    is_onefile = "--onefile" in sys.argv
    success = build_app(onefile=is_onefile)
    sys.exit(0 if success else 1)

