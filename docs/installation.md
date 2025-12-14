---
notion_page_id: 2c9c95e7-d72e-81c1-82d3-e1186a6820a2
notion_url: https://www.notion.so/installation-2c9c95e7d72e81c182d3e1186a6820a2
title: installation
uploaded: 2025-12-14T12:05:21.228595
---

# Installation Guide

## Requirements

- **Python 3.7 or higher**
- **PyYAML** (automatically installed)

## Installation Methods

### Method 1: Install from Source (Recommended)

```bash
# Clone the repository
git clone https://github.com/graemejross/notion-sync-tools.git
cd notion-sync-tools

# Install in development mode
pip install -e .
```

This creates the command-line tools:
- `markdown-to-notion`
- `notion-to-markdown`
- `bulk-upload-notion`

### Method 2: Install as Package

```bash
# Clone and install
git clone https://github.com/graemejross/notion-sync-tools.git
cd notion-sync-tools
pip install .
```

### Method 3: Use Directly (No Installation)

```bash
# Clone the repository
git clone https://github.com/graemejross/notion-sync-tools.git
cd notion-sync-tools

# Install PyYAML dependency
pip install PyYAML

# Run directly
python -m notion_sync.markdown_to_notion --help
python -m notion_sync.notion_to_markdown --help
python -m notion_sync.bulk_upload --help
```

## Verification

Check that installation worked:

```bash
# Test commands are available
markdown-to-notion --help
notion-to-markdown --help
bulk-upload-notion --help
```

## Next Steps

Continue to [Configuration](configuration.md) to set up your Notion API token.
