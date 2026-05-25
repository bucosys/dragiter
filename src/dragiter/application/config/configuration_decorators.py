from typing import Generic, TypeVar
from dataclasses import dataclass
from dragiter.domain.models.settings import BoolSetting, IntegerSetting, StringSetting, FloatSetting, PathSetting

T = TypeVar('T')


@dataclass
class ArgumentDecorator(Generic[T]):
    value_setting_object: T
    short_key: str = "-"
    help: str = "Unknown basic setting"
    required: bool = False

    # for now value setting object ist responsible to define long key
    def __post_init__(self):
        if self.value_setting_object is not None:
            self.long_key = self.value_setting_object.key
        else:
            raise AttributeError("Key of ConfigValue object has not been set and cannot be changed!")


@dataclass
class StringSettingArgumentDecorator(ArgumentDecorator[StringSetting]): ...

@dataclass
class BoolSettingArgumentDecorator(ArgumentDecorator[BoolSetting]): ...

@dataclass
class PathSettingArgumentDecorator(ArgumentDecorator[PathSetting]): ...

@dataclass
class FloatSettingArgumentDecorator(ArgumentDecorator[FloatSetting]): ...

@dataclass
class IntegerSettingArgumentDecorator(ArgumentDecorator[IntegerSetting]): ...





class DecoratorError(Exception):
    pass