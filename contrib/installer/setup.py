#!/usr/bin/env python3
#
# Copyright (C) 2007-2017 by frePPLe bv
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero
# General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import cx_Freeze
import os.path
import sys

from distutils.command.install import INSTALL_SCHEMES

for scheme in INSTALL_SCHEMES.values():
    scheme["data"] = scheme["purelib"]

sys.path.append(os.path.join(os.path.split(__file__)[0], "..", ".."))

# Define what is to be included and excluded
packages = [
    # Required for django standalone deployment
    "logging",
    "email",
    "cheroot",
    "portend",
    "sqlparse",
    "pathlib",
    "psutil",
    "PIL",
    "appdirs",
    "packaging",
    "pkg_resources",
    "wsgiref",
    "html5lib",
    # Added for PostgreSQL
    "psycopg2",
    # Dependencies for openpyxl
    "jdcal",
    "et_xmlfile",
    # Added to be able to connect to SQL Server
    "adodbapi",
    # Required for REST API
    "rest_framework_bulk",
    "rest_framework_filters",
    "markdown",
    # Added to package a more complete python library with frePPLe
    "urllib",
    "multiprocessing",
    "asyncio",
    "pip",
    "html.parser",
    "csv",
    "poplib",
    "imaplib",
    "telnetlib",
    "colorsys",
    # Added for unicode and internationalization
    "encodings",
    # Added for cx_freeze binaries
    "cx_Logging",
    # Request for json web tokents
    "jwt",
    # Required for requests package
    "idna",
    "urllib3",
    "chardet",
    # Required for pysftp
    "pysftp",
    "paramiko",
    "bcrypt",
    "cffi",
    "nacl",
    "pycparser",
    "setuptools_rust",
    "semantic_version",
    "toml",
]
excludes = [
    "django",
    "freppledb",
    "pydoc",
    "cx_Oracle",
    "MySQLdb",
    "rest_framework",
    "tkinter",
    "certifi",
]

# Add all modules that need to be added in uncompiled format
import bootstrap3
import certifi
import dateutil
import django
import django_admin_bootstrapped
import freppledb
import rest_framework
import pytz
import requests
import openpyxl
from distutils.sysconfig import get_python_lib

data_files = [
    ("freppleservice.py", "freppleservice.py"),
    (os.path.join(get_python_lib(), "win32", "lib", "pywintypes.py"), "pywintypes.py"),
    (
        os.path.join(get_python_lib(), "win32", "lib", "win32timezone.py"),
        "win32timezone.py",
    ),
    (
        os.path.join(get_python_lib(), "win32", "lib", "win32serviceutil.py"),
        "win32serviceutil.py",
    ),
    (os.path.join(get_python_lib(), "pythoncom.py"), "pythoncom.py"),
]
for mod in [
    bootstrap3,
    certifi,
    dateutil,
    django,
    django_admin_bootstrapped,
    freppledb,
    rest_framework,
    pytz,
    requests,
    openpyxl,
]:
    srcdir = mod.__path__[0]
    targetdir = os.path.join("custom", mod.__name__)
    root_path_length = len(srcdir) + 1
    for dirpath, dirnames, filenames in os.walk(os.path.join(srcdir)):
        # Ignore dirnames that start with '.'
        for i, dirname in enumerate(dirnames):
            if dirname.startswith(".") or dirname == "__pycache__":
                del dirnames[i]
        # Append data files for this subdirectory
        for f in filenames:
            if not f.endswith(".pyc") and not f.endswith(".pyo"):
                data_files.append(
                    (
                        os.path.join(dirpath, f),
                        os.path.join(targetdir, dirpath[root_path_length:], f),
                    )
                )

# Find version number
version = freppledb.__version__
for v in sys.argv:
    if v.startswith("--version="):
        version = v.split("=")[1]
        sys.argv.remove(v)
        break

# Run the cx_Freeze program
cx_Freeze.setup(
    version=version,
    description="frePPLe web application",
    name="frePPLe",
    author="frepple.com",
    url="https://frepple.com",
    options={
        "install_exe": {"install_dir": "dist"},
        "build_exe": {
            "silent": True,
            "optimize": 2,
            "packages": packages,
            "excludes": excludes,
            "include_files": data_files,
            "include_msvcr": True,
        },
    },
    executables=[
        # A console application
        cx_Freeze.Executable(
            "frepplectl.py",
            base="Console",
            icon=os.path.join("..", "..", "src", "frepple.ico"),
        ),
        # A Windows service
        cx_Freeze.Executable(
            "freppleservice.py",
            base="Win32Service",
            icon=os.path.join("..", "..", "src", "frepple.ico"),
        ),
        # A system tray application
        cx_Freeze.Executable(
            "freppleserver.py",
            base="Win32GUI",
            icon=os.path.join("..", "..", "src", "frepple.ico"),
        ),
    ],
)
