---
notion_page_id: 2c9c95e7-d72e-81b1-a82e-ca3499f08f68
notion_url: https://www.notion.so/README-2c9c95e7d72e81b1a82eca3499f08f68
title: /README
uploaded: 2025-12-14T12:08:50.892111
---

# Notion Sync Tools

Bidirectional markdown ↔ Notion sync tools with full formatting preservation. Upload/download markdown files to Notion with YAML frontmatter tracking.

## Features

✨ **Full Markdown Support**
- Bold, italic, code, strikethrough, links
- Headings (H1, H2, H3)
- Lists (bulleted, numbered, to-do)
- Code blocks with syntax highlighting
- Tables (auto-splits large tables > 100 rows)
- Quotes, dividers, and more

🔄 **Bidirectional Sync**
- Upload markdown → Notion (create or update)
- Download Notion → markdown
- YAML frontmatter tracking (prevents duplicates)
- Bulk operations support

🛡️ **Production Ready**
- Configurable via YAML or environment variables
- Comprehensive error handling
- Rate limiting and retries
- Proper logging
- No hardcoded paths or credentials

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/graemejross/notion-sync-tools.git
cd notion-sync-tools

# Install (creates command-line tools)
pip install -e .
```

### 2. Configuration

Create a `config.yaml` file:

```yaml
# Notion API Configuration
notion:
  # Get your token from: https://www.notion.so/my-integrations
  token: "secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  api_version: "2022-06-28"

# Rate limiting
api:
  max_blocks_per_request: 100
  max_text_length: 2000
  retry_attempts: 3
  retry_delay: 1.0
  rate_limit_delay: 0.5

# Bulk upload exclusions
bulk_upload:
  exclude_patterns:
    - ".git"
    - "node_modules"
    - "__pycache__"
    - ".venv"
    - "venv"
    - ".pytest_cache"
```

Or use environment variables:

```bash
export NOTION_TOKEN="secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export NOTION_API_VERSION="2022-06-28"
```

### 3. Usage

**Upload markdown to Notion:**

```bash
# Create new page
markdown-to-notion README.md <parent_page_id>

# Update existing page (uses notion_page_id from frontmatter)
markdown-to-notion README.md --update
```

**Download from Notion:**

```bash
# Download page to markdown
notion-to-markdown <page_id_or_url> output.md
```

**Bulk upload:**

```bash
# Upload all markdown files in a directory
bulk-upload-notion <parent_page_id> /path/to/docs
```

## Documentation

- Installation Guide (see installation page)
- Configuration (see configuration page)
- Usage Examples (see usage page)
- API Reference (see api page)

## How It Works

### YAML Frontmatter Tracking

When you upload a markdown file, the tool automatically adds YAML frontmatter:

```yaml
---
notion_page_id: 2bfc95e7-d72e-8164-86a5-cfb9a97fa8c9
notion_url: https://www.notion.so/My-Page-2bfc95e7d72e816486a5cfb9a97fa8c9
title: My Page
uploaded: 2025-12-14T10:30:00
---

# Your markdown content here
```

This prevents duplicate uploads and enables update mode.

### Formatting Preservation

The tools preserve all markdown formatting when converting to Notion blocks:

- **Bold** → Notion bold annotation
- *Italic* → Notion italic annotation
- `code` → Notion code annotation
- ~~Strikethrough~~ → Notion strikethrough
- Links `[text](url)` → Notion link objects
- Tables → Notion table blocks (auto-split if > 100 rows)

## Examples

See the examples directory for:
- Sample markdown files
- Configuration examples
- Common use cases

## Requirements

- Python 3.7+
- No external dependencies (uses only Python standard library)

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

- **Issues:** https://github.com/graemejross/notion-sync-tools/issues
- **Discussions:** https://github.com/graemejross/notion-sync-tools/discussions

## Credits

Created by Graeme Ross ([@graemejross](https://github.com/graemejross))

Built with the [Notion API](https://developers.notion.com/).
