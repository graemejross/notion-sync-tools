#!/usr/bin/env python3
"""
Upload markdown to Notion with full formatting and link preservation.

Usage:
    ./markdown-to-notion.py <markdown_file>                        # Auto-resolve parent from hierarchy
    ./markdown-to-notion.py <markdown_file> <parent_page_id_or_url>  # Explicit parent
    ./markdown-to-notion.py <markdown_file> --update               # Update existing page

Features:
    - Preserves bold, italic, code, strikethrough, links
    - Reads YAML frontmatter for page ID (supports updates)
    - Auto-resolves parent page from hierarchy (notion_parent_id or domain anchor)
    - Handles nested lists, code blocks, quotes
    - Preserves internal Notion links
    - Supports creating or updating pages

Options:
    --update    Update existing page (uses notion_page_id from frontmatter)
    --force     With --update: delete ALL blocks including child pages (dangerous!)

Parent Resolution (create mode, no explicit parent):
    1. File's notion_parent_id in frontmatter (project override)
    2. Domain overview's notion_page_id (domain anchor, for files under 01-domains/)

Example:
    # Create new page (auto-resolve parent from hierarchy):
    ./markdown-to-notion.py ~/claude-docs/01-domains/bagdb/20-projects/myproject/README.md

    # Create new page (explicit parent):
    ./markdown-to-notion.py schema.md 2bfc95e7d72e816486a5cfb9a97fa8c9

    # Update existing page (requires frontmatter with notion_page_id):
    ./markdown-to-notion.py schema.md --update
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
MAX_BLOCKS_PER_REQUEST = 100
MAX_TEXT_LENGTH = 2000  # Notion's limit per rich text object


def read_notion_token():
    """Read Notion API token from credentials file."""
    with open(CREDENTIALS_FILE, "r") as f:
        for line in f:
            if "NOTION_TOKEN" in line:
                return line.split("=")[1].strip().strip('"').strip("'")
    raise ValueError("NOTION_TOKEN not found in credentials file")


def extract_page_id(input_str):
    """Extract page ID from URL or use directly if it's an ID."""
    if "notion.so" in input_str:
        match = re.search(
            r"([a-f0-9]{32}|[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})",
            input_str,
        )
        if match:
            page_id = match.group(1)
            if "-" not in page_id:
                page_id = f"{page_id[:8]}-{page_id[8:12]}-{page_id[12:16]}-{page_id[16:20]}-{page_id[20:]}"
            return page_id
    return input_str


def parse_frontmatter(content):
    """Parse YAML frontmatter from markdown."""
    frontmatter = {}
    content_without_frontmatter = content

    if content.startswith("---\n"):
        parts = content.split("---\n", 2)
        if len(parts) >= 3:
            frontmatter_text = parts[1]
            content_without_frontmatter = parts[2].lstrip("\n")

            # Parse YAML frontmatter
            for line in frontmatter_text.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    frontmatter[key.strip()] = value.strip()

    return frontmatter, content_without_frontmatter


def resolve_parent_page_id(file_path):
    """Resolve Notion parent page ID from hierarchy.

    Resolution chain:
    1. File's own frontmatter notion_parent_id (project override)
    2. Domain overview's notion_page_id (domain anchor)

    Returns: (page_id, source_description) or (None, error_message)
    """
    file_path = Path(file_path).resolve()

    # Read the file's own frontmatter
    try:
        content = file_path.read_text(errors="replace")
        fm, _ = parse_frontmatter(content)
    except OSError as e:
        return None, f"Cannot read file: {e}"

    # Check for project-level override
    parent_id = fm.get("notion_parent_id")
    if parent_id:
        return parent_id.strip(), f"notion_parent_id from {file_path.name}"

    # Walk up to find domain overview
    # Expected path: .../01-domains/{domain}/20-projects/{name}/README.md
    #            or: .../01-domains/{domain}/30-services/{name}/README.md
    parts = file_path.parts
    try:
        domains_idx = parts.index("01-domains")
    except ValueError:
        return None, (
            f"File is not under 01-domains/ hierarchy.\n"
            f"  Provide parent page ID explicitly: ./markdown-to-notion.py {file_path.name} <parent_page_id>"
        )

    if domains_idx + 1 >= len(parts):
        return None, "Cannot determine domain from path"

    domain = parts[domains_idx + 1]

    # Verify file is under 20-projects/ or 30-services/
    path_str = str(file_path)
    if "/20-projects/" not in path_str and "/30-services/" not in path_str:
        return None, (
            f"File is not under 20-projects/ or 30-services/.\n"
            f"  Provide parent page ID explicitly: ./markdown-to-notion.py {file_path.name} <parent_page_id>"
        )

    # Build path to domain overview
    domains_dir = Path(*parts[: domains_idx + 1])
    overview_path = domains_dir / domain / "00-overview" / "README.md"

    if not overview_path.exists():
        return None, f"Domain overview not found: {overview_path}"

    # Read domain overview frontmatter
    try:
        overview_content = overview_path.read_text(errors="replace")
        overview_fm, _ = parse_frontmatter(overview_content)
    except OSError as e:
        return None, f"Cannot read domain overview: {e}"

    domain_page_id = overview_fm.get("notion_page_id")
    if not domain_page_id:
        return None, (
            f"Domain '{domain}' overview has no notion_page_id.\n"
            f"  Provide parent page ID explicitly: ./markdown-to-notion.py {file_path.name} <parent_page_id>"
        )

    return domain_page_id.strip(), f"domain anchor for '{domain}'"


