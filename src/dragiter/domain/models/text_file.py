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

import pathlib
from dataclasses import dataclass
from typing import Union


@dataclass
class TextFile:
    path: Union[str, pathlib.Path]
    encoding: str = "utf-8"

    def __post_init__(self):
        """
        Called automatically after __init__.
        Ensures that the 'path' attribute is always a pathlib.Path instance.
        """
        if isinstance(self.path, str):
            self.path = pathlib.Path(self.path)

    def __repr__(self) -> str:
        return f"TextFile(path='{self.path}', encoding='{self.encoding}')"
