#!/usr/bin/env python3
"""
Download Notion pages to markdown with full formatting and link preservation.

Usage:
    ./notion-to-markdown.py <page_id_or_url> <output_file>

Features:
    - Preserves bold, italic, code, strikethrough, links
    - Saves page ID and metadata as YAML frontmatter
    - Handles nested pages and databases
    - Preserves Notion internal links

Example:
    ./notion-to-markdown.py https://www.notion.so/Database-Schema-123abc schema.md
    ./notion-to-markdown.py 2bfc95e7d72e816486a5cfb9a97fa8c9 schema.md
"""

import urllib.request
import urllib.parse
import json
import sys
import re
from pathlib import Path
from datetime import datetime

# Configuration
CREDENTIALS_FILE = Path.home() / ".notion-credentials"
NOTION_API_VERSION = "2022-06-28"


def read_notion_token():
    """Read Notion API token from credentials file."""
    with open(CREDENTIALS_FILE, 'r') as f:
        for line in f:
            if 'NOTION_TOKEN' in line:
                return line.split('=')[1].strip().strip('"').strip("'")
    raise ValueError("NOTION_TOKEN not found in credentials file")


def extract_page_id(input_str):
    """Extract page ID from URL or use directly if it's an ID."""
    if 'notion.so' in input_str:
        match = re.search(r'([a-f0-9]{32}|[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', input_str)
        if match:
            page_id = match.group(1)
            # Add hyphens if not present
            if '-' not in page_id:
                page_id = f"{page_id[:8]}-{page_id[8:12]}-{page_id[12:16]}-{page_id[16:20]}-{page_id[20:]}"
            return page_id
    # Already a page ID
    return input_str


def get_page(token, page_id):
    """Get page metadata."""
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_API_VERSION
    }

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read())


def get_all_blocks(token, page_id):
    """Get all blocks from a page, handling pagination."""
    all_blocks = []
    start_cursor = None

    while True:
        url = f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=100"
        if start_cursor:
            url += f"&start_cursor={start_cursor}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_API_VERSION
        }

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read())

        all_blocks.extend(result.get('results', []))

        if result.get('has_more'):
            start_cursor = result.get('next_cursor')
        else:
            break

    return all_blocks


def rich_text_to_markdown(rich_text_array):
    """Convert Notion rich text array to markdown with formatting and links."""
    if not rich_text_array:
        return ""

    result = []
    for text_obj in rich_text_array:
        content = text_obj['text']['content']
        annotations = text_obj.get('annotations', {})
        link = text_obj['text'].get('link')

        # Apply formatting
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


def block_to_markdown(block, page_links_map=None):
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
            return f"<!-- Unsupported block type: {block_type} -->"

    except Exception as e:
        return f"<!-- Error converting block: {str(e)} -->"


def get_page_title(page):
    """Extract page title from page object."""
    if 'properties' in page:
        for prop_name, prop_value in page['properties'].items():
            if prop_value.get('type') == 'title' and prop_value.get('title'):
                return rich_text_to_markdown(prop_value['title'])
    return "Untitled"


def export_page_to_markdown(token, page_id):
    """Export a Notion page to markdown with frontmatter."""
    # Get page metadata
    page = get_page(token, page_id)
    title = get_page_title(page)
    created_time = page.get('created_time', '')
    last_edited_time = page.get('last_edited_time', '')
    url = page.get('url', '')

    # Get all blocks
    blocks = get_all_blocks(token, page_id)

    # Build page links map for internal references
    page_links_map = {}
    for block in blocks:
        if block['type'] == 'child_page':
            page_links_map[block['id']] = block['child_page']['title']

    # Convert blocks to markdown
    markdown_lines = []
    for block in blocks:
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

    return markdown_content, title, len(blocks)


def main():
    if len(sys.argv) != 3:
        print("Usage: ./notion-to-markdown.py <page_id_or_url> <output_file>")
        print("\nExample:")
        print("  ./notion-to-markdown.py 2bfc95e7d72e816486a5cfb9a97fa8c9 schema.md")
        print("  ./notion-to-markdown.py https://www.notion.so/Database-123abc schema.md")
        sys.exit(1)

    page_input = sys.argv[1]
    output_file = Path(sys.argv[2])

    # Extract page ID
    page_id = extract_page_id(page_input)
    print(f"📄 Downloading Notion page: {page_id}")

    # Read token
    token = read_notion_token()

    # Export to markdown
    print("🔄 Converting to markdown...")
    markdown_content, title, block_count = export_page_to_markdown(token, page_id)

    # Write to file
    output_file.write_text(markdown_content)

    # Success
    print(f"✅ Download complete!")
    print(f"   Title: {title}")
    print(f"   Blocks: {block_count}")
    print(f"   Saved to: {output_file}")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