# Module-level link resolution map: relative_path -> notion_url
_link_map = {}


def build_link_map(source_file):
    """Build a map of relative .md paths to Notion URLs by scanning sibling files' frontmatter.

    Scans the source file's directory and all subdirectories for .md files with
    notion_page_id in their frontmatter. Stores both direct filename and relative
    path variants so links like 'GLOSSARY.md' and 'reference/GLOSSARY.md' both resolve.
    """
    global _link_map
    _link_map = {}

    source_dir = Path(source_file).resolve().parent

    # Scan for .md files in source dir and subdirectories
    for md_file in source_dir.rglob("*.md"):
        try:
            content = md_file.read_text(errors="replace")
            if not content.startswith("---\n"):
                continue
            fm, _ = parse_frontmatter(content)
            page_id = fm.get("notion_page_id")
            if not page_id:
                continue

            # Build Notion URL (strip dashes for URL format)
            clean_id = page_id.replace("-", "")
            notion_url = f"https://www.notion.so/{clean_id}"

            # Store relative path from source dir
            try:
                rel_path = md_file.resolve().relative_to(source_dir)
                _link_map[str(rel_path)] = notion_url
                # Also store just the filename for bare references like [x](GLOSSARY.md)
                _link_map[md_file.name] = notion_url
            except ValueError:
                pass
        except (OSError, UnicodeDecodeError):
            continue

    if _link_map:
        print(f"   📎 Link map: {len(_link_map)} resolvable paths from {source_dir}")


def resolve_link(url, source_file=None):
    """Resolve a link URL. Converts relative .md links to Notion URLs if possible."""
    # Already a full URL — pass through
    if url.startswith(("http://", "https://", "mailto:")):
        return url

    # Strip anchor fragments for lookup, preserve for Notion URL
    base_url = url.split("#")[0]

    # Try to resolve from link map
    if base_url in _link_map:
        return _link_map[base_url]

    # If it's a relative .md link we can't resolve, return None to indicate
    # it should be rendered as plain text rather than a broken link
    if base_url.endswith(".md"):
        return None

    return url


