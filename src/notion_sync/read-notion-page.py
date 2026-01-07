#!/usr/bin/env python3
"""
Read and display complete content from any Notion page
Handles pagination to read pages of unlimited size
"""

import urllib.request
import json
import os
import sys
import re

# Read credentials
creds = {}
with open(os.path.expanduser('~/.notion-credentials'), 'r') as f:
    for line in f:
        if '=' in line:
            key, value = line.strip().split('=', 1)
            creds[key] = value

TOKEN = creds['NOTION_TOKEN']
NOTION_VERSION = "2022-06-28"


def extract_page_id(input_str):
    """Extract page ID from URL or use directly if it's an ID"""
    # If it's a URL, extract the ID
    if 'notion.so' in input_str:
        # Format: https://www.notion.so/Page-Name-{ID}
        match = re.search(r'([a-f0-9]{32}|[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', input_str)
        if match:
            page_id = match.group(1)
            # Add hyphens if not present
            if '-' not in page_id:
                page_id = f"{page_id[:8]}-{page_id[8:12]}-{page_id[12:16]}-{page_id[16:20]}-{page_id[20:]}"
            return page_id
    # Otherwise assume it's already an ID
    return input_str


def get_all_blocks(page_id):
    """Get all blocks from a page, handling pagination"""
    all_blocks = []
    start_cursor = None

    while True:
        url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        if start_cursor:
            url += f"?start_cursor={start_cursor}"

        headers = {
            "Authorization": f"Bearer {TOKEN}",
            "Notion-Version": NOTION_VERSION
        }

        req = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read())

            blocks = result.get('results', [])
            all_blocks.extend(blocks)

            # Check if there are more blocks
            if result.get('has_more'):
                start_cursor = result.get('next_cursor')
            else:
                break

        except urllib.error.HTTPError as e:
            print(f"Error reading page: {e}")
            return []

    return all_blocks


def get_page_title(page_id):
    """Get the title of a page"""
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Notion-Version": NOTION_VERSION
    }

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req) as response:
            page = json.loads(response.read())

        # Try to get title from different locations
        if 'properties' in page:
            for prop_name, prop_value in page['properties'].items():
                if prop_value.get('type') == 'title' and prop_value.get('title'):
                    return prop_value['title'][0]['text']['content']

        # Fallback to URL or ID
        return page.get('url', page_id).split('/')[-1]

    except Exception as e:
        return "Unknown Page"


def block_to_text(block):
    """Convert a Notion block to readable text"""
    block_type = block['type']

    try:
        # Paragraph
        if block_type == 'paragraph':
            texts = block['paragraph'].get('rich_text', [])
            return ''.join([t['text']['content'] for t in texts])

        # Headings
        elif block_type == 'heading_1':
            texts = block['heading_1'].get('rich_text', [])
            text = ''.join([t['text']['content'] for t in texts])
            return f"# {text}"

        elif block_type == 'heading_2':
            texts = block['heading_2'].get('rich_text', [])
            text = ''.join([t['text']['content'] for t in texts])
            return f"## {text}"

        elif block_type == 'heading_3':
            texts = block['heading_3'].get('rich_text', [])
            text = ''.join([t['text']['content'] for t in texts])
            return f"### {text}"

        # Lists
        elif block_type == 'bulleted_list_item':
            texts = block['bulleted_list_item'].get('rich_text', [])
            text = ''.join([t['text']['content'] for t in texts])
            return f"• {text}"

        elif block_type == 'numbered_list_item':
            texts = block['numbered_list_item'].get('rich_text', [])
            text = ''.join([t['text']['content'] for t in texts])
            return f"  {text}"

        elif block_type == 'to_do':
            texts = block['to_do'].get('rich_text', [])
            text = ''.join([t['text']['content'] for t in texts])
            checked = '✓' if block['to_do'].get('checked') else ' '
            return f"[{checked}] {text}"

        # Code
        elif block_type == 'code':
            texts = block['code'].get('rich_text', [])
            code = ''.join([t['text']['content'] for t in texts])
            language = block['code'].get('language', 'plain')
            return f"```{language}\n{code}\n```"

        # Quote
        elif block_type == 'quote':
            texts = block['quote'].get('rich_text', [])
            text = ''.join([t['text']['content'] for t in texts])
            return f"> {text}"

        # Divider
        elif block_type == 'divider':
            return "---"

        # Child page
        elif block_type == 'child_page':
            return f"📄 {block['child_page']['title']}"

        else:
            return f"[{block_type}]"

    except Exception as e:
        return f"[Error reading {block_type}]"


def read_page(page_id, output_format='text'):
    """Read and display a complete Notion page"""
    # Get page title
    title = get_page_title(page_id)

    print("=" * 70)
    print(f"📄 {title}")
    print(f"🆔 {page_id}")
    print("=" * 70)
    print()

    # Get all blocks
    blocks = get_all_blocks(page_id)

    if not blocks:
        print("⚠️  No content found or unable to read page")
        return

    print(f"📦 Total blocks: {len(blocks)}")
    print()
    print("─" * 70)
    print()

    # Convert and display blocks
    for i, block in enumerate(blocks, 1):
        text = block_to_text(block)
        if text and text.strip():
            print(text)

    print()
    print("─" * 70)
    print(f"✅ Read {len(blocks)} blocks successfully")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 read-notion-page.py <page_id_or_url>")
        print()
        print("Examples:")
        print("  python3 read-notion-page.py 2bdc95e7-d72e-813a-bc9b-e0e9f2772746")
        print("  python3 read-notion-page.py https://www.notion.so/Home-Network-2bdc95e7d72e813abc9be0e9f2772746")
        sys.exit(1)

    page_input = sys.argv[1]
    page_id = extract_page_id(page_input)

    read_page(page_id)
