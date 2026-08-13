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

"""
Infrastructure / CLI Layer
Responsible for extracting detailed information from info.txt file
"""

import importlib.resources
from dragiter import __version__, __tool_name__

class InfoPresenter:

    @staticmethod
    def show_usage() -> int:
        print("Usage: dragiter [OPTIONS]")
        print("\nHelp & Assets:")
        print("  dragiter --help              Show command line help")
        print("  dragiter --info              Show detailed information (man page)")
        print("  dragiter-gen-docs [PATH]     Extract documentation (default: ./docs/)")
        print("  dragiter-gen-examples [PATH] Extract examples (default: ./examples/)")
        return 0

    @staticmethod
    def show_help() -> int:
        """Loads info.txt and renders it like a real Unix man page."""

        try:
            from importlib.resources import files
            help_path = importlib.resources.files("dragiter") / "docs" / "info.txt"
            md_text = help_path.read_text(encoding="utf-8")
            print(md_text)
            return 0

        except Exception as e:
            print(f"Error loading help: {e}")
            return 1

    @staticmethod
    def print_banner() -> None:
        banner = r"""
    __                   __                 
  __| |_ __  __ _  __ _(_) |_ ___ _ __  
 / _` | '__|/ _` |/ _` | | __/ _ \ '__| 
| (_| | |  | (_| | (_| | | |_| __/ |    
 \__,_|_|   \__,_|\__, |_|\__\___|_|    
                  |___/        
"""
        print(banner)
        print(f"[dragiter v{__version__} – Deterministic Context Iterator.]")
        print("-" * 70)
        print("")
