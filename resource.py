import os
import sys

try:
    base_path = sys._MEIPASS
    print("[RESOURCE] Running as a package")
except Exception:
    print("[RESOURCE] Running from source")

def path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath("./")

    print("[RESOURCE]", relative_path)
    rPath = os.path.join(base_path, relative_path)
    return rPath
