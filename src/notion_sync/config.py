"""Configuration management for Notion Sync Tools."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List


class Config:
    """Configuration manager with support for YAML files and environment variables."""

    DEFAULT_CONFIG = {
        "notion": {
            "token": "",
            "api_version": "2022-06-28",
        },
        "api": {
            "max_blocks_per_request": 100,
            "max_text_length": 2000,
            "retry_attempts": 3,
            "retry_delay": 1.0,
            "rate_limit_delay": 0.5,
        },
        "bulk_upload": {
            "exclude_patterns": [
                ".git",
                "node_modules",
                "__pycache__",
                ".venv",
                "venv",
                ".pytest_cache",
            ]
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file": "",
        },
    }

    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize configuration.

        Args:
            config_file: Path to YAML config file. If None, looks for config.yaml
                        in current directory, then ~/.notion-sync-tools/config.yaml
        """
        self.config = self.DEFAULT_CONFIG.copy()

        # Load from YAML file if available
        if config_file:
            self._load_yaml(config_file)
        else:
            # Try default locations
            for path in [
                Path.cwd() / "config.yaml",
                Path.home() / ".notion-sync-tools" / "config.yaml",
            ]:
                if path.exists():
                    self._load_yaml(path)
                    break

        # Override with environment variables
        self._load_from_env()

        # Validate required fields
        self._validate()

    def _load_yaml(self, config_file: Path) -> None:
        """Load configuration from YAML file."""
        if not config_file.exists():
            return

        with open(config_file, "r") as f:
            yaml_config = yaml.safe_load(f)

        if yaml_config:
            self._deep_update(self.config, yaml_config)

    def _load_from_env(self) -> None:
        """Load configuration from environment variables."""
        # Notion token (most important)
        if os.getenv("NOTION_TOKEN"):
            self.config["notion"]["token"] = os.getenv("NOTION_TOKEN")

        # API version
        if os.getenv("NOTION_API_VERSION"):
            self.config["notion"]["api_version"] = os.getenv("NOTION_API_VERSION")

        # Rate limits
        if os.getenv("NOTION_MAX_BLOCKS"):
            self.config["api"]["max_blocks_per_request"] = int(
                os.getenv("NOTION_MAX_BLOCKS")
            )

        if os.getenv("NOTION_RETRY_ATTEMPTS"):
            self.config["api"]["retry_attempts"] = int(
                os.getenv("NOTION_RETRY_ATTEMPTS")
            )

        # Logging
        if os.getenv("LOG_LEVEL"):
            self.config["logging"]["level"] = os.getenv("LOG_LEVEL")

    def _deep_update(self, base: Dict, updates: Dict) -> None:
        """Recursively update nested dictionaries."""
        for key, value in updates.items():
            if (
                key in base
                and isinstance(base[key], dict)
                and isinstance(value, dict)
            ):
                self._deep_update(base[key], value)
            else:
                base[key] = value

    def _validate(self) -> None:
        """Validate that required configuration is present."""
        if not self.config["notion"]["token"]:
            raise ValueError(
                "Notion token is required. Set NOTION_TOKEN environment variable "
                "or add 'notion.token' to config.yaml"
            )

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Args:
            key_path: Dot-separated path (e.g., 'notion.token')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key_path.split(".")
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    @property
    def notion_token(self) -> str:
        """Get Notion API token."""
        return self.config["notion"]["token"]

    @property
    def api_version(self) -> str:
        """Get Notion API version."""
        return self.config["notion"]["api_version"]

    @property
    def max_blocks_per_request(self) -> int:
        """Get maximum blocks per request."""
        return self.config["api"]["max_blocks_per_request"]

    @property
    def max_text_length(self) -> int:
        """Get maximum text length."""
        return self.config["api"]["max_text_length"]

    @property
    def retry_attempts(self) -> int:
        """Get number of retry attempts."""
        return self.config["api"]["retry_attempts"]

    @property
    def retry_delay(self) -> float:
        """Get retry delay in seconds."""
        return self.config["api"]["retry_delay"]

    @property
    def rate_limit_delay(self) -> float:
        """Get rate limit delay in seconds."""
        return self.config["api"]["rate_limit_delay"]

    @property
    def exclude_patterns(self) -> List[str]:
        """Get bulk upload exclude patterns."""
        return self.config["bulk_upload"]["exclude_patterns"]

    @property
    def log_level(self) -> str:
        """Get logging level."""
        return self.config["logging"]["level"]

    @property
    def log_format(self) -> str:
        """Get logging format."""
        return self.config["logging"]["format"]

    @property
    def log_file(self) -> str:
        """Get log file path."""
        return self.config["logging"]["file"]


def load_config(config_file: Optional[Path] = None) -> Config:
    """
    Load configuration from file or environment.

    Args:
        config_file: Optional path to YAML config file

    Returns:
        Config object

    Raises:
        ValueError: If required configuration is missing
    """
    return Config(config_file)
