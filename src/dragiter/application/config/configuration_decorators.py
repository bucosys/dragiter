# =============================================================================
# dragiter - Deterministic RAG Iterator
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

from dataclasses import dataclass
from typing import Generic, TypeVar

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
