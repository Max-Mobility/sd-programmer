# SD Programmer

This repository contains the code for uploading bootloader and
firmware to a MX2+ system.

Since the programmer is written in python, which requires many
dependencies to be installed and is not easily packaged for other
people (and other platforms) to use, it must be converted into an
executable for whatever platforms are required. To perform this
conversion into an executable, the user needs to install the
`PyInstaller` library, which turns a python script into an executable
and set of libraries that can be packed into an installer or as a
simiple zip/archive that can be unpacked onto the target devices. The
steps for this creations are:

```bash
pip install pyInstaller
pyinstaller ./program.py
```

This will install the `pyInstaller` library and then create a
`./programmer.exe`. The `./programmer.exe` can be redistributed
as a standalone executable with its required libraries.
