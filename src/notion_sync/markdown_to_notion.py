#!/usr/bin/env python3
"""
Upload markdown to Notion with full formatting and link preservation.

Usage:
    markdown-to-notion <markdown_file> <parent_page_id_or_url> [--update] [--config CONFIG]

Features:
    - Preserves bold, italic, code, strikethrough, links
    - Reads YAML frontmatter for page ID (supports updates)
    - Handles nested lists, code blocks, quotes, tables
    - Preserves internal Notion links
    - Supports creating or updating pages

Options:
    --update    Update existing page (uses notion_page_id from frontmatter)
    --config    Path to config file (default: config.yaml or env vars)

Example:
    # Create new page:
    markdown-to-notion schema.md 2bfc95e7d72e816486a5cfb9a97fa8c9

    # Update existing page (requires frontmatter):
    markdown-to-notion schema.md --update
"""

import urllib.request
import urllib.error
import json
import sys
import re
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

from .config import load_config, Config

# Set up logging
logger = logging.getLogger(__name__)


def extract_page_id(input_str: str) -> str:
    """Extract page ID from URL or use directly if it's an ID."""
    if 'notion.so' in input_str:
        match = re.search(
            r'([a-f0-9]{32}|[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})',
            input_str
        )
        if match:
            page_id = match.group(1)
            if '-' not in page_id:
                page_id = f"{page_id[:8]}-{page_id[8:12]}-{page_id[12:16]}-{page_id[16:20]}-{page_id[20:]}"
            return page_id
    return input_str


def parse_frontmatter(content: str) -> Tuple[Dict[str, str], str]:
    """Parse YAML frontmatter from markdown."""
    frontmatter = {}
    content_without_frontmatter = content

    if content.startswith('---\n'):
        parts = content.split('---\n', 2)
        if len(parts) >= 3:
            frontmatter_text = parts[1]
            content_without_frontmatter = parts[2].lstrip('\n')

            # Parse YAML frontmatter
            for line in frontmatter_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    frontmatter[key.strip()] = value.strip()

    return frontmatter, content_without_frontmatter


def parse_markdown_formatting(text: str, max_length: int) -> List[Dict[str, Any]]:
    """Parse markdown formatting into Notion rich text objects."""
    rich_text = []

    # Split by code spans first
    parts = re.split(r'(`[^`]+`)', text)

    for part in parts:
        if not part:
            continue

        # Handle code spans
        if part.startswith('`') and part.endswith('`'):
            content = part[1:-1]
            if len(content) > max_length:
                content = content[:max_length]
            rich_text.append({
                "type": "text",
                "text": {"content": content},
                "annotations": {"code": True}
            })
            continue

        # Handle links, bold, italic
        pos = 0
        while pos < len(part):
            # Try to match link
            link_match = re.match(r'\[([^\]]+)\]\(([^\)]+)\)', part[pos:])
            if link_match:
                link_text = link_match.group(1)
                link_url = link_match.group(2)

                # Check for formatting within link text
                annotations = {
                    "bold": '**' in link_text,
                    "italic": '*' in link_text and '**' not in link_text,
                    "strikethrough": '~~' in link_text
                }

                # Clean up link text
                clean_text = link_text.replace('**', '').replace('*', '').replace('~~', '')

                if len(clean_text) > max_length:
                    clean_text = clean_text[:max_length]

                rich_text.append({
                    "type": "text",
                    "text": {"content": clean_text, "link": {"url": link_url}},
                    "annotations": annotations
                })
                pos += len(link_match.group(0))
                continue

            # Try to match **bold**
            bold_match = re.match(r'\*\*([^\*]+)\*\*', part[pos:])
            if bold_match:
                content = bold_match.group(1)
                if len(content) > max_length:
                    content = content[:max_length]
                rich_text.append({
                    "type": "text",
                    "text": {"content": content},
                    "annotations": {"bold": True}
                })
                pos += len(bold_match.group(0))
                continue

            # Try to match *italic*
            italic_match = re.match(r'\*([^\*]+)\*', part[pos:])
            if italic_match:
                content = italic_match.group(1)
                if len(content) > max_length:
                    content = content[:max_length]
                rich_text.append({
                    "type": "text",
                    "text": {"content": content},
                    "annotations": {"italic": True}
                })
                pos += len(italic_match.group(0))
                continue

            # Try to match ~~strikethrough~~
            strike_match = re.match(r'~~([^~]+)~~', part[pos:])
            if strike_match:
                content = strike_match.group(1)
                if len(content) > max_length:
                    content = content[:max_length]
                rich_text.append({
                    "type": "text",
                    "text": {"content": content},
                    "annotations": {"strikethrough": True}
                })
                pos += len(strike_match.group(0))
                continue

            # Regular text until next special character
            next_special = len(part)
            for pattern in [r'\[', r'\*\*', r'\*', r'~~']:
                match = re.search(pattern, part[pos:])
                if match and match.start() < next_special - pos:
                    next_special = pos + match.start()

            if next_special > pos:
                content = part[pos:next_special]
                if len(content) > max_length:
                    content = content[:max_length]
                rich_text.append({
                    "type": "text",
                    "text": {"content": content}
                })
                pos = next_special
            else:
                pos += 1

    return rich_text if rich_text else [{"type": "text", "text": {"content": ""}}]


