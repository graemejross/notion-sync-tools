# Notion Sync Tools

Bidirectional markdown ↔ Notion sync tools with full formatting preservation.

## Quick Reference

| Script | Purpose |
|--------|---------|
| `markdown-to-notion.py` | Upload markdown to Notion (create or update) |
| `notion-to-markdown.py` | Download Notion page to markdown |
| `read-notion-page.py` | Read page content to stdout |
| `bulk-upload-to-notion.sh` | Batch upload all markdown files |

## Installation

```bash
# Clone the repository
git clone https://github.com/graemejross/notion-sync-tools.git

# Copy scripts to home directory (recommended)
cp notion-sync-tools/src/notion_sync/*.py ~/

# Or install as package
cd notion-sync-tools && pip install -e .
```

## Configuration

Create `~/.notion-credentials`:

```bash
NOTION_TOKEN="secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

Get your token from: https://www.notion.so/my-integrations

```bash
chmod 600 ~/.notion-credentials
```

## Scripts

### markdown-to-notion.py

Upload markdown files to Notion with full formatting preservation.

**Create new page:**
```bash
~/markdown-to-notion.py <file.md> <parent_page_id>
```

**Update existing page:**
```bash
~/markdown-to-notion.py <file.md> --update
```

**Update with force (deletes child pages too):**
```bash
~/markdown-to-notion.py <file.md> --update --force
```

**Features:**
- Full markdown support (bold, italic, code, links, tables)
- YAML frontmatter tracking (prevents duplicate uploads)
- Auto-splits large tables (>100 rows)
- **Preserves child pages** on update (unless --force)

**Example:**
```bash
# Create new page under parent
~/markdown-to-notion.py ~/projects/my-project.md 2bfc95e7d72e816486a5cfb9a97fa8c9

# Update existing (uses notion_page_id from frontmatter)
~/markdown-to-notion.py ~/projects/my-project.md --update
```

### notion-to-markdown.py

Download Notion pages to markdown with formatting preserved.

```bash
~/notion-to-markdown.py <page_id_or_url> <output_file.md>
```

**Example:**
```bash
~/notion-to-markdown.py 2bfc95e7d72e816486a5cfb9a97fa8c9 ~/downloads/page.md
~/notion-to-markdown.py "https://www.notion.so/My-Page-abc123" output.md
```

### read-notion-page.py

Read Notion page content to stdout (useful for piping/scripting).

```bash
~/read-notion-page.py <page_id>
```

**Example:**
```bash
~/read-notion-page.py 2bfc95e7d72e816486a5cfb9a97fa8c9
~/read-notion-page.py 2bfc95e7d72e816486a5cfb9a97fa8c9 | grep "keyword"
```

### bulk-upload-to-notion.sh

Batch upload all markdown files from a directory.

```bash
~/bulk-upload-to-notion.sh <parent_page_id> [directory]
```

**Features:**
- Recursive file discovery
- Skips files already uploaded (checks frontmatter)
- Progress logging

**Example:**
```bash
~/bulk-upload-to-notion.sh 2bfc95e7d72e816486a5cfb9a97fa8c9 ~/projects/
```

## YAML Frontmatter

When you upload a file, frontmatter is added automatically:

```yaml
---
notion_page_id: 2bfc95e7-d72e-8164-86a5-cfb9a97fa8c9
notion_url: https://www.notion.so/My-Page-2bfc95e7d72e816486a5cfb9a97fa8c9
title: My Page
uploaded: 2025-12-14T10:30:00
---

# Your content here
```

This enables:
- **Update mode**: `--update` uses the page ID from frontmatter
- **Duplicate prevention**: Bulk upload skips files with existing page IDs

## Page IDs

Page IDs can be found in Notion URLs:
```
https://www.notion.so/My-Page-2bfc95e7d72e816486a5cfb9a97fa8c9
                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                              This is the page ID (32 hex chars)
```

Both formats work:
- With dashes: `2bfc95e7-d72e-8164-86a5-cfb9a97fa8c9`
- Without dashes: `2bfc95e7d72e816486a5cfb9a97fa8c9`

## Formatting Support

| Markdown | Notion |
|----------|--------|
| `**bold**` | Bold text |
| `*italic*` | Italic text |
| `` `code` `` | Inline code |
| `~~strike~~` | Strikethrough |
| `[link](url)` | Hyperlink |
| `# Heading` | Heading 1/2/3 |
| `- item` | Bulleted list |
| `1. item` | Numbered list |
| `- [ ] task` | To-do item |
| `> quote` | Quote block |
| ` ``` ` | Code block |
| `\|table\|` | Table (auto-splits if >100 rows) |

## Child Page Handling

When updating a page (`--update`), the script preserves:
- **child_page** blocks (nested pages)
- **child_database** blocks (inline databases)
- **synced_block** blocks

To delete everything including child pages, use `--force`:
```bash
~/markdown-to-notion.py file.md --update --force
```

## Common Issues

**"NOTION_TOKEN not found"**
- Create `~/.notion-credentials` with your token
- Ensure the file has correct format: `NOTION_TOKEN="secret_xxx"`

**"Page not found" or 403 error**
- Share the page with your integration in Notion
- Click "..." menu → "Add connections" → Select your integration

**Large tables truncated**
- Tables >100 rows are automatically split into multiple tables
- This is a Notion API limitation

## Integration with Claude Code

These scripts are the preferred way to interact with Notion in Claude Code sessions:

1. **Use scripts, not MCP tools** - Scripts save context and ensure consistency
2. **Check CLAUDE.md** for key page IDs
3. **End-of-session sync** uses these scripts to update documentation

See: https://github.com/graemejross/claude-process for workflow rules.

## License

MIT License - see LICENSE file for details.

## Support

- **Issues:** https://github.com/graemejross/notion-sync-tools/issues
- **Repository:** https://github.com/graemejross/notion-sync-tools
