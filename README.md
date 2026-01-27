# Oregon Processing Project

A Python package for communicating with Oregon RFID devices over a serial connection. It provides a high-level interface for connecting to the reader, sending commands, inspecting device status, and running an interactive terminal.

- Package name: `oregon-processing` (import as `oregon_processing`)
- Minimum Python: 3.8+
- Key modules: `OregonCommunicator`, `OregonConnector`

## What’s Included
- Connect to an Oregon RFID reader via serial port
- Send commands and parse responses
- Inspect/verify system status and health
- Export logs and status information
- Interactive terminal for manual exploration


## Quick Start
If you already have Anaconda/Miniconda installed:

```Anaconda prompt
# Create and activate the environment
conda create -n oregon_env python=3.11 -y
conda activate oregon_env

# (Optional) Upgrade pip
python -m pip install --upgrade pip

# Install this package (choose one of the two options below)
# 1) Editable install (recommended for development)
python install.py -e
# 2) Direct install (recommended for users)
python install.py
```

Then try the interactive terminal example:

```Anaconda prompt
python test/terminal.py
```

> Note: The test scripts add the `src/` folder to `sys.path` for convenience. If you installed the package, you can also import `oregon_processing` from anywhere in the environment.

---

## Beginner-Friendly Setup (Step by Step)

### 1) Install Anaconda
You can use either the full Anaconda distribution or the lighter Miniconda. Choose the method for your operating system.

- Windows
  1. Download the latest “Anaconda” (or “Miniconda”) installer from  your company software center or from the official site: https://www.anaconda.com/download.
  2. Run the installer and follow the defaults.
  3. Open an “Anaconda Prompt” terminal.


If the Software Center option isn’t available, download Anaconda/Miniconda from the official site and follow their Linux install instructions.


### 2) Create a Conda Environment
Create a fresh environment named `orgegon_env`. You can use a different name if you prefer.

```Anaconda prompt
conda create -n oregon_env python=3.11 -y
```

Activate it:

```Anaconda prompt
conda activate oregon_env
```

(Optional) Upgrade pip inside the environment:

```Anaconda prompt
python -m pip install --upgrade pip
```


### 3) Install the Project
From the repository root (where `install.py` and `pyproject.toml` live), run one of the following:

- Editable install (for development):

  ```Anaconda prompt
  conda activate oregon_env

  cd path/to/oregon-processing-project

  python install.py -e
  ```

- Direct install (for end users):

  ```Anaconda prompt
  conda activate oregon_env

  cd path/to/oregon-processing-project

  python install.py
  ```

Both options call `pip` under the hood, then clean build artifacts. The environment must be active so that installation lands in the correct place.


### Editable vs Direct Install
- Editable install (`python install.py -e`):
  - Uses `pip install -e .`
  - Your environment points to the local source in `src/`.
  - Any code changes you make are immediately reflected when you `import oregon_processing` without reinstalling.
  - Ideal for development and contributing.

- Direct install (`python install.py`):
  - Uses `pip install .`
  - Builds and installs a copy of the package into site-packages.
  - Changes to the local source do not affect the installed package until you reinstall.
  - Ideal for regular users who just want to use the package.


## Verifying the Install
Run a tiny import check from anywhere in the activated environment:

```Anaconda prompt
python -c "import oregon_processing; print('oregon_processing imported OK')"
```



## Project Layout
- `src/oregon_processing/` – package source (import as `oregon_processing`)
- `install.py` – helper installer (editable or direct) + cleanup
- `test/terminal.py` – interactive terminal example
- `test/test.py` – scripted example for status/log export


## Troubleshooting
- Conda not found:
  - Ensure Anaconda/Miniconda is installed and you’re in an “Anaconda Prompt” (Windows) or a terminal with Conda initialized.
- Permission issues on install:
  - Activate your environment before running `python install.py`.
- Windows readline history:
  - The project depends on `pyreadline3` on Windows to provide readline-like behavior.
- Serial access:
  - Ensure the correct serial port is available/accessible; on Linux you may need to add your user to the `dialout` group and re-login.


## License
MIT
