# Usage Guide

## Quick Reference

```bash
# Upload markdown to Notion (create new page)
markdown-to-notion README.md <parent_page_id>

# Update existing page
markdown-to-notion README.md --update

# Download from Notion
notion-to-markdown <page_id> output.md

# Bulk upload directory
bulk-upload-notion <parent_page_id> /path/to/docs
```

## Upload Markdown to Notion

### Create New Page

```bash
# Using page ID
markdown-to-notion schema.md 2bfc95e7d72e816486a5cfb9a97fa8c9

# Using Notion URL (page ID extracted automatically)
markdown-to-notion schema.md https://www.notion.so/My-Page-2bfc95e7d72e816486a5cfb9a97fa8c9
```

**What happens:**
1. Reads markdown file
2. Converts to Notion blocks
3. Creates new page under parent
4. Uploads all blocks
5. Adds `notion_page_id` to frontmatter (prevents duplicates)

### Update Existing Page

```bash
markdown-to-notion schema.md --update
```

**Requirements:**
- File must have YAML frontmatter with `notion_page_id`
- Page must exist and be accessible to your integration

**What happens:**
1. Reads `notion_page_id` from frontmatter
2. Deletes all existing blocks on page
3. Uploads new blocks from markdown

### With Custom Config

```bash
markdown-to-notion schema.md <parent_id> --config /path/to/config.yaml
```

## Download from Notion

### Basic Usage

```bash
# Using page ID
notion-to-markdown 2bfc95e7d72e816486a5cfb9a97fa8c9 schema.md

# Using Notion URL
notion-to-markdown https://www.notion.so/Database-Schema-123abc schema.md
```

**What happens:**
1. Fetches page metadata and blocks from Notion
2. Converts blocks to markdown
3. Adds YAML frontmatter with page info
4. Saves to file

**Frontmatter added:**
```yaml
---
notion_page_id: 2bfc95e7d72e816486a5cfb9a97fa8c9
notion_url: https://www.notion.so/...
title: Page Title
created: 2025-01-15T10:30:00.000Z
updated: 2025-01-20T14:22:00.000Z
downloaded: 2025-01-20T15:00:00.123456
---
```

## Bulk Upload

### Upload Entire Directory

```bash
bulk-upload-notion <parent_page_id> /path/to/docs
```

**Features:**
- Recursively finds all `.md` files
- Skips files already uploaded (checks for `notion_page_id`)
- Skips configured exclusions (`.git`, `node_modules`, etc.)
- Progress logging for each file
- Summary report at end

**Example:**

```bash
# Upload all docs to Notion
bulk-upload-notion 2c6c95e7d72e80e39714fdb498641b84 ~/projects/docs

# Output:
# Found 42 markdown files
#
# [1/42] README.md
#   📤 Uploading...
#   ✅ SUCCESS: 45 blocks uploaded
#
# [2/42] installation.md
#   ⏭️  SKIPPED: Already has notion_page_id
#
# [3/42] api-reference.md
#   📤 Uploading...
#   ✅ SUCCESS: 120 blocks uploaded
#
# ========================================
# Summary
# ========================================
# Uploaded:  35
# Skipped:   7
# Failed:    0
# ========================================
```

### Customize Exclusions

Edit `config.yaml`:

```yaml
bulk_upload:
  exclude_patterns:
    - ".git"
    - "node_modules"
    - "__pycache__"
    - "build"
    - "dist"
    - ".DS_Store"
    - "temp"
    - "scratch"
```

## Advanced Usage

### Bidirectional Sync Workflow

```bash
# 1. Download from Notion for local editing
notion-to-markdown <page_id> document.md

# 2. Edit locally
vim document.md

# 3. Upload changes back to Notion
markdown-to-notion document.md --update
```

### Batch Processing

```bash
# Upload multiple specific files
for file in docs/*.md; do
  markdown-to-notion "$file" <parent_id>
done

# Or use bulk upload for entire directory
bulk-upload-notion <parent_id> docs/
```

### CI/CD Integration

