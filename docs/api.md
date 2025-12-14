# API Reference

For programmatic usage of the Notion Sync Tools in your Python code.

## Installation

```python
from notion_sync import Config, upload_to_notion, download_from_notion
```

## Configuration

### Load Configuration

```python
from notion_sync.config import load_config
from pathlib import Path

# Load from default locations (config.yaml or env vars)
config = load_config()

# Load from specific file
config = load_config(Path("/path/to/config.yaml"))

# Access configuration
token = config.notion_token
api_version = config.api_version
max_blocks = config.max_blocks_per_request
```

### Create Configuration Manually

```python
from notion_sync.config import Config

# Create minimal config (requires NOTION_TOKEN env var)
config = Config()

# Or provide config file
config = Config(config_file=Path("./my-config.yaml"))
```

### Configuration Properties

```python
# Notion API
config.notion_token          # str: API token
config.api_version           # str: API version

# Rate limiting
config.max_blocks_per_request  # int: Max blocks per request (100)
config.max_text_length         # int: Max text length (2000)
config.retry_attempts          # int: Number of retries (3)
config.retry_delay             # float: Delay between retries (1.0s)
config.rate_limit_delay        # float: Delay between requests (0.5s)

# Bulk upload
config.exclude_patterns      # List[str]: Exclude patterns

# Logging
config.log_level            # str: Log level (INFO)
config.log_format           # str: Log format string
config.log_file             # str: Log file path (empty = console only)
```

## Upload Markdown to Notion

### upload_to_notion()

```python
from notion_sync import upload_to_notion
from pathlib import Path

# Create new page
page_id, page_url, blocks_uploaded = upload_to_notion(
    md_file=Path("README.md"),
    parent_id="2bfc95e7d72e816486a5cfb9a97fa8c9",
    update_mode=False,
    config=config  # Optional, loads default if None
)

print(f"Created page: {page_url}")
print(f"Uploaded {blocks_uploaded} blocks")
```

### Update existing page

```python
# Update mode (requires notion_page_id in frontmatter)
page_id, page_url, blocks_uploaded = upload_to_notion(
    md_file=Path("README.md"),
    update_mode=True,
    config=config
)
```

### Parameters

- **md_file** (Path): Path to markdown file
- **parent_id** (str, optional): Parent page ID for create mode
- **update_mode** (bool): Whether to update existing page
- **config** (Config, optional): Configuration object

### Returns

Tuple of `(page_id, page_url, blocks_uploaded)`:
- **page_id** (str): Notion page ID
- **page_url** (str): Notion page URL
- **blocks_uploaded** (int): Number of blocks uploaded

### Raises

- **FileNotFoundError**: If markdown file doesn't exist
- **ValueError**: If invalid arguments
- **urllib.error.HTTPError**: On API errors

## Download from Notion

### download_from_notion()

```python
from notion_sync import download_from_notion
from pathlib import Path

# Download page
title, block_count = download_from_notion(
    page_id="2bfc95e7d72e816486a5cfb9a97fa8c9",
    output_file=Path("output.md"),
    config=config  # Optional
)

print(f"Downloaded: {title}")
print(f"Blocks: {block_count}")
```

### Parameters

- **page_id** (str): Notion page ID or URL
- **output_file** (Path): Path to save markdown file
- **config** (Config, optional): Configuration object

### Returns

Tuple of `(title, block_count)`:
- **title** (str): Page title
- **block_count** (int): Number of blocks downloaded

### Raises

- **urllib.error.HTTPError**: On API errors

## Bulk Upload

### bulk_upload()

```python
from notion_sync.bulk_upload import bulk_upload
from pathlib import Path

# Bulk upload directory
uploaded, skipped, failed = bulk_upload(
    parent_id="2bfc95e7d72e816486a5cfb9a97fa8c9",
    directory=Path("./docs"),
    config=config  # Optional
)

print(f"Uploaded: {uploaded}")
print(f"Skipped: {skipped}")
print(f"Failed: {failed}")
```

### Parameters

- **parent_id** (str): Parent page ID for all uploads
- **directory** (Path): Directory to search for markdown files
- **config** (Config, optional): Configuration object

### Returns

Tuple of `(uploaded, skipped, failed)`:
- **uploaded** (int): Number of files uploaded
- **skipped** (int): Number of files skipped
- **failed** (int): Number of files that failed

### Raises

- **ValueError**: If directory doesn't exist

## Advanced Usage

### Custom Retry Logic

