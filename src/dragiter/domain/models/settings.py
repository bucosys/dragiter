# =============================================================================
# dragiter - Deterministic Context Iterator
# Copyright (c) 2026 Michael Buchold <michael.buchold@dragiter.app>
#
# This file is part of dragiter.
#
# dragiter is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# dragiter is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with dragiter. If not, see <https://www.gnu.org/licenses/>.
#
# For commercial licensing (closed-source use, SaaS, etc.), please contact:
# Michael Buchold <michael.buchold@dragiter.app>
# =============================================================================

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Generic, TypeVar

T = TypeVar('T')

class ValueOrigin(str, Enum):
    """Short label for the source of a setting value."""

    CLI = "A"
    CONFIG = "C"
    CONFIG_RESOLVED = "C$"
    ENV = "E"
    ENV_RESOLVED = "E$"
    DEFAULT = "D"

    def __str__(self) -> str:
        return self.value

# the base class

@dataclass
class ValueSetting(Generic[T]):
    # We store the actual value in a private field
    _key: str = field(default=None, init=True, repr=False)
    _value: T = field(default=None, init=False, repr=False)
    _origin: ValueOrigin | None = field(default=None, init=False, repr=False)
    _is_set: bool = field(default=False, init=False, repr=False)


    @property
    def key(self) -> str:
        return self._key

    @property
    def value(self) -> T:
        return self._value

    @property
    def is_set(self) -> bool:
        return self._is_set


    @property
    def origin(self) -> ValueOrigin | None:
        return self._origin

    def set(self, new_value: T, origin: ValueOrigin) -> None:
        if self.is_set:
            raise AttributeError(
                f"Setting '{self.key}' has already been set and cannot be changed!"
            )
        if not isinstance(origin, ValueOrigin):
            raise TypeError(f"origin must be ValueOrigin, got {type(origin).__name__}")

        self._validate(new_value)
        self._value = new_value
        self._origin = origin
        self._is_set = True

    def _validate(self, new_value: Any) -> None:
        """Hook for subclasses to validate the incoming value. Default: no-op."""
        pass

    def from_string(self, raw_value: str, origin: ValueOrigin) -> None:
        """
        Parses a string and assigns it to the setting.
        Must be overridden by all subclasses to ensure strict typing.
        """
        raise NotImplementedError(
            f"The subclass '{self.__class__.__name__}' must implement the 'from_string' method."
        )

    def __repr__(self) -> str:
        name = type(self).__name__
        if self.is_set:
            return (
                f"{name}(key={self.key!r}, "
                f"value={self.value!r}, "
                f"origin={self.origin!r})"
            )
        return f"{name}(key={self.key!r}, <not set>)"



# typed inheritance

class APIStringSetting(ValueSetting[str]):
    def _validate(self, new_value: Any) -> None:
        if not isinstance(new_value, str):
            raise TypeError(
                f"APIStringSetting '{self.key}' expected str, got {type(new_value).__name__}"
            )
    def from_string(self, raw_value: str, origin: ValueOrigin) -> None:
        """Explicitly implements parsing for strings (which is a direct pass-through)."""
        if not isinstance(origin, ValueOrigin):
            raise TypeError(f"origin must be ValueOrigin, got {type(origin).__name__}")

        self.set(raw_value, origin)

    def __repr__(self) -> str:
        name = type(self).__name__
        if self.is_set:
            return (
                f"{name}(key={self.key!r}, "
                f"value=********, "
                f"origin={self.origin!r})"
            )
        return f"{name}(key={self.key!r}, <not set>)"


class StringSetting(ValueSetting[str]):
    def _validate(self, new_value: Any) -> None:
        if not isinstance(new_value, str):
            raise TypeError(
                f"StringSetting '{self.key}' expected str, got {type(new_value).__name__}"
            )
    def from_string(self, raw_value: str, origin: ValueOrigin) -> None:
        """Explicitly implements parsing for strings (which is a direct pass-through)."""
        self.set(raw_value, origin)



class BoolSetting(ValueSetting[bool]):
    def _validate(self, new_value: Any) -> None:
        if not isinstance(new_value, bool):
            raise TypeError(
                f"BoolSetting '{self.key}' expected bool, got {type(new_value).__name__}"
            )

    def from_string(self, raw_value: str, origin: ValueOrigin) -> None:
        if not isinstance(origin, ValueOrigin):
            raise TypeError(f"origin must be ValueOrigin, got {type(origin).__name__}")
        
        val = str(raw_value).strip().lower()
        if val in ("true", "1", "yes", "on", "y"):
            self.set(True, origin)
        elif val in ("false", "0", "no", "off", "n"):
            self.set(False, origin)
        else:
            raise ValueError(f"Cannot interpret '{raw_value}' as bool for '{self.key}'.")

