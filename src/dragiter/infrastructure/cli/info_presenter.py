"""
Infrastructure / CLI Layer
Responsible for extracting detailed information from info.txt file
"""

import importlib.resources


class InfoPresenter:

    @staticmethod
    def show_usage() -> int:
        print("Usage: dragiter [OPTIONS]")
        print("\nHelp & Assets:")
        print("  dragiter --info                Show detailed informations (from info.txt)")
        print("  dragiter-gen-docs [path]       Extract documentation (default: current folder)")
        print("  dragiter-gen-examples [path]   Extract examples (default: current folder)")
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
[dragiter – Deterministic RAG Iterator.]
"""
        print(banner)
        print("-" * 60)
        print("")
