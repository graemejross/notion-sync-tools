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