def parse_markdown_formatting(text):
    """Parse markdown formatting into Notion rich text objects."""
    rich_text = []

    # Split by code spans first
    parts = re.split(r"(`[^`]+`)", text)

    for part in parts:
        if not part:
            continue

        # Handle code spans
        if part.startswith("`") and part.endswith("`"):
            content = part[1:-1]
            if len(content) > MAX_TEXT_LENGTH:
                content = content[:MAX_TEXT_LENGTH]
            rich_text.append(
                {
                    "type": "text",
                    "text": {"content": content},
                    "annotations": {"code": True},
                }
            )
            continue

        # Handle links, bold, italic
        # Pattern: [text](url) or **bold** or *italic* or ~~strike~~
        pos = 0
        while pos < len(part):
            # Try to match link
            link_match = re.match(r"\[([^\]]+)\]\(([^\)]+)\)", part[pos:])
            if link_match:
                link_text = link_match.group(1)
                link_url = link_match.group(2)

                # Resolve relative .md links to Notion URLs
                resolved_url = resolve_link(link_url)

                # Check for formatting within link text
                annotations = {
                    "bold": "**" in link_text,
                    "italic": "*" in link_text and "**" not in link_text,
                    "strikethrough": "~~" in link_text,
                }

                # Clean up link text
                clean_text = (
                    link_text.replace("**", "").replace("*", "").replace("~~", "")
                )

                if len(clean_text) > MAX_TEXT_LENGTH:
                    clean_text = clean_text[:MAX_TEXT_LENGTH]

                if resolved_url is None:
                    # Unresolvable .md link — render as plain text to avoid broken link
                    rich_text.append(
                        {
                            "type": "text",
                            "text": {"content": clean_text},
                            "annotations": annotations,
                        }
                    )
                else:
                    rich_text.append(
                        {
                            "type": "text",
                            "text": {
                                "content": clean_text,
                                "link": {"url": resolved_url},
                            },
                            "annotations": annotations,
                        }
                    )
                pos += len(link_match.group(0))
                continue

            # Try to match **bold**
            bold_match = re.match(r"\*\*([^\*]+)\*\*", part[pos:])
            if bold_match:
                content = bold_match.group(1)
                if len(content) > MAX_TEXT_LENGTH:
                    content = content[:MAX_TEXT_LENGTH]
                rich_text.append(
                    {
                        "type": "text",
                        "text": {"content": content},
                        "annotations": {"bold": True},
                    }
                )
                pos += len(bold_match.group(0))
                continue

            # Try to match *italic*
            italic_match = re.match(r"\*([^\*]+)\*", part[pos:])
            if italic_match:
                content = italic_match.group(1)
                if len(content) > MAX_TEXT_LENGTH:
                    content = content[:MAX_TEXT_LENGTH]
                rich_text.append(
                    {
                        "type": "text",
                        "text": {"content": content},
                        "annotations": {"italic": True},
                    }
                )
                pos += len(italic_match.group(0))
                continue

            # Try to match ~~strikethrough~~
            strike_match = re.match(r"~~([^~]+)~~", part[pos:])
            if strike_match:
                content = strike_match.group(1)
                if len(content) > MAX_TEXT_LENGTH:
                    content = content[:MAX_TEXT_LENGTH]
                rich_text.append(
                    {
                        "type": "text",
                        "text": {"content": content},
                        "annotations": {"strikethrough": True},
                    }
                )
                pos += len(strike_match.group(0))
                continue

            # Check if we're at a [ that's not a link - treat as regular text
            if part[pos] == "[":
                # Look for closing ] and check if followed by (
                bracket_match = re.match(r"\[([^\]]+)\]", part[pos:])
                if bracket_match:
                    # Check if this is followed by ( - if so, it's a broken link, skip
                    end_pos = pos + len(bracket_match.group(0))
                    if end_pos < len(part) and part[end_pos] == "(":
                        # Broken link syntax, skip the [
                        pos += 1
                        continue
                    # Not followed by ( - include brackets as plain text
                    content = bracket_match.group(0)  # Include the brackets
                    if len(content) > MAX_TEXT_LENGTH:
                        content = content[:MAX_TEXT_LENGTH]
                    rich_text.append({"type": "text", "text": {"content": content}})
                    pos += len(bracket_match.group(0))
                    continue

            # Regular text until next special character
            next_special = len(part)
            for pattern in [r"\[", r"\*\*", r"\*", r"~~"]:
                match = re.search(pattern, part[pos:])
                if match and match.start() < next_special - pos:
                    next_special = pos + match.start()

            if next_special > pos:
                content = part[pos:next_special]
                if len(content) > MAX_TEXT_LENGTH:
                    content = content[:MAX_TEXT_LENGTH]
                rich_text.append({"type": "text", "text": {"content": content}})
                pos = next_special
            else:
                pos += 1

    return rich_text if rich_text else [{"type": "text", "text": {"content": ""}}]


