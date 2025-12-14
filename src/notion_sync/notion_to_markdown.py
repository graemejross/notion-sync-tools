#!/usr/bin/env python3
"""
Download Notion pages to markdown with full formatting and link preservation.

Usage:
    notion-to-markdown <page_id_or_url> <output_file> [--config CONFIG]

Features:
    - Preserves bold, italic, code, strikethrough, links
    - Saves page ID and metadata as YAML frontmatter
    - Handles nested pages and databases
    - Preserves Notion internal links

Options:
    --config    Path to config file (default: config.yaml or env vars)

Example:
    notion-to-markdown https://www.notion.so/Database-123abc schema.md
    notion-to-markdown 2bfc95e7d72e816486a5cfb9a97fa8c9 schema.md
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
            # Add hyphens if not present
            if '-' not in page_id:
                page_id = f"{page_id[:8]}-{page_id[8:12]}-{page_id[12:16]}-{page_id[16:20]}-{page_id[20:]}"
            return page_id
    # Already a page ID
    return input_str


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
        "Notion-Version": api_version
    }

    if data:
        headers["Content-Type"] = "application/json"

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


def get_page(token: str, api_version: str, page_id: str, config: Config) -> Dict[str, Any]:
    """Get page metadata."""
    url = f"https://api.notion.com/v1/pages/{page_id}"
    return make_api_request(url, token, api_version, config=config)


def get_all_blocks(token: str, api_version: str, page_id: str, config: Config) -> List[Dict[str, Any]]:
    """Get all blocks from a page, handling pagination."""
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
            # Rate limiting between pagination requests
            time.sleep(config.rate_limit_delay)
        else:
            break

    return all_blocks


def rich_text_to_markdown(rich_text_array: List[Dict[str, Any]]) -> str:
    """Convert Notion rich text array to markdown with formatting and links."""
    if not rich_text_array:
        return ""

    result = []
    for text_obj in rich_text_array:
        content = text_obj['text']['content']
        annotations = text_obj.get('annotations', {})
        link = text_obj['text'].get('link')

        # Apply formatting (in order: code, bold, italic, strikethrough)
        if annotations.get('code'):
            content = f"`{content}`"
        if annotations.get('bold'):
            content = f"**{content}**"
        if annotations.get('italic'):
            content = f"*{content}*"
        if annotations.get('strikethrough'):
            content = f"~~{content}~~"

        # Apply link
        if link:
            link_url = link['url']
            content = f"[{content}]({link_url})"

        result.append(content)

    return ''.join(result)


def block_to_markdown(block: Dict[str, Any], page_links_map: Optional[Dict[str, str]] = None) -> str:
    """Convert a Notion block to markdown."""
    block_type = block['type']

    if page_links_map is None:
        page_links_map = {}

    try:
        # Paragraph
        if block_type == 'paragraph':
            return rich_text_to_markdown(block['paragraph'].get('rich_text', []))

        # Headings
        elif block_type == 'heading_1':
            text = rich_text_to_markdown(block['heading_1'].get('rich_text', []))
            return f"# {text}"

        elif block_type == 'heading_2':
            text = rich_text_to_markdown(block['heading_2'].get('rich_text', []))
            return f"## {text}"

        elif block_type == 'heading_3':
            text = rich_text_to_markdown(block['heading_3'].get('rich_text', []))
            return f"### {text}"

        # Lists
        elif block_type == 'bulleted_list_item':
            text = rich_text_to_markdown(block['bulleted_list_item'].get('rich_text', []))
            return f"- {text}"

        elif block_type == 'numbered_list_item':
            text = rich_text_to_markdown(block['numbered_list_item'].get('rich_text', []))
            return f"1. {text}"

        elif block_type == 'to_do':
            text = rich_text_to_markdown(block['to_do'].get('rich_text', []))
            checked = 'x' if block['to_do'].get('checked') else ' '
            return f"- [{checked}] {text}"

        # Code
        elif block_type == 'code':
            code = rich_text_to_markdown(block['code'].get('rich_text', []))
            language = block['code'].get('language', 'plain text')
            return f"```{language}\n{code}\n```"

        # Quote
        elif block_type == 'quote':
            text = rich_text_to_markdown(block['quote'].get('rich_text', []))
            return f"> {text}"

        # Callout
        elif block_type == 'callout':
            text = rich_text_to_markdown(block['callout'].get('rich_text', []))
            icon = block['callout'].get('icon', {})
            emoji = icon.get('emoji', '💡') if icon.get('type') == 'emoji' else '💡'
            return f"> {emoji} {text}"

        # Divider
        elif block_type == 'divider':
            return "---"

        # Toggle
        elif block_type == 'toggle':
            text = rich_text_to_markdown(block['toggle'].get('rich_text', []))
            return f"<details><summary>{text}</summary>\n\n</details>"

        # Table
        elif block_type == 'table':
            # Tables are handled by their child rows
            return ""

        # Table row
        elif block_type == 'table_row':
            cells = block['table_row'].get('cells', [])
            row_text = " | ".join([rich_text_to_markdown(cell) for cell in cells])
            return f"| {row_text} |"

        # Child page (link to it)
        elif block_type == 'child_page':
            title = block['child_page']['title']
            child_id = block['id']
            # Store for reference
            if page_links_map is not None:
                page_links_map[child_id] = title
            return f"→ [[{title}]]"

        # Link to page
        elif block_type == 'link_to_page':
            page_id = block['link_to_page'].get('page_id', '')
            if page_id in page_links_map:
                return f"→ [[{page_links_map[page_id]}]]"
            return f"→ [Linked Page]({page_id})"

        else:
            logger.warning(f"Unsupported block type: {block_type}")
            return f"<!-- Unsupported block type: {block_type} -->"

    except Exception as e:
        logger.error(f"Error converting block: {str(e)}", exc_info=True)
        return f"<!-- Error converting block: {str(e)} -->"


def get_page_title(page: Dict[str, Any]) -> str:
    """Extract page title from page object."""
    if 'properties' in page:
        for prop_name, prop_value in page['properties'].items():
            if prop_value.get('type') == 'title' and prop_value.get('title'):
                return rich_text_to_markdown(prop_value['title'])
    return "Untitled"


def download_from_notion(
    page_id: str,
    output_file: Path,
    config: Optional[Config] = None
) -> Tuple[str, int]:
    """
    Download Notion page to markdown file.

    Args:
        page_id: Notion page ID or URL
        output_file: Path to output markdown file
        config: Configuration object

    Returns:
        Tuple of (title, block_count)

    Raises:
        urllib.error.HTTPError: On API errors
    """
    if config is None:
        config = load_config()

    # Extract page ID from URL if needed
    page_id = extract_page_id(page_id)
    logger.info(f"Downloading Notion page: {page_id}")

    # Get page metadata
    logger.info("Fetching page metadata...")
    page = get_page(config.notion_token, config.api_version, page_id, config)
    title = get_page_title(page)
    created_time = page.get('created_time', '')
    last_edited_time = page.get('last_edited_time', '')
    url = page.get('url', '')

    # Get all blocks
    logger.info("Fetching page blocks...")
    blocks = get_all_blocks(config.notion_token, config.api_version, page_id, config)
    logger.info(f"   Retrieved {len(blocks)} blocks")

    # Build page links map for internal references
    page_links_map = {}
    for block in blocks:
        if block['type'] == 'child_page':
            page_links_map[block['id']] = block['child_page']['title']

    # Convert blocks to markdown
    logger.info("Converting to markdown...")
    markdown_lines = []
    in_table = False
    table_row_count = 0

    for block in blocks:
        # Handle table structure
        if block['type'] == 'table':
            in_table = True
            table_row_count = 0
            continue
        elif in_table and block['type'] == 'table_row':
            md = block_to_markdown(block, page_links_map)
            if md:
                markdown_lines.append(md)
                # Add separator after header row
                if table_row_count == 0:
                    num_cols = len(block['table_row'].get('cells', []))
                    separator = "| " + " | ".join(["---"] * num_cols) + " |"
                    markdown_lines.append(separator)
                table_row_count += 1
        elif block['type'] != 'table_row':
            in_table = False
            md = block_to_markdown(block, page_links_map)
            if md:
                markdown_lines.append(md)

    # Build frontmatter
    frontmatter = f"""---
notion_page_id: {page_id}
notion_url: {url}
title: {title}
created: {created_time}
updated: {last_edited_time}
downloaded: {datetime.now().isoformat()}
---

"""

    # Combine frontmatter + content
    markdown_content = frontmatter + '\n\n'.join(markdown_lines)

    # Write to file
    logger.info(f"Writing to file: {output_file}")
    output_file.write_text(markdown_content)

    return title, len(blocks)


def main():
    """Main entry point for command-line usage."""
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    # Parse arguments
    page_input = None
    output_file = None
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
        elif page_input is None:
            page_input = arg
        elif output_file is None:
            output_file = Path(arg)
        else:
            print(f"Error: Unexpected argument: {arg}")
            sys.exit(1)

        i += 1

    if page_input is None or output_file is None:
        print("Error: page_id_or_url and output_file are required")
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

    # Download from Notion
    try:
        title, block_count = download_from_notion(page_input, output_file, config)

        print(f"\n✅ Download complete!")
        print(f"   Title: {title}")
        print(f"   Blocks: {block_count}")
        print(f"   Saved to: {output_file}")

        return 0

    except Exception as e:
        logger.error(f"Download failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
