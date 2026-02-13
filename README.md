# Oregon Processing Project

A Python package for communicating with Oregon RFID devices over a serial connection. It provides a high-level interface for connecting to the reader, sending commands, inspecting device status, and running an interactive terminal.

- Package name: `oregon-processing` (import as `oregon_processing`)
- Minimum Python: 3.8+


## Install

Requirements: Windows + Anaconda/Miniconda.

### 1) Install Anaconda
You can use either the full Anaconda distribution or the lighter Miniconda. Choose the method for your operating system.

- Windows
  1. Download the latest “Anaconda” (or “Miniconda”) installer from your company software center or from the official site: https://www.anaconda.com/download.
  2. Run the installer and follow the defaults.
  3. Open an “Anaconda Prompt” terminal.

If the Software Center option isn’t available, download Anaconda/Miniconda from the official site and follow their Linux install instructions.


### 2) Set up Oregon-Processing

Once you have Anaconda/Miniconda installed, you can set up the actual package in a proper Conda environment.

### Option A: Use the installer batch files (recommended)

1. Double-click `scripts\install.bat` (recommended for end users)
  - This creates/updates the conda environment and installs the package.
2. (Optional) For development, use `scripts\install_dev.bat` instead
  - This installs the package in editable mode.

Cleanup (Optional): Cleanup the folders afterwards by double-clicking `scripts\cleanup.bat`.

### Option B: Manual install (advanced)

In Anaconda Prompt, navigate to the main project directory and run the following commands:
```Anaconda prompt
conda create -n oregon_env python=3.11 -y
conda activate oregon_env
python -m pip install --upgrade pip
python -m pip install .
```

### Editable vs Direct Install
- Editable install (`scripts\install_dev.bat`):
  - Uses `pip install -e .`
  - Your environment points to the local source in `src/`.
  - Any code changes you make are immediately reflected when you `import oregon_processing` without reinstalling.
  - Ideal for development and contributing.

- Direct install (`scripts\install.bat`):
  - Uses `pip install .`
  - Builds and installs a copy of the package into site-packages.
  - Changes to the local source do not affect the installed package until you reinstall.
  - Ideal for regular users who just want to use the package.


### 3) Use the tools

Once the package is installed properly, the following tools can be used:

- `scripts\open_terminal.bat` (interactive terminal)
- `scripts\start_export.bat` (export data)

These two .bat files can be run from any directory, as long as the package is installed in the conda environment. You can copy them to your Desktop or create shortcuts and run them from there.

---




## Project Layout
- `src/oregon_processing/` – package source (import as `oregon_processing`)
- `scripts/` – user-facing batch files (install, terminal, export)
- `dev/` – developer utilities (cleanup, legacy install)


## Troubleshooting
- Conda not found:
  - Ensure Anaconda/Miniconda is installed and you’re in an “Anaconda Prompt” (Windows) or a terminal with Conda initialized.


## License
MIT
