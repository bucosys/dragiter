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

"""
Infrastructure / CLI Layer
Responsible for exporting package resources (docs + examples)
"""

import importlib.resources
import shutil
import sys
from pathlib import Path


class ResourceExporter:
    @staticmethod
    def export(resource_name: str) -> None:
        """
        Exports a folder from the package (docs or examples) to the file system.

        Args:
        resource_name (str): The name of the resource to export, typically 'docs' or 'examples'.
        """

        try:

            target_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
            dest_path = target_root / resource_name

            # get access to resources of package
            pkg_files = importlib.resources.files("dragiter") / resource_name

            if not pkg_files.exists():
                print(f"❌ Resource '{resource_name}' not found in package.", file=sys.stderr)
                sys.exit(1)

            shutil.copytree(pkg_files, dest_path, dirs_exist_ok=True)
            print(f"✅ {resource_name.capitalize()} successfully exported to: {dest_path}")

        except Exception as e:
            print(f"❌ Error exporting {resource_name}: {e}", file=sys.stderr)
            sys.exit(1)
