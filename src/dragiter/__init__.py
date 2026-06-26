# In src/dragiter/__init__.py
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("dragiter")
except PackageNotFoundError:
    __version__ = "0000.00.00a0"  # fall back version not valid
