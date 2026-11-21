"""Entry point: `python main.py` during development, and the script PyInstaller packages."""
import sys

from secureapp.ui import run

if __name__ == "__main__":
    sys.exit(run())
