# Configuration Guide

## Overview

Notion Sync Tools can be configured using:
1. **YAML configuration file** (recommended)
2. **Environment variables** (for CI/CD or containers)
3. **Combination of both** (env vars override YAML)

## Getting Your Notion API Token

1. Go to https://www.notion.so/my-integrations
2. Click **"+ New integration"**
3. Give it a name (e.g., "Markdown Sync Tools")
4. Choose **Internal integration**
5. Copy the **"Internal Integration Token"** (starts with `secret_`)
6. **Important:** Share your Notion pages/databases with the integration:
   - Open the page in Notion
   - Click **"..."** → **"Connections"** → Add your integration

## Configuration File (config.yaml)

### Location

The tool looks for `config.yaml` in:
1. Current working directory: `./config.yaml`
2. Home directory: `~/.notion-sync-tools/config.yaml`

Or specify manually with `--config` flag.

### Create config.yaml

```bash
# Copy the example
cp config.example.yaml config.yaml

# Edit with your token
nano config.yaml
```

### Minimal Configuration

```yaml
notion:
  token: "secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

### Full Configuration

```yaml
# Notion API Configuration
notion:
  token: "secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  api_version: "2022-06-28"

# API Rate Limiting and Performance
api:
  max_blocks_per_request: 100
  max_text_length: 2000
  retry_attempts: 3
  retry_delay: 1.0
  rate_limit_delay: 0.5

# Bulk Upload Configuration
bulk_upload:
  exclude_patterns:
    - ".git"
    - "node_modules"
    - "__pycache__"
    - ".venv"
    - "venv"

# Logging Configuration
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: ""  # Optional log file path
```

## Environment Variables

Set environment variables instead of (or in addition to) config.yaml:

```bash
# Required
export NOTION_TOKEN="secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Optional (with defaults shown)
export NOTION_API_VERSION="2022-06-28"
export NOTION_MAX_BLOCKS="100"
export NOTION_RETRY_ATTEMPTS="3"
export LOG_LEVEL="INFO"
```

### Precedence

Environment variables **override** config.yaml values:

1. Environment variables (highest priority)
2. config.yaml file
3. Default values (lowest priority)

## Docker / Container Usage

For containers, use environment variables:

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY . .
RUN pip install .

ENV NOTION_TOKEN=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ENV LOG_LEVEL=INFO

CMD ["markdown-to-notion", "--help"]
```

Or with docker-compose:

```yaml
version: '3'
services:
  notion-sync:
    build: .
    environment:
      - NOTION_TOKEN=${NOTION_TOKEN}
      - LOG_LEVEL=INFO
    volumes:
      - ./docs:/docs
```

## CI/CD Usage (GitHub Actions)

```yaml
name: Sync to Notion

on:
  push:
    paths:
      - 'docs/**/*.md'

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install tools
        run: |
          pip install git+https://github.com/graemejross/notion-sync-tools.git

      - name: Upload to Notion
        env:
          NOTION_TOKEN: ${{ secrets.NOTION_TOKEN }}
        run: |
          bulk-upload-notion ${{ secrets.NOTION_PARENT_PAGE }} docs/
```

## Security Best Practices

⚠️ **NEVER commit your Notion token to version control!**

### Protect Your Token

1. **Add to .gitignore:**
   ```
   config.yaml
   .notion-credentials
   .env
   ```

2. **Use secrets management:**
   - GitHub Secrets (for GitHub Actions)
   - AWS Secrets Manager (for production)
   - HashiCorp Vault (for enterprise)
   - Environment variables (for local/dev)

3. **Rotate tokens regularly:**
   - Create new integration token
   - Update configuration
   - Delete old token

## Troubleshooting

### "Notion token is required" error

Make sure you've set the token via:
- `config.yaml` with `notion.token` field
- `NOTION_TOKEN` environment variable

### "Page not found" or "Forbidden" errors

Your integration needs permission to access the page:
1. Open the Notion page
2. Click **"..."** → **"Connections"**
3. Add your integration

### Token not working

- Check it starts with `secret_`
- Verify you copied the entire token
- Make sure the integration hasn't been deleted
- Try creating a new integration

## Next Steps

Continue to [Usage Examples](usage.md) to start syncing!
