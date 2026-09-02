# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from dataclasses import dataclass
from typing import Generic, TypeVar

from dragiter.domain.models.settings import (
    APIStringSetting,
    BoolSetting,
    FloatSetting,
    IntegerSetting,
    PathSetting,
    StringSetting,
)

T = TypeVar('T')


@dataclass
class ArgumentDecorator(Generic[T]):
    value_setting_object: T
    short_key: str = "-"
    help: str = "Unknown basic setting"
    required: bool = False

    # for now value setting object is responsible to define long key
    def __post_init__(self):
        if self.value_setting_object is not None:
            self.long_key = self.value_setting_object.key
        else:
            raise AttributeError("Key of ConfigValue object has not been set and cannot be changed!")


@dataclass
class StringSettingArgumentDecorator(ArgumentDecorator[StringSetting]): ...

@dataclass
class APIStringSettingArgumentDecorator(ArgumentDecorator[APIStringSetting]): ...

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
