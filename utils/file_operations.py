"""
File operation utilities.
"""

import json
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class FileOperations:
    """Helper class for file operations."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def read_yaml(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Read YAML file.

        Args:
            file_path: Path to YAML file

        Returns:
            Dictionary with YAML contents or None
        """
        try:
            with open(file_path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Error reading YAML file {file_path}: {str(e)}")
            return None

    def write_yaml(self, file_path: Path, data: Dict[str, Any]) -> bool:
        """
        Write YAML file.

        Args:
            file_path: Path to YAML file
            data: Data to write

        Returns:
            True if successful
        """
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w") as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            return True
        except Exception as e:
            self.logger.error(f"Error writing YAML file {file_path}: {str(e)}")
            return False

    def read_json(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Read JSON file.

        Args:
            file_path: Path to JSON file

        Returns:
            Dictionary with JSON contents or None
        """
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error reading JSON file {file_path}: {str(e)}")
            return None

    def write_json(
        self, file_path: Path, data: Dict[str, Any], pretty: bool = True
    ) -> bool:
        """
        Write JSON file.

        Args:
            file_path: Path to JSON file
            data: Data to write
            pretty: Whether to pretty-print

        Returns:
            True if successful
        """
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w") as f:
                if pretty:
                    json.dump(data, f, indent=2)
                else:
                    json.dump(data, f)
            return True
        except Exception as e:
            self.logger.error(f"Error writing JSON file {file_path}: {str(e)}")
            return False

    def copy_directory(
        self, source: Path, destination: Path, ignore_patterns: Optional[list] = None
    ) -> bool:
        """
        Copy directory recursively.

        Args:
            source: Source directory
            destination: Destination directory
            ignore_patterns: List of patterns to ignore

        Returns:
            True if successful
        """
        try:
            if ignore_patterns:
                ignore_func = shutil.ignore_patterns(*ignore_patterns)
            else:
                ignore_func = None

            shutil.copytree(source, destination, ignore=ignore_func, dirs_exist_ok=True)
            return True
        except Exception as e:
            self.logger.error(f"Error copying directory {source} to {destination}: {str(e)}")
            return False

    def create_backup(self, source: Path, backup_dir: Path) -> Optional[Path]:
        """
        Create backup of directory.

        Args:
            source: Source directory to backup
            backup_dir: Backup directory

        Returns:
            Path to backup or None
        """
        try:
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{source.name}_backup_{timestamp}"
            backup_path = backup_dir / backup_name

            backup_dir.mkdir(parents=True, exist_ok=True)

            # Ignore common directories
            ignore_patterns = [
                "node_modules",
                ".git",
                "target",
                "build",
                "dist",
                "__pycache__",
                "*.pyc",
                ".DS_Store",
            ]

            if self.copy_directory(source, backup_path, ignore_patterns):
                self.logger.info(f"Backup created: {backup_path}")
                return backup_path

            return None

        except Exception as e:
            self.logger.error(f"Error creating backup: {str(e)}")
            return None

    def find_files(
        self, directory: Path, pattern: str, recursive: bool = True
    ) -> list[Path]:
        """
        Find files matching pattern.

        Args:
            directory: Directory to search
            pattern: Glob pattern (e.g., '*.java')
            recursive: Whether to search recursively

        Returns:
            List of matching file paths
        """
        try:
            if recursive:
                return list(directory.rglob(pattern))
            else:
                return list(directory.glob(pattern))
        except Exception as e:
            self.logger.error(f"Error finding files: {str(e)}")
            return []

    def ensure_directory(self, directory: Path) -> bool:
        """
        Ensure directory exists.

        Args:
            directory: Directory path

        Returns:
            True if successful
        """
        try:
            directory.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            self.logger.error(f"Error creating directory {directory}: {str(e)}")
            return False
