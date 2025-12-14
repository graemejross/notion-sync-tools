"""Notion Sync Tools - Bidirectional markdown ↔ Notion sync."""

__version__ = "1.0.0"
__author__ = "Graeme Ross"
__license__ = "MIT"

from .config import Config
from .markdown_to_notion import upload_to_notion
from .notion_to_markdown import download_from_notion

__all__ = [
    "Config",
    "upload_to_notion",
    "download_from_notion",
]
