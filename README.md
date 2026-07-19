# Hermes Crawl4ai Web Extract Plugin

Self-hosted web content extraction plugin for Hermes using [crawl4ai](https://github.com/unclecode/crawl4ai).

## Overview

This plugin provides a `crawl4ai` web extract backend for Hermes. It enables extraction of clean markdown content from any URL, including JavaScript-rendered pages, using your own self-hosted crawl4ai instance.

**Perfect pairing with searxng** for a fully self-hosted search + extract stack:
- `searxng` → self-hosted web search
- `crawl4ai` → self-hosted web extraction (this plugin)

## About crawl4ai

[crawl4ai](https://github.com/unclecode/crawl4ai) is an open-source web crawler and extractor designed for LLM-friendly output. Key points:

- **Self-hosted** — runs on your infrastructure via Docker (`docker pull unclecode/crawl4ai`)
- **LLM-optimized** — returns clean markdown via the `/md` endpoint, ideal for RAG and agent workflows
- **JavaScript rendering** — built-in browser handles SPAs and dynamic content
- **No vendor lock-in** — no API keys to buy, no rate limits, no data leaving your network
- **Docker Hub:** `unclecode/crawl4ai`

It's the natural counterpart to `searxng`: search locally, extract locally, zero external dependencies.

## Installation

```bash
# Clone into your Hermes plugins directory (flat layout)
git clone https://github.com/mblauser/hermes-plugin-crawl4ai.git ~/.hermes/plugins/crawl4ai

# Install Python dependency
pip install --break-system-packages httpx
```

Then **enable the plugin** in `~/.hermes/config.yaml`:

```yaml
plugins:
  enabled:
    - crawl4ai
```

## Configuration

Set these environment variables (in `~/.hermes/.env` or your shell profile):

```bash
# Required: URL of your crawl4ai instance
export CRAWL4AI_URL=http://localhost:11235

# Optional: JWT API token (if your crawl4ai instance requires auth)
export CRAWL4AI_API_TOKEN=your-jwt-token
```

Configure in `~/.hermes/config.yaml`:

```yaml
web:
  extract_backend: "crawl4ai"
```

**Restart the Hermes gateway** after making config changes:

```bash
hermes gateway restart
```

Plugins are loaded at startup — a restart is required for the plugin to be registered as a valid extract backend.

## Usage

Once installed and configured, use it automatically:

```bash
# Explicit backend
hermes chat -q "extract https://example.com using crawl4ai"

# Or if set as default backend in config.yaml:
hermes chat -q "extract https://example.com"
```

## Requirements

- **crawl4ai instance** — run via Docker:
  ```bash
  docker run -d -p 11235:11235 unclecode/crawl4ai
  ```
  The API token will be logged on startup.

## How It Works

- Calls crawl4ai's `/md` endpoint for clean markdown extraction
- Handles JavaScript-rendered pages via crawl4ai's built-in browser
- Returns normalized document format compatible with Hermes web tools
- Self-hosted — no third-party API costs, no data leaves your infrastructure

## License

MIT — same as crawl4ai and Hermes.
