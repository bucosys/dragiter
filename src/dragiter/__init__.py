# In src/dragiter/__init__.py
from importlib.metadata import version, PackageNotFoundError

__tool_name__ = "dragiter"
try:
    __version__ = version("dragiter")
except PackageNotFoundError:
    __version__ = "2026.8.10"  # fall back version (current)

