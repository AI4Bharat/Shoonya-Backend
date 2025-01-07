"""
``openfile`` is a trivial Python module that implements a single convenience
function ``openfile(filename, mode="rt", **kwargs)`` wich delegates the real
work to ``gzip.open()``, ``bz2.open()``, ``lzma.open()`` or ``open()``,
depending on the filename suffix.
"""

try:
    import bz2
except ImportError:
    bz2 = None

try:
    import gzip
except ImportError:
    gzip = None

try:
    import lzma
except ImportError:
    lzma = None

import os.path
import sys


__version__ = "0.0.7"


def openfile(filename, mode="rt", *args, expanduser=False, expandvars=False,
             makedirs=False, **kwargs):
    """Open filename and return a corresponding file object."""
    if filename in ("-", None):
        return sys.stdin if "r" in mode else sys.stdout
    if expanduser:
        filename = os.path.expanduser(filename)
    if expandvars:
        filename = os.path.expandvars(filename)
    if makedirs and ("a" in mode or "w" in mode):
        parentdir = os.path.dirname(filename)
        if not os.path.isdir(parentdir):
            os.makedirs(parentdir)
    if filename.endswith(".gz"):
        if gzip is None:
            raise NotImplementedError
        _open = gzip.open
    elif filename.endswith(".bz2"):
        if bz2 is None:
            raise NotImplementedError
        _open = bz2.open
    elif filename.endswith(".xz") or filename.endswith(".lzma"):
        if lzma is None:
            raise NotImplementedError
        _open = lzma.open
    else:
        _open = open
    return _open(filename, mode, *args, **kwargs)


__all__ = ["openfile"]