def markdown_to_notion_blocks(md_content):
    """Convert markdown to Notion block objects."""
    blocks = []
    lines = md_content.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].rstrip()

        # Skip empty lines
        if not line:
            i += 1
            continue

        # Heading 1
        if line.startswith("# "):
            blocks.append(
                {
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {"rich_text": parse_markdown_formatting(line[2:])},
                }
            )
        # Heading 2
        elif line.startswith("## "):
            blocks.append(
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {"rich_text": parse_markdown_formatting(line[3:])},
                }
            )
        # Heading 3
        elif line.startswith("### "):
            blocks.append(
                {
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {"rich_text": parse_markdown_formatting(line[4:])},
                }
            )
        # Code block
        elif line.startswith("```"):
            language_match = re.match(r"```([a-z0-9 +#]+)?", line, re.IGNORECASE)
            language = (
                (language_match.group(1).strip() or "plain text")
                if language_match and language_match.group(1)
                else "plain text"
            )

            code_content = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_content.append(lines[i].rstrip())
                i += 1

            code_text = "\n".join(code_content)
            if len(code_text) > MAX_TEXT_LENGTH:
                code_text = code_text[:MAX_TEXT_LENGTH]

            blocks.append(
                {
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [{"type": "text", "text": {"content": code_text}}],
                        "language": language,
                    },
                }
            )
        # Table (detect by pipe characters)
        elif "|" in line and i + 1 < len(lines) and "|" in lines[i + 1]:
            # Collect table rows
            table_lines = []
            while i < len(lines) and "|" in lines[i]:
                table_lines.append(lines[i].strip())
                i += 1
            i -= 1  # Back up one since we'll increment at the end

            # Skip if it's a separator row only (|---|---|)
            if table_lines and not all(
                "-" in line or line == "|" for line in table_lines
            ):
                # Parse table
                rows = []
                for table_line in table_lines:
                    # Skip separator rows
                    if table_line.startswith("|---") or table_line.startswith("|-"):
                        continue
                    # Parse cells
                    cells = [cell.strip() for cell in table_line.split("|")]
                    cells = [c for c in cells if c]  # Remove empty strings
                    if cells:
                        rows.append(cells)

                # Create proper Notion table
                if rows and len(rows) > 0:
                    # Determine number of columns
                    num_cols = len(rows[0])

                    # Create table block with children (table rows)
                    table_children = []
                    for row in rows:
                        # Pad row if needed to match column count
                        while len(row) < num_cols:
                            row.append("")

                        # Create table_row with cells
                        cells = []
                        for cell_text in row[:num_cols]:  # Limit to num_cols
                            cells.append(parse_markdown_formatting(cell_text))

                        table_children.append(
                            {"type": "table_row", "table_row": {"cells": cells}}
                        )

                    # Notion has a 100-row limit per table
                    # Split large tables into multiple tables
                    MAX_TABLE_ROWS = 100

                    if len(table_children) <= MAX_TABLE_ROWS:
                        # Single table fits within limit
                        blocks.append(
                            {
                                "object": "block",
                                "type": "table",
                                "table": {
                                    "table_width": num_cols,
                                    "has_column_header": True,
                                    "has_row_header": False,
                                    "children": table_children,
                                },
                            }
                        )
                    else:
                        # Split into multiple tables
                        header_row = table_children[0] if table_children else None
                        data_rows = (
                            table_children[1:] if len(table_children) > 1 else []
                        )

                        # Create tables in chunks of MAX_TABLE_ROWS-1 (to include header)
                        chunk_size = MAX_TABLE_ROWS - 1
                        for chunk_idx in range(0, len(data_rows), chunk_size):
                            chunk = data_rows[chunk_idx : chunk_idx + chunk_size]

                            # Include header in each chunk
                            chunk_with_header = (
                                [header_row] + chunk if header_row else chunk
                            )

                            blocks.append(
                                {
                                    "object": "block",
                                    "type": "table",
                                    "table": {
                                        "table_width": num_cols,
                                        "has_column_header": True,
                                        "has_row_header": False,
                                        "children": chunk_with_header,
                                    },
                                }
                            )

                            # Add a note between split tables
                            if chunk_idx + chunk_size < len(data_rows):
                                blocks.append(
                                    {
                                        "object": "block",
                                        "type": "paragraph",
                                        "paragraph": {
                                            "rich_text": [
                                                {
                                                    "type": "text",
                                                    "text": {
                                                        "content": f"(Table continued - part {chunk_idx // chunk_size + 2})"
                                                    },
                                                }
                                            ]
                                        },
                                    }
                                )
        # Divider
        elif line.strip() == "---":
            blocks.append({"object": "block", "type": "divider", "divider": {}})
        # Quote
        elif line.startswith("> "):
            blocks.append(
                {
                    "object": "block",
                    "type": "quote",
                    "quote": {"rich_text": parse_markdown_formatting(line[2:])},
                }
            )
        # Bulleted list
        elif line.startswith("- ") and not line.startswith("- ["):
            blocks.append(
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": parse_markdown_formatting(line[2:])
                    },
                }
            )
        # To-do list
        elif line.startswith("- ["):
            checked = "x" in line[0:5].lower()
            content = re.sub(r"^- \[[x ]\] ", "", line, flags=re.IGNORECASE)
            blocks.append(
                {
                    "object": "block",
                    "type": "to_do",
                    "to_do": {
                        "rich_text": parse_markdown_formatting(content),
                        "checked": checked,
                    },
                }
            )
        # Numbered list
        elif re.match(r"^\d+\. ", line):
            content = re.sub(r"^\d+\. ", "", line)
            blocks.append(
                {
                    "object": "block",
                    "type": "numbered_list_item",
                    "numbered_list_item": {
                        "rich_text": parse_markdown_formatting(content)
                    },
                }
            )
        # Paragraph (default)
        else:
            blocks.append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": parse_markdown_formatting(line)},
                }
            )

        i += 1

    return blocks


