#!/usr/bin/env python
# install.py
import subprocess
import sys
import argparse
import glob
import os
import shutil
import stat

PROJECT_NAME = 'oregon_processing'

def remove_readonly(func, path, _):
    """Clear the readonly bit and reattempt removal."""
    os.chmod(path, stat.S_IWRITE)
    func(path)

def safe_rmtree(folder: str):
    if os.path.exists(folder):
        for root, dirs, files in os.walk(folder, topdown=False):
            for name in files:
                file_path = os.path.join(root, name)
                try:
                    os.remove(file_path)
                except PermissionError:
                    # Try to remove readonly and delete again
                    os.chmod(file_path, stat.S_IWRITE)
                    os.remove(file_path)
            for name in dirs:
                dir_path = os.path.join(root, name)
                try:
                    os.rmdir(dir_path)
                except OSError:
                    pass  # may not be empty yet
        try:
            shutil.rmtree(folder, onerror=remove_readonly)
        except Exception as e:
            print(f"\t- Could not remove {folder}: {e}")
        else:
            print(f"\t- Removed {folder}")

def safe_rmtree_pattern(pattern: str):
    """Remove all folders matching a glob pattern."""
    for folder in glob.glob(pattern, recursive=True):
        if os.path.isdir(folder):
            safe_rmtree(folder)

def clean():
    print("\n\nCleaning build:")
    # Remove standard folders
    for folder in ["build", "dist"]:
        safe_rmtree(folder)

    # Remove all .egg-info folders anywhere
    safe_rmtree_pattern("**/*.egg-info")


def run_command(cmd):
    """Run a shell command and exit if it fails."""
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"Command failed: {' '.join(cmd)}")
        sys.exit(result.returncode)

def main(editable: bool):
    """Install the package and clean build artifacts."""
    install_cmd = ["pip", "install", "-e", "."] if editable else ["pip", "install", "."]

    if editable:
        print(f"\n{PROJECT_NAME}: Editable install running.\n\n")
    else:
        print(f"\n{PROJECT_NAME}: Normal install running.\n\n")

    run_command(install_cmd)


    clean()

    print("\nInstall complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Install the package and clean build artifacts."
    )
    parser.add_argument(
        "-e", "--editable", action="store_true",
        help="Do an editable install (pip install -e .)"
    )
    args = parser.parse_args()
    main(args.editable)