```bash
#!/bin/bash
# sync-to-notion.sh

set -e

# Check for changes in docs/
if git diff --name-only HEAD^ HEAD | grep '^docs/'; then
  echo "Documentation changed, syncing to Notion..."

  # Update existing pages
  for file in docs/*.md; do
    if grep -q 'notion_page_id:' "$file"; then
      echo "Updating $file..."
      markdown-to-notion "$file" --update
    fi
  done

  echo "Sync complete!"
fi
```

## Working with Frontmatter

### Frontmatter Structure

After uploading, files have frontmatter added:

```yaml
---
notion_page_id: 2bfc95e7d72e816486a5cfb9a97fa8c9
notion_url: https://www.notion.so/My-Page-2bfc95e7d72e816486a5cfb9a97fa8c9
title: My Page
uploaded: 2025-01-20T10:30:00.123456
---

# Your content starts here
```

### Custom Titles

By default, the filename is used as the page title:
- `README.md` → "parent-folder/README" (includes parent folder)
- `schema.md` → "schema"

Override by adding frontmatter manually:

```yaml
---
title: Custom Page Title
---

# Content
```

### Preventing Duplicates

The `notion_page_id` field prevents duplicate uploads:
- `bulk-upload-notion` skips files with this field
- You can still force update with `--update` flag

To re-upload as a NEW page:
1. Remove `notion_page_id` from frontmatter
2. Run upload command again

## Formatting Support

### Supported Features

✅ **Text Formatting:**
- **Bold** (`**text**`)
- *Italic* (`*text*`)
- `Inline code` (`` `code` ``)
- ~~Strikethrough~~ (`~~text~~`)
- [Links](url) (`[text](url)`)

✅ **Blocks:**
- Headings (H1, H2, H3)
- Paragraphs
- Code blocks with language syntax
- Bulleted lists
- Numbered lists
- To-do lists (checkboxes)
- Quotes
- Tables
- Dividers

✅ **Special Features:**
- Large tables (auto-splits > 100 rows)
- Mixed formatting (bold + links, etc.)
- Code block language detection

### Limitations

⚠️ **Not Fully Supported:**
- Nested lists (Notion API limitation)
- Images (not implemented yet)
- Embeds (YouTube, etc.)
- Callouts with custom colors
- Databases (tables only)

## Troubleshooting

### File Already Has notion_page_id

If `bulk-upload-notion` skips a file but you want to update it:

```bash
# Use --update flag for individual file
markdown-to-notion document.md --update
```

### Upload Failed

Check:
1. **Notion token valid?** Test with single file first
2. **Page accessible?** Integration needs permission
3. **Network issues?** Check internet connection
4. **Rate limited?** Tool automatically retries

### Formatting Not Preserved

- Check markdown syntax is correct
- Some Notion features not available via API
- See [Formatting Support](#formatting-support) section

### Large Files Slow

For files with 500+ blocks:
- Upload happens in batches of 100 blocks
- Rate limiting adds small delays
- Normal behavior, wait for completion

## Best Practices

### 1. Organize with Frontmatter

Add metadata to your markdown:

```yaml
---
title: API Documentation
tags: [api, reference, v2]
author: John Doe
---
```

### 2. Use Consistent Structure

```
docs/
├── README.md
├── getting-started/
│   ├── installation.md
│   └── quickstart.md
└── reference/
    ├── api.md
    └── cli.md
```

### 3. Test Before Bulk Upload

```bash
# Test single file first
markdown-to-notion docs/test.md <parent_id>

# If successful, bulk upload
bulk-upload-notion <parent_id> docs/
```

### 4. Version Control Integration

Add to `.gitignore`:
```
config.yaml
.notion-credentials
*.log
```

Commit frontmatter to track Notion page mappings:
```bash
git add docs/
git commit -m "Sync docs to Notion"
```

### 5. Regular Backups

Download from Notion periodically:
```bash
# Backup all pages
for page_id in $(cat notion_pages.txt); do
  notion-to-markdown "$page_id" "backups/$(date +%Y%m%d)_$page_id.md"
done
```

## Getting Help

- **Documentation:** https://github.com/graemejross/notion-sync-tools
- **Issues:** https://github.com/graemejross/notion-sync-tools/issues
- **Notion API Docs:** https://developers.notion.com/