class PathSetting(ValueSetting[Path]):
    """
    Specialized setting for file system paths.

    Features:
      - Accepts both relative and absolute paths on first set
      - .value always returns an absolute Path
      - Supports rebasing: changing the base directory for relative paths
      - Stores the absolute resolved path internally (_value)
    """

    # Private storage for the originally provided path (to enable rebasing)
    _original_path: Path | None = field(default=None, init=False, repr=False)
    # Current base directory used for resolving relative paths
    _base_dir: Path = field(default_factory=Path.cwd, init=False, repr=False)

    @property
    def value(self) -> Path:
        """Always returns an absolute path (as stored in _value)."""
        if not self.is_set:
            return None  # raise AttributeError("Value has not been set yet")
        return self._value

    def set(self, new_value: str | Path, origin: ValueOrigin) -> None:
        """Set the path. First assignment only (immutable after that)."""
        
        if self.is_set:
            raise AttributeError(
                f"PathSetting '{self.key}' has already been set and cannot be changed!"
            )
        if not isinstance(origin, ValueOrigin):
            raise TypeError(f"origin must be ValueOrigin, got {type(origin).__name__}")

        if isinstance(new_value, str):
            new_value = Path(new_value)

        self._original_path = new_value

        # Resolve to absolute path immediately using current CWD
        if new_value.is_absolute():
            self._value = new_value.resolve()
            self._base_dir = new_value.parent  # optional: use parent as base
        else:
            self._base_dir = Path.cwd()
            self._value = (self._base_dir / new_value).resolve()

        self._is_set = True
        self._origin = origin

    def rebase(self, new_base: str | Path) -> None:
        """
        Change the base directory and update the stored absolute path.
        Only affects paths that were originally relative.
        """
        if not self.is_set or self._original_path is None:
            raise RuntimeError("Cannot rebase: no value has been set yet.")

        if isinstance(new_base, str):
            new_base = Path(new_base)

        self._base_dir = new_base.resolve()

        # Recompute _value if the original path was relative
        if not self._original_path.is_absolute():
            self._value = (self._base_dir / self._original_path).resolve()

    @property
    def original_value(self) -> Path | None:
        """Returns the originally set path (relative or absolute). Useful for debugging."""
        return self._original_path


    def from_string(self, raw_value: str, origin: ValueOrigin) -> None:
        """Explicitly implements parsing for strings (which is a direct pass-through)."""
        self.set(Path(str(raw_value).strip()), origin)


    def __repr__(self) -> str:
        if self.is_set:
            return (
                f"PathSetting(key={self.key!r}, "
                f"value={self.value}, "
                f"original={self._original_path}, "
                f"base={self._base_dir})"
            )
        return f"PathSetting(key={self.key!r}, <not set>)"


class FloatSetting(ValueSetting[float]):
    def _validate(self, new_value: Any) -> None:
        if not isinstance(new_value, float):
            raise TypeError(
                f"FloatSetting '{self.key}' expected float, got {type(new_value).__name__}"
            )

    def from_string(self, raw_value: str, origin: ValueOrigin) -> None:
        self.set(float(raw_value), origin)


class IntegerSetting(ValueSetting[int]):
    def _validate(self, new_value: Any) -> None:
        # bool is a subclass of int in Python - reject it explicitly
        if type(new_value) is not int:
            raise TypeError(
                f"IntegerSetting '{self.key}' expected int, got {type(new_value).__name__}"
            )

    def from_string(self, raw_value: str, origin: ValueOrigin) -> None:
        self.set(int(raw_value), origin)
        

# bool first ####
class DebugBoolSetting(BoolSetting): ...
class TCPKeepAliveBoolSetting(BoolSetting): ...
class SimulateBoolSetting(BoolSetting): ...
class VerboseBoolSetting(BoolSetting): ...
class SequentialProcessingBoolSetting(BoolSetting): ...


# then str #####
class APIKeyStringSetting(APIStringSetting): ...
# Historical alias kept so older tests and call sites keep importing cleanly.
ApiKeyStringSetting = APIKeyStringSetting
class BaseURLStringSetting(StringSetting): ...
class ModelNameStringSetting(StringSetting): ...
class OutputDelimiterStringSetting(StringSetting): ...
class OutputFilenameSchemaStringSetting(StringSetting): ...


class OutputModeStringSetting(StringSetting): ...
class TaskStringSetting(StringSetting): ...

#### at the end numbers ####
class CharsPerTokenFloatSetting(FloatSetting): ...
class MaxContextTokensIntSetting(IntegerSetting): ...
class MaxOutputTokensIntSetting(IntegerSetting): ...
class MaxRetryIntSetting(IntegerSetting): ...

class RetryDelayIntSetting(IntegerSetting): ...
class TemperatureFloatSetting(FloatSetting): ...


# last path
class ActivityFilePathSetting(PathSetting): ...
class CaBundleFilePathSetting(PathSetting): ...
class ClientCertFilePathSetting(PathSetting): ...
class ClientKeyFilePathSetting(PathSetting): ...
class ConfigFilePathSetting(PathSetting): ...
class LogFilePathSetting(PathSetting): ...
class PromptFilePathSetting(PathSetting): ...
class LoopFilePathSetting(PathSetting): ...
class ResourceFilePathSetting(PathSetting): ...
class OutputFilePathSetting(PathSetting): ...
class OutputDirectoryPathSetting(PathSetting): ...
class BaseDirectoryPathSetting(PathSetting): ...


class ConfigurationSettingsError(Exception):
    pass
