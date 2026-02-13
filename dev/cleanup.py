#!/usr/bin/env python
# cleanup.py
"""
Cleanup script to remove build artifacts and cache files.
This script removes:
- build/
- dist/
- *.egg-info folders
- __pycache__ folders
"""
import glob
import os
import shutil
import stat


def remove_readonly(func, path, _):
    """Clear the readonly bit and reattempt removal."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def safe_rmtree(folder: str):
    """Safely remove a directory tree, handling permission issues."""
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
    """Remove all build artifacts and cache files."""
    print("\nCleaning build artifacts and cache files:")

    # Remove standard build folders
    for folder in ["build", "dist"]:
        safe_rmtree(folder)

    # Remove all .egg-info folders anywhere
    safe_rmtree_pattern("**/*.egg-info")

    # Remove all __pycache__ folders anywhere
    safe_rmtree_pattern("**/__pycache__")

    print("\nCleanup complete.")


if __name__ == "__main__":
    clean()