```python
import time
from notion_sync.markdown_to_notion import make_api_request

# Make API request with custom retry logic
try:
    result = make_api_request(
        url="https://api.notion.com/v1/pages/123",
        token=config.notion_token,
        api_version=config.api_version,
        method='GET',
        config=config
    )
except urllib.error.HTTPError as e:
    print(f"API error: {e.code}")
```

### Parse Markdown Manually

```python
from notion_sync.markdown_to_notion import markdown_to_notion_blocks

# Convert markdown to Notion blocks
md_content = "# Hello\n\nThis is **bold** text."
blocks = markdown_to_notion_blocks(md_content, config)

print(f"Generated {len(blocks)} blocks")
```

### Extract Page ID from URL

```python
from notion_sync.markdown_to_notion import extract_page_id

# Extract ID from URL
page_id = extract_page_id("https://www.notion.so/My-Page-2bfc95e7d72e816486a5cfb9a97fa8c9")
# Returns: "2bfc95e7-d72e-8164-86a5-cfb9a97fa8c9"
```

## Error Handling

### Common Exceptions

```python
from urllib.error import HTTPError

try:
    page_id, page_url, blocks = upload_to_notion(
        md_file=Path("doc.md"),
        parent_id="invalid-id"
    )
except FileNotFoundError as e:
    print(f"File not found: {e}")
except ValueError as e:
    print(f"Invalid arguments: {e}")
except HTTPError as e:
    if e.code == 401:
        print("Invalid Notion token")
    elif e.code == 404:
        print("Page not found or no permission")
    elif e.code == 429:
        print("Rate limited (automatically retried)")
    else:
        print(f"API error: {e.code}")
```

### Logging

```python
import logging

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Now all operations will show debug output
upload_to_notion(...)
```

## Examples

### Sync Documentation Site

```python
from pathlib import Path
from notion_sync import Config, upload_to_notion, bulk_upload

# Load config
config = Config()

# Bulk upload docs
uploaded, skipped, failed = bulk_upload(
    parent_id="YOUR_PARENT_PAGE_ID",
    directory=Path("./docs"),
    config=config
)

print(f"Documentation sync complete!")
print(f"  Uploaded: {uploaded}")
print(f"  Skipped: {skipped} (already synced)")
print(f"  Failed: {failed}")
```

### Bidirectional Sync

```python
from pathlib import Path
from notion_sync import download_from_notion, upload_to_notion

# Download from Notion
title, blocks = download_from_notion(
    page_id="YOUR_PAGE_ID",
    output_file=Path("document.md")
)

# Edit locally
# (user edits document.md)

# Upload changes back
page_id, url, uploaded = upload_to_notion(
    md_file=Path("document.md"),
    update_mode=True  # Uses notion_page_id from frontmatter
)

print(f"Updated {uploaded} blocks")
```

### Backup All Pages

```python
import json
from pathlib import Path
from notion_sync import download_from_notion

# Load page IDs from file
with open("page_ids.json") as f:
    page_ids = json.load(f)

# Backup each page
backup_dir = Path("./backups")
backup_dir.mkdir(exist_ok=True)

for page_id in page_ids:
    output = backup_dir / f"{page_id}.md"
    try:
        title, blocks = download_from_notion(page_id, output)
        print(f"✅ Backed up: {title}")
    except Exception as e:
        print(f"❌ Failed {page_id}: {e}")
```

## Type Hints

All functions include full type hints:

```python
from typing import Tuple, Optional
from pathlib import Path
from notion_sync.config import Config

def upload_to_notion(
    md_file: Path,
    parent_id: Optional[str] = None,
    update_mode: bool = False,
    config: Optional[Config] = None
) -> Tuple[str, str, int]:
    ...

def download_from_notion(
    page_id: str,
    output_file: Path,
    config: Optional[Config] = None
) -> Tuple[str, int]:
    ...
```

## Testing

### Mock Configuration for Tests

```python
import unittest
from unittest.mock import Mock
from notion_sync.config import Config

class TestNotionSync(unittest.TestCase):
    def setUp(self):
        # Mock config
        self.config = Mock(spec=Config)
        self.config.notion_token = "test_token"
        self.config.api_version = "2022-06-28"
        self.config.max_blocks_per_request = 100

    def test_upload(self):
        # Your test here
        pass
```

## Further Reading

- [Usage Guide](usage.md) - Command-line usage examples
- [Configuration](configuration.md) - Detailed configuration options
- [Notion API Documentation](https://developers.notion.com/) - Official API docs
