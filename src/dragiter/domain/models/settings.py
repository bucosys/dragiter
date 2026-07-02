from dataclasses import dataclass, field
from pathlib import Path
from typing import Generic, Optional, TypeVar

T = TypeVar('T')


# the base class

@dataclass
class ValueSetting(Generic[T]):
    # We store the actual value in a private field
    _key: str = field(default=None, init=True, repr=False)
    _value: T = field(default=None, init=False, repr=False)
    is_set: bool = field(default=False, init=False)

    @property
    def key(self) -> T:
        return self._key

    @property
    def value(self) -> T:
        return self._value

    @value.setter
    def value(self, new_value: T):
        if self.is_set:
            raise AttributeError("Value has already been set and cannot be changed!")

        self._value = new_value
        self.is_set = True

    # def __copy__(self):
    #     """Prevents copying value."""
    #     return self
    #
    # def __deepcopy__(self, memo: dict):
    #     """Prevents deep copying value."""
    #     return self


# typed inheritance

@dataclass
class StringSetting(ValueSetting[str]): ...


@dataclass
class BoolSetting(ValueSetting[bool]): ...


#    def __bool__(self) -> bool:
#        return self.is_set and bool(self._value)

# @dataclass
# class PathSetting(ValueSetting[Path]): ...


@dataclass
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
    _original_path: Optional[Path] = field(default=None, init=False, repr=False)
    # Current base directory used for resolving relative paths
    _base_dir: Path = field(default_factory=Path.cwd, init=False, repr=False)

    @property
    def value(self) -> Path:
        """Always returns an absolute path (as stored in _value)."""
        if not self.is_set:
            return None  # raise AttributeError("Value has not been set yet")
        return self._value

    @value.setter
    def value(self, new_value: str | Path) -> None:
        """Set the path. First assignment only (immutable after that)."""
        if self.is_set:
            raise AttributeError("Value has already been set and cannot be changed!")

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

        self.is_set = True

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
    def original_value(self) -> Optional[Path]:
        """Returns the originally set path (relative or absolute). Useful for debugging."""
        return self._original_path

    def __repr__(self) -> str:
        if self.is_set:
            return (
                f"PathSetting(key={self.key!r}, "
                f"value={self.value}, "
                f"original={self._original_path}, "
                f"base={self._base_dir})"
            )
        return f"PathSetting(key={self.key!r}, <not set>)"


@dataclass
class FloatSetting(ValueSetting[float]): ...


@dataclass
class IntegerSetting(ValueSetting[int]): ...


# bool first ####
@dataclass
class DebugBoolSetting(BoolSetting): ...


@dataclass
class SimulateBoolSetting(BoolSetting): ...


@dataclass
class VerboseBoolSetting(BoolSetting): ...


@dataclass
class SequentialProcessingBoolSetting(BoolSetting): ...


# then str #####
@dataclass
class ApiKeyStringSetting(StringSetting): ...


@dataclass
class BaseURLStringSetting(StringSetting): ...


@dataclass
class ModelNameStringSetting(StringSetting): ...


@dataclass
class OutputDelimiterStringSetting(StringSetting): ...


@dataclass
class OutputFilenameSchemaStringSetting(StringSetting): ...


@dataclass
class OutputModeStringSetting(StringSetting): ...


@dataclass
class TaskStringSetting(StringSetting): ...


#### at the end numbers ####

@dataclass
class CharsPerTokenFloatSetting(FloatSetting): ...


@dataclass
class MaxContextTokensIntSetting(IntegerSetting): ...


@dataclass
class MaxOutputTokensIntSetting(IntegerSetting): ...


@dataclass
class MaxRetryIntSetting(FloatSetting): ...


@dataclass
class RetryDelayIntSetting(IntegerSetting): ...


@dataclass
class TemperatureFloatSetting(FloatSetting): ...


# last path
@dataclass
class ActivityFilePathSetting(PathSetting): ...


@dataclass
class ConfigFilePathSetting(PathSetting): ...

@dataclass
class LogFilePathSetting(PathSetting): ...

@dataclass
class PromptFilePathSetting(PathSetting): ...


@dataclass
class LoopFilePathSetting(PathSetting): ...


@dataclass
class ResourceFilePathSetting(PathSetting): ...


@dataclass
class OutputFilePathSetting(PathSetting): ...


@dataclass
class OutputDirectoryPathSetting(PathSetting): ...


@dataclass
class BaseDirectoryPathSetting(PathSetting): ...


class ConfigurationSettingsError(Exception):
    pass
