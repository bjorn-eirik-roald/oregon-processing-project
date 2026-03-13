Quick Setup (Recommended for End Users)
---------------------------------------



### 1) Download the Project

* Download the ZIP release from GitHub (or optionally clone the repository).

* **Place the folder in a logical location**, e.g., `C:\Users\<YourUser>\Documents\oregon-processing-project`.

  > The location will be used for the virtual environment and scripts, so choose a place that you can keep permanently.


### 2) Install Python Install Manager (Recommended)

* Install **Python Install Manager** from the Windows Store. This does not require admin rights and is the preferred method.

* No manual installation or separate download of Python is required. The setup script will handle Python 3.13 installation if needed.

### 3) Run the Setup Script

Navigate to the project folder using File Explorer and double-click on `setup.bat` to run it.

The setup script will:
  1. Detect if Python 3.13 is installed via the Python launcher (`py.exe`). If not present, it will install Python 3.13 automatically.
  2. Create a virtual environment in the project folder (`.venv`).
  3. Install the BJØRN package and dependencies into the virtual environment.


### 4) Verify the Setup


Try running any of the batch files in `bin/`. The application should start (even if it does not run to completion, it should launch), indicating setup was successful.

* (Optional) To verify Python is installed, open a Command Prompt and run:

  `py --version`

  You should see `Python 3.13.x` displayed.

* If you encounter issues, see Troubleshooting below.

* * *

Project Layout
--------------


* `bin/` – user-facing shortcuts (double-click to run)

* `.venv/` – virtual environment (created by `setup.bat`)

* `src/` – source-code

* * *


Troubleshooting
---------------


* **Python launcher not found**: Ensure you have installed Python Install Manager from the Windows Store. The setup script will handle Python installation automatically.

* **Python 3.13 not found or not launching**: If you see an error indicating that Python 3.13 is not installed, or the setup script fails to find the correct version, open a Command Prompt and run:

  `py --version`

  If the output does not show `Python 3.13.x`, the setup script should install it automatically. If it does not, ensure Python Install Manager is installed and try running the setup script again.

* **WARNING: The 'install' command is unavailable because this is the legacy py.exe command.** Inspect your Installed Apps in Windows Settings and uninstall any older Python Launchers. Only the most recent one, installed from Python Install Manager, should remain.


* * *

License
-------

MIT