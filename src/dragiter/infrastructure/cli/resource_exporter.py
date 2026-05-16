"""
Infrastructure / CLI Layer
Verantwortlich für das Exportieren von Package-Ressourcen (docs + examples)
"""

import importlib.resources
import shutil
import sys
from pathlib import Path


class ResourceExporter:
    """Exportiert eingebettete Package-Ressourcen auf das Dateisystem."""

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