def markdown_to_notion_blocks(md_content: str, config: Config) -> List[Dict[str, Any]]:
    """Convert markdown to Notion block objects."""
    blocks = []
    lines = md_content.split('\n')
    i = 0
    max_text_length = config.max_text_length

    while i < len(lines):
        line = lines[i].rstrip()

        # Skip empty lines
        if not line:
            i += 1
            continue

        # Heading 1
        if line.startswith('# '):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": parse_markdown_formatting(line[2:], max_text_length)
                }
            })
        # Heading 2
        elif line.startswith('## '):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": parse_markdown_formatting(line[3:], max_text_length)
                }
            })
        # Heading 3
        elif line.startswith('### '):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": parse_markdown_formatting(line[4:], max_text_length)
                }
            })
        # Code block
        elif line.startswith('```'):
            language_match = re.match(r'```([a-z0-9 +#]+)?', line, re.IGNORECASE)
            language = (language_match.group(1).strip() or 'plain text') if language_match and language_match.group(1) else 'plain text'

            code_content = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_content.append(lines[i].rstrip())
                i += 1

            code_text = '\n'.join(code_content)
            if len(code_text) > max_text_length:
                code_text = code_text[:max_text_length]

            blocks.append({
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [{"type": "text", "text": {"content": code_text}}],
                    "language": language
                }
            })
        # Table (detect by pipe characters)
        elif '|' in line and i + 1 < len(lines) and '|' in lines[i + 1]:
            # Collect table rows
            table_lines = []
            while i < len(lines) and '|' in lines[i]:
                table_lines.append(lines[i].strip())
                i += 1
            i -= 1  # Back up one since we'll increment at the end

            # Skip if it's a separator row only
            if table_lines and not all('-' in line or line == '|' for line in table_lines):
                # Parse table
                rows = []
                for table_line in table_lines:
                    # Skip separator rows
                    if table_line.startswith('|---') or table_line.startswith('|-'):
                        continue
                    # Parse cells
                    cells = [cell.strip() for cell in table_line.split('|')]
                    cells = [c for c in cells if c]  # Remove empty strings
                    if cells:
                        rows.append(cells)

                # Create proper Notion table
                if rows and len(rows) > 0:
                    num_cols = len(rows[0])

                    # Create table block with children
                    table_children = []
                    for row in rows:
                        # Pad row if needed
                        while len(row) < num_cols:
                            row.append("")

                        # Create table_row with cells
                        cells = []
                        for cell_text in row[:num_cols]:
                            cells.append(parse_markdown_formatting(cell_text, max_text_length))

                        table_children.append({
                            "type": "table_row",
                            "table_row": {
                                "cells": cells
                            }
                        })

                    # Notion has a 100-row limit - split if needed
                    MAX_TABLE_ROWS = 100

                    if len(table_children) <= MAX_TABLE_ROWS:
                        blocks.append({
                            "object": "block",
                            "type": "table",
                            "table": {
                                "table_width": num_cols,
                                "has_column_header": True,
                                "has_row_header": False,
                                "children": table_children
                            }
                        })
                    else:
                        # Split into multiple tables
                        header_row = table_children[0] if table_children else None
                        data_rows = table_children[1:] if len(table_children) > 1 else []

                        chunk_size = MAX_TABLE_ROWS - 1
                        for chunk_idx in range(0, len(data_rows), chunk_size):
                            chunk = data_rows[chunk_idx:chunk_idx + chunk_size]
                            chunk_with_header = [header_row] + chunk if header_row else chunk

                            blocks.append({
                                "object": "block",
                                "type": "table",
                                "table": {
                                    "table_width": num_cols,
                                    "has_column_header": True,
                                    "has_row_header": False,
                                    "children": chunk_with_header
                                }
                            })

                            # Add note between split tables
                            if chunk_idx + chunk_size < len(data_rows):
                                blocks.append({
                                    "object": "block",
                                    "type": "paragraph",
                                    "paragraph": {
                                        "rich_text": [{
                                            "type": "text",
                                            "text": {"content": f"(Table continued - part {chunk_idx // chunk_size + 2})"}
                                        }]
                                    }
                                })
        # Divider
        elif line.strip() == '---':
            blocks.append({
                "object": "block",
                "type": "divider",
                "divider": {}
            })
        # Quote
        elif line.startswith('> '):
            blocks.append({
                "object": "block",
                "type": "quote",
                "quote": {
                    "rich_text": parse_markdown_formatting(line[2:], max_text_length)
                }
            })
        # Bulleted list
        elif line.startswith('- ') and not line.startswith('- ['):
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": parse_markdown_formatting(line[2:], max_text_length)
                }
            })
        # To-do list
        elif line.startswith('- ['):
            checked = 'x' in line[0:5].lower()
            content = re.sub(r'^- \[[x ]\] ', '', line, flags=re.IGNORECASE)
            blocks.append({
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": parse_markdown_formatting(content, max_text_length),
                    "checked": checked
                }
            })
        # Numbered list
        elif re.match(r'^\d+\. ', line):
            content = re.sub(r'^\d+\. ', '', line)
            blocks.append({
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {
                    "rich_text": parse_markdown_formatting(content, max_text_length)
                }
            })
        # Paragraph (default)
        else:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": parse_markdown_formatting(line, max_text_length)
                }
            })

        i += 1

    return blocks