def create_notion_page(token, title, parent_id):
    """Create a new Notion page."""
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_API_VERSION,
    }

    payload = {
        "parent": {"page_id": parent_id},
        "properties": {
            "title": {
                "type": "title",
                "title": [{"type": "text", "text": {"content": title}}],
            }
        },
    }

    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )

    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read())
        return result["id"], result["url"]


def delete_all_blocks(token, page_id, preserve_children=True):
    """Delete child blocks from a page, optionally preserving child pages and databases.

    Args:
        token: Notion API token
        page_id: Page ID to delete blocks from
        preserve_children: If True, preserves child_page, child_database, and synced_block blocks

    Returns:
        Tuple of (deleted_count, preserved_count)
    """
    # Block types that should be preserved (nested pages/databases)
    PROTECTED_BLOCK_TYPES = {"child_page", "child_database", "synced_block"}

    headers = {"Authorization": f"Bearer {token}", "Notion-Version": NOTION_API_VERSION}

    # Get all existing blocks
    all_blocks = []
    start_cursor = None

    while True:
        url = f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=100"
        if start_cursor:
            url += f"&start_cursor={start_cursor}"

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read())

        all_blocks.extend(result.get("results", []))

        if result.get("has_more"):
            start_cursor = result.get("next_cursor")
        else:
            break

    # Delete each block (respecting protected types)
    deleted = 0
    preserved = 0
    for block in all_blocks:
        block_type = block.get("type", "")
        block_id = block["id"]

        # Skip protected block types if preserve_children is True
        if preserve_children and block_type in PROTECTED_BLOCK_TYPES:
            # Get the title of the child page/database for logging
            if block_type == "child_page":
                title = block.get("child_page", {}).get("title", "Untitled")
            elif block_type == "child_database":
                title = block.get("child_database", {}).get("title", "Untitled")
            else:
                title = block_type
            print(f"   ⏭️  Preserving {block_type}: {title}")
            preserved += 1
            continue

        url = f"https://api.notion.com/v1/blocks/{block_id}"

        req = urllib.request.Request(url, headers=headers, method="DELETE")
        try:
            with urllib.request.urlopen(req) as response:
                deleted += 1
        except urllib.error.HTTPError as e:
            # Ignore errors for blocks that can't be deleted
            pass

    return deleted, preserved


