#!/usr/bin/env python3
"""
Bulk upload markdown files to Notion.

Usage:
    bulk-upload-notion <parent_page_id_or_url> <directory> [--config CONFIG]

Features:
    - Recursively finds all markdown files in directory
    - Skips files with notion_page_id (already uploaded)
    - Skips configured exclude patterns (.git, node_modules, etc.)
    - Progress logging and error reporting
    - Configurable rate limiting

Options:
    --config    Path to config file (default: config.yaml or env vars)

Example:
    bulk-upload-notion 2c6c95e7d72e80e39714fdb498641b84 ~/docs
"""

import sys
import logging
from pathlib import Path
from typing import List, Tuple, Optional
import time

from .config import load_config, Config
from .markdown_to_notion import upload_to_notion

# Set up logging
logger = logging.getLogger(__name__)


def should_exclude(file_path: Path, base_dir: Path, exclude_patterns: List[str]) -> bool:
    """
    Check if file should be excluded based on patterns.

    Args:
        file_path: File to check
        base_dir: Base directory for relative path calculation
        exclude_patterns: List of patterns to exclude

    Returns:
        True if file should be excluded
    """
    try:
        relative_path = file_path.relative_to(base_dir)
    except ValueError:
        # File is not relative to base_dir
        return False

    # Check each path component
    path_str = str(relative_path)
    for part in relative_path.parts:
        for pattern in exclude_patterns:
            if part == pattern or part.startswith(pattern):
                return True

    # Also check full path string
    for pattern in exclude_patterns:
        if pattern in path_str:
            return True

    return False


def has_notion_page_id(file_path: Path) -> bool:
    """
    Check if markdown file already has notion_page_id in frontmatter.

    Args:
        file_path: Markdown file to check

    Returns:
        True if file has notion_page_id
    """
    try:
        content = file_path.read_text()
        # Check for frontmatter with notion_page_id
        if content.startswith('---\n'):
            lines = content.split('\n')
            for line in lines[1:20]:  # Check first 20 lines
                if line.startswith('---'):
                    break
                if line.startswith('notion_page_id:'):
                    return True
    except Exception as e:
        logger.warning(f"Error reading {file_path}: {e}")

    return False


def find_markdown_files(directory: Path, exclude_patterns: List[str]) -> List[Path]:
    """
    Find all markdown files in directory, excluding patterns.

    Args:
        directory: Directory to search
        exclude_patterns: Patterns to exclude

    Returns:
        List of markdown file paths
    """
    markdown_files = []

    for file_path in directory.rglob("*.md"):
        if not file_path.is_file():
            continue

        # Skip excluded files
        if should_exclude(file_path, directory, exclude_patterns):
            logger.debug(f"Excluded (pattern): {file_path}")
            continue

        # Skip empty files
        if file_path.stat().st_size == 0:
            logger.debug(f"Excluded (empty): {file_path}")
            continue

        markdown_files.append(file_path)

    return sorted(markdown_files)


def bulk_upload(
    parent_id: str,
    directory: Path,
    config: Optional[Config] = None
) -> Tuple[int, int, int]:
    """
    Bulk upload markdown files to Notion.

    Args:
        parent_id: Parent page ID for all uploads
        directory: Directory to search for markdown files
        config: Configuration object

    Returns:
        Tuple of (uploaded, skipped, failed) counts
    """
    if config is None:
        config = load_config()

    if not directory.exists() or not directory.is_dir():
        raise ValueError(f"Directory not found: {directory}")

    logger.info(f"Bulk upload to Notion")
    logger.info(f"Parent page: {parent_id}")
    logger.info(f"Directory: {directory}")
    logger.info("")

    # Find all markdown files
    logger.info("Searching for markdown files...")
    markdown_files = find_markdown_files(directory, config.exclude_patterns)
    logger.info(f"Found {len(markdown_files)} markdown files")
    logger.info("")

    # Upload files
    uploaded = 0
    skipped = 0
    failed = 0

    for idx, file_path in enumerate(markdown_files, 1):
        logger.info(f"[{idx}/{len(markdown_files)}] {file_path.relative_to(directory)}")

        # Skip if already uploaded
        if has_notion_page_id(file_path):
            logger.info("  ⏭️  SKIPPED: Already has notion_page_id")
            skipped += 1
            continue

        # Try to upload
        try:
            logger.info("  📤 Uploading...")
            page_id, page_url, blocks = upload_to_notion(
                file_path,
                parent_id=parent_id,
                update_mode=False,
                config=config
            )
            logger.info(f"  ✅ SUCCESS: {blocks} blocks uploaded")
            uploaded += 1

            # Rate limiting between uploads
            if idx < len(markdown_files):
                time.sleep(config.rate_limit_delay)

        except Exception as e:
            logger.error(f"  ❌ FAILED: {str(e)}", exc_info=True)
            failed += 1

    return uploaded, skipped, failed


def main():
    """Main entry point for command-line usage."""
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    # Parse arguments
    parent_id = None
    directory = None
    config_file = None

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]

        if arg == '--config':
            if i + 1 < len(sys.argv):
                config_file = Path(sys.argv[i + 1])
                i += 1
            else:
                print("Error: --config requires a file path")
                sys.exit(1)
        elif parent_id is None:
            parent_id = arg
        elif directory is None:
            directory = Path(arg)
        else:
            print(f"Error: Unexpected argument: {arg}")
            sys.exit(1)

        i += 1

    if parent_id is None or directory is None:
        print("Error: parent_page_id and directory are required")
        print(__doc__)
        sys.exit(1)

    # Load configuration
    try:
        config = load_config(config_file)
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Set NOTION_TOKEN environment variable or create config.yaml")
        sys.exit(1)

    # Set up logging
    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format=config.log_format
    )

    # Bulk upload
    try:
        uploaded, skipped, failed = bulk_upload(parent_id, directory, config)

        print(f"\n{'='*40}")
        print("Summary")
        print(f"{'='*40}")
        print(f"Uploaded:  {uploaded}")
        print(f"Skipped:   {skipped}")
        print(f"Failed:    {failed}")
        print(f"{'='*40}")

        return 0 if failed == 0 else 1

    except Exception as e:
        logger.error(f"Bulk upload failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