def make_api_request(
    url: str,
    token: str,
    api_version: str,
    method: str = 'GET',
    data: Optional[bytes] = None,
    config: Optional[Config] = None
) -> Dict[str, Any]:
    """
    Make an API request with retries and error handling.

    Args:
        url: API endpoint URL
        token: Notion API token
        api_version: Notion API version
        method: HTTP method
        data: Request payload
        config: Configuration object

    Returns:
        API response as dict

    Raises:
        urllib.error.HTTPError: On API errors after retries
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": api_version
    }

    retry_attempts = config.retry_attempts if config else 3
    retry_delay = config.retry_delay if config else 1.0

    last_error = None

    for attempt in range(retry_attempts):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read())

        except urllib.error.HTTPError as e:
            last_error = e
            error_body = e.read().decode('utf-8')

            # Check if it's a rate limit error
            if e.code == 429:
                wait_time = retry_delay * (attempt + 1)
                logger.warning(f"Rate limited. Waiting {wait_time}s before retry {attempt + 1}/{retry_attempts}")
                time.sleep(wait_time)
                continue

            # For other errors, log and retry
            logger.warning(f"Request failed (attempt {attempt + 1}/{retry_attempts}): {e.code} - {error_body}")

            if attempt < retry_attempts - 1:
                time.sleep(retry_delay)
                continue
            else:
                raise

        except Exception as e:
            last_error = e
            logger.warning(f"Request failed (attempt {attempt + 1}/{retry_attempts}): {str(e)}")

            if attempt < retry_attempts - 1:
                time.sleep(retry_delay)
                continue
            else:
                raise

    # If we got here, all retries failed
    if last_error:
        raise last_error
    else:
        raise RuntimeError("API request failed after all retries")


def create_notion_page(token: str, api_version: str, title: str, parent_id: str, config: Config) -> Tuple[str, str]:
    """Create a new Notion page."""
    url = "https://api.notion.com/v1/pages"

    payload = {
        "parent": {"page_id": parent_id},
        "properties": {
            "title": {
                "type": "title",
                "title": [{"type": "text", "text": {"content": title}}]
            }
        }
    }

    result = make_api_request(
        url,
        token,
        api_version,
        method='POST',
        data=json.dumps(payload).encode('utf-8'),
        config=config
    )

    return result['id'], result['url']


def delete_all_blocks(token: str, api_version: str, page_id: str, config: Config) -> int:
    """Delete all child blocks from a page."""
    # Get all existing blocks
    all_blocks = []
    start_cursor = None

    while True:
        url = f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=100"
        if start_cursor:
            url += f"&start_cursor={start_cursor}"

        result = make_api_request(url, token, api_version, config=config)
        all_blocks.extend(result.get('results', []))

        if result.get('has_more'):
            start_cursor = result.get('next_cursor')
        else:
            break

    # Delete each block
    deleted = 0
    for block in all_blocks:
        block_id = block['id']
        url = f"https://api.notion.com/v1/blocks/{block_id}"

        try:
            make_api_request(url, token, api_version, method='DELETE', config=config)
            deleted += 1
        except urllib.error.HTTPError:
            # Ignore errors for blocks that can't be deleted
            pass

        # Rate limiting
        if config:
            time.sleep(config.rate_limit_delay)

    return deleted


def upload_blocks_to_page(
    token: str,
    api_version: str,
    page_id: str,
    blocks: List[Dict[str, Any]],
    config: Config
) -> int:
    """Upload blocks to a Notion page in batches."""
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"

    total_uploaded = 0
    max_blocks = config.max_blocks_per_request

    for i in range(0, len(blocks), max_blocks):
        batch = blocks[i:i + max_blocks]
        payload = json.dumps({"children": batch}).encode('utf-8')

        result = make_api_request(
            url,
            token,
            api_version,
            method='PATCH',
            data=payload,
            config=config
        )

        uploaded = len(result.get('results', []))
        total_uploaded += uploaded
        logger.info(f"Batch {i//max_blocks + 1}: {uploaded} blocks uploaded")

        # Rate limiting between batches
        if i + max_blocks < len(blocks):
            time.sleep(config.rate_limit_delay)

    return total_uploaded


def upload_to_notion(
    md_file: Path,
    parent_id: Optional[str] = None,
    update_mode: bool = False,
    config: Optional[Config] = None
) -> Tuple[str, str, int]:
    """
    Upload markdown file to Notion.

    Args:
        md_file: Path to markdown file
        parent_id: Parent page ID (for create mode)
        update_mode: Whether to update existing page
        config: Configuration object

    Returns:
        Tuple of (page_id, page_url, blocks_uploaded)

    Raises:
        ValueError: If invalid arguments
        FileNotFoundError: If markdown file doesn't exist
    """
    if not md_file.exists():
        raise FileNotFoundError(f"File not found: {md_file}")

    if config is None:
        config = load_config()

    # Read markdown file
    logger.info(f"Reading markdown file: {md_file}")
    md_content = md_file.read_text()

    # Parse frontmatter
    frontmatter, content = parse_frontmatter(md_content)

    # Generate title
    if 'title' in frontmatter:
        title = frontmatter['title']
    else:
        # Common filenames that need parent folder prefix
        common_names = ['README', 'readme', 'INDEX', 'index', 'todos', 'TODOS']
        if md_file.stem in common_names:
            parent_name = md_file.parent.name
            title = f"{parent_name}/{md_file.stem}"
        else:
            title = md_file.stem

    # Determine mode
    if update_mode:
        page_id = frontmatter.get('notion_page_id')
        if not page_id:
            raise ValueError("--update requires 'notion_page_id' in frontmatter")
        logger.info(f"Update mode: Updating page {page_id}")
        logger.info(f"   Title: {title}")
    else:
        if not parent_id:
            raise ValueError("parent_page_id required for creating new pages")
        parent_id = extract_page_id(parent_id)
        logger.info(f"Create mode: New page under {parent_id}")
        logger.info(f"   Title: {title}")

    # Convert markdown to Notion blocks
    logger.info("Converting markdown to Notion blocks...")
    blocks = markdown_to_notion_blocks(content, config)
    logger.info(f"   Generated {len(blocks)} blocks")

    # Create or update page
    if update_mode:
        logger.info("Deleting existing blocks...")
        deleted = delete_all_blocks(config.notion_token, config.api_version, page_id, config)
        logger.info(f"   Deleted {deleted} blocks")

        logger.info("Uploading new blocks...")
        total_uploaded = upload_blocks_to_page(
            config.notion_token,
            config.api_version,
            page_id,
            blocks,
            config
        )
        page_url = frontmatter.get('notion_url', f"https://notion.so/{page_id}")
    else:
        logger.info("Creating new Notion page...")
        page_id, page_url = create_notion_page(
            config.notion_token,
            config.api_version,
            title,
            parent_id,
            config
        )
        logger.info(f"   Page created: {page_id}")

        logger.info(f"Uploading {len(blocks)} blocks...")
        total_uploaded = upload_blocks_to_page(
            config.notion_token,
            config.api_version,
            page_id,
            blocks,
            config
        )

        # Update markdown file with notion_page_id
        frontmatter['notion_page_id'] = page_id
        frontmatter['notion_url'] = page_url
        frontmatter['title'] = title
        frontmatter['uploaded'] = datetime.now().isoformat()

        # Write updated frontmatter
        updated_content = "---\n"
        for key, value in frontmatter.items():
            updated_content += f"{key}: {value}\n"
        updated_content += "---\n\n" + content

        md_file.write_text(updated_content)
        logger.info(f"   Updated {md_file.name} with notion_page_id")

    return page_id, page_url, total_uploaded


def main():
    """Main entry point for command-line usage."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    # Parse arguments
    md_file = None
    parent_id = None
    update_mode = False
    config_file = None

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]

        if arg == '--update':
            update_mode = True
        elif arg == '--config':
            if i + 1 < len(sys.argv):
                config_file = Path(sys.argv[i + 1])
                i += 1
            else:
                print("Error: --config requires a file path")
                sys.exit(1)
        elif md_file is None:
            md_file = Path(arg)
        elif parent_id is None and not update_mode:
            parent_id = arg
        else:
            print(f"Error: Unexpected argument: {arg}")
            sys.exit(1)

        i += 1

    if md_file is None:
        print("Error: markdown_file is required")
        sys.exit(1)

    if not update_mode and parent_id is None:
        print("Error: parent_page_id required for creating new pages")
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

    # Upload to Notion
    try:
        page_id, page_url, total_uploaded = upload_to_notion(
            md_file,
            parent_id,
            update_mode,
            config
        )

        print(f"\n✅ Upload complete!")
        print(f"   Total blocks: {total_uploaded}")
        print(f"   Notion page: {page_url}")

        return 0

    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