def upload_blocks_to_page(token, page_id, blocks):
    """Upload blocks to a Notion page in batches."""
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_API_VERSION,
    }

    total_uploaded = 0
    for i in range(0, len(blocks), MAX_BLOCKS_PER_REQUEST):
        batch = blocks[i : i + MAX_BLOCKS_PER_REQUEST]
        payload = json.dumps({"children": batch}).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers=headers, method="PATCH")

        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read())
            uploaded = len(result.get("results", []))
            total_uploaded += uploaded
            print(
                f"  Batch {i // MAX_BLOCKS_PER_REQUEST + 1}: {uploaded} blocks uploaded"
            )

    return total_uploaded


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: ./markdown-to-notion.py <markdown_file> [parent_page_id_or_url] [--update]"
        )
        print("\nExamples:")
        print("  # Create new page (auto-resolve parent from hierarchy):")
        print(
            "  ./markdown-to-notion.py ~/claude-docs/01-domains/bagdb/20-projects/myproject/README.md"
        )
        print("\n  # Create new page (explicit parent):")
        print("  ./markdown-to-notion.py schema.md 2bfc95e7d72e816486a5cfb9a97fa8c9")
        print("\n  # Update existing page (requires frontmatter):")
        print("  ./markdown-to-notion.py schema.md --update")
        sys.exit(1)

    md_file = Path(sys.argv[1])
    update_mode = "--update" in sys.argv
    force_mode = "--force" in sys.argv

    if not md_file.exists():
        print(f"Error: File not found: {md_file}")
        sys.exit(1)

    # Read markdown file
    print(f"📄 Reading markdown file: {md_file}")
    md_content = md_file.read_text()

    # Parse frontmatter
    frontmatter, content = parse_frontmatter(md_content)

    # Generate title - include parent folder for common filenames
    if "title" in frontmatter:
        title = frontmatter["title"]
    else:
        # Common filenames that need parent folder prefix for uniqueness
        common_names = ["README", "readme", "INDEX", "index", "todos", "TODOS"]
        if md_file.stem in common_names:
            # Include parent directory name: "parent-folder/README"
            parent_name = md_file.parent.name
            title = f"{parent_name}/{md_file.stem}"
        else:
            title = md_file.stem

    # Determine mode
    if update_mode:
        page_id = frontmatter.get("notion_page_id")
        if not page_id:
            print("Error: --update requires 'notion_page_id' in frontmatter")
            sys.exit(1)
        print(f"🔄 Update mode: Updating page {page_id}")
        print(f"   Title: {title}")
    else:
        # Determine parent: explicit arg > auto-resolve from hierarchy
        explicit_args = [a for a in sys.argv[2:] if not a.startswith("--")]
        if explicit_args:
            parent_id = extract_page_id(explicit_args[0])
            print(f"✨ Create mode: New page under {parent_id}")
        else:
            parent_id, source = resolve_parent_page_id(md_file)
            if parent_id is None:
                print(f"Error: Cannot auto-resolve parent page.\n  {source}")
                sys.exit(1)
            parent_id = extract_page_id(parent_id)
            print(f"✨ Create mode: New page under {parent_id}")
            print(f"   (resolved from {source})")
        print(f"   Title: {title}")

    # Read token
    token = read_notion_token()

    # Build link resolution map from sibling files' frontmatter
    build_link_map(md_file)

    # Convert markdown to Notion blocks
    print("\n🔄 Converting markdown to Notion blocks...")
    blocks = markdown_to_notion_blocks(content)
    print(f"   Generated {len(blocks)} blocks")

    # Create or update page
    if update_mode:
        preserve_children = not force_mode
        if force_mode:
            print(f"\n⚠️  Force mode: will delete ALL blocks including child pages!")
        print(f"\n🗑️  Deleting existing blocks...")
        deleted, preserved = delete_all_blocks(
            token, page_id, preserve_children=preserve_children
        )
        print(f"   Deleted {deleted} blocks")
        if preserved > 0:
            print(f"   Preserved {preserved} child pages/databases")

        print(f"\n📤 Uploading new blocks...")
        total_uploaded = upload_blocks_to_page(token, page_id, blocks)
        page_url = frontmatter.get("notion_url", f"https://notion.so/{page_id}")
    else:
        print(f"\n✨ Creating new Notion page...")
        page_id, page_url = create_notion_page(token, title, parent_id)
        print(f"   Page created: {page_id}")

        print(f"\n📤 Uploading {len(blocks)} blocks...")
        total_uploaded = upload_blocks_to_page(token, page_id, blocks)

        # Update markdown file with notion_page_id to prevent duplicate uploads
        if not update_mode:
            frontmatter["notion_page_id"] = page_id
            frontmatter["notion_url"] = page_url
            frontmatter["title"] = title
            frontmatter["uploaded"] = datetime.now().isoformat()

            # Write updated frontmatter back to file
            updated_content = "---\n"
            for key, value in frontmatter.items():
                updated_content += f"{key}: {value}\n"
            updated_content += "---\n\n" + content

            md_file.write_text(updated_content)
            print(f"   ✏️  Updated {md_file.name} with notion_page_id")

    # Success
    print(f"\n✅ Upload complete!")
    print(f"   Total blocks: {total_uploaded}")
    print(f"   Notion page: {page_url}")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"\n❌ HTTP Error {e.code}: {error_body}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)
