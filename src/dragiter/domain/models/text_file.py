# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

from dataclasses import dataclass
import pathlib


@dataclass
class TextFile:
    path: str | pathlib.Path
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
