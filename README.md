# Hermes Crawl4ai Web Extract Plugin

Self-hosted web content extraction plugin for Hermes using [crawl4ai](https://github.com/unclecode/crawl4ai).

## Overview

This plugin provides a `crawl4ai` web extract backend for Hermes. It enables extraction of clean markdown content from any URL, including JavaScript-rendered pages, using your own self-hosted crawl4ai instance.

**Perfect pairing with searxng** for a fully self-hosted search + extract stack:
- `searxng` -> self-hosted web search
- `crawl4ai` -> self-hosted web extraction (this plugin)

## About crawl4ai

[crawl4ai](https://github.com/unclecode/crawl4ai) is an open-source web crawler and extractor designed for LLM-friendly output. Key points:

- **Self-hosted** -- runs on your infrastructure via Docker (`docker pull unclecode/crawl4ai`)
- **LLM-optimized** -- returns clean markdown via the `/md` endpoint, ideal for RAG and agent workflows
- **JavaScript rendering** -- built-in browser handles SPAs and dynamic content
- **No vendor lock-in** -- no API keys to buy, no rate limits, no data leaving your network
- **Docker Hub:** `unclecode/crawl4ai`

It's the natural counterpart to `searxng`: search locally, extract locally, zero external dependencies.

## Installation

```bash
# Clone into your Hermes plugins directory (flat layout)
git clone https://github.com/mblauser/hermes-plugin-crawl4ai.git ~/.hermes/plugins/crawl4ai

# Install Python dependency (Debian/Ubuntu)
sudo apt install -y python3-httpx

# Or via pip (other distros)
# pip install httpx
```

## Configuration

Set these environment variables (in `~/.hermes/.env` or your shell profile):

```bash
# Required: URL of your crawl4ai instance
export CRAWL4AI_URL=http://localhost:11235

# Required: JWT API token (your crawl4ai instance requires auth by default)
export CRAWL4AI_API_TOKEN=your-jwt-token
```

**Note:** The plugin's `is_available()` checks for both `CRAWL4AI_URL` and
`CRAWL4AI_API_TOKEN`. If your crawl4ai instance has auth disabled, patch
`provider.py` to drop the token check.

### Single-profile setup

Add to your Hermes config (at `~/.hermes/config.yaml` or your active profile):

```yaml
plugins:
  enabled:
    - crawl4ai

web:
  extract_backend: "crawl4ai"
```

### Multi-profile setup (repeat per profile)

Each Hermes profile has its own config and plugin discovery path.
Repeat for every profile that needs crawl4ai:

1. **Enable the plugin** in the profile's config:

   ```yaml
   # ~/.hermes/profiles/<name>/config.yaml
   plugins:
     enabled:
       - crawl4ai

   web:
     extract_backend: "crawl4ai"
   ```

   The `plugins.enabled` key is NOT inherited from the base
   `~/.hermes/config.yaml`. Each profile's config is authoritative.

2. **Symlink the plugin** into the profile's plugin directory:

   ```bash
   mkdir -p ~/.hermes/profiles/<name>/plugins
   ln -s ~/.hermes/plugins/crawl4ai ~/.hermes/profiles/<name>/plugins/crawl4ai
   ```

   Hermes per-profile plugin discovery scans
   `~/.hermes/profiles/<name>/plugins/`, NOT the base
   `~/.hermes/plugins/`. Without this symlink, the profile won't
   find the plugin even with correct config.

3. **Restart the profile's gateway**:

   ```bash
   systemctl --user restart hermes-gateway-<name>.service
   ```

   Each profile runs its own systemd gateway service. Restarting one
   does NOT reload others.

### Verifying the plugin loaded

```bash
# Check plugin is registered
hermes plugins list | grep crawl4ai

# Live test with web_extract
hermes -p <name> -z 'extract content from https://example.com'
```

If you see "SearXNG is a search-only backend" despite correct config,
the plugin didn't load. Check the three things:

1. Is `plugins.enabled: [crawl4ai]` in the **profile's** config.yaml?
2. Does the profile have a symlink at `plugins/crawl4ai`?
3. Was the profile's gateway restarted after changes?

See the `self-hosted-web-backends` skill (`skill_view(name='self-hosted-web-backends')`)
for the full troubleshooting checklist, including the load-order bug (PR
[#67309](https://github.com/NousResearch/hermes-agent/pull/67309)) that
can prevent plugin-registered backends from being selected even when the
plugin is installed and registered.

## Compatibility

This plugin depends on the plugin-provider load-order fix in Hermes (see
PR [#67309](https://github.com/NousResearch/hermes-agent/pull/67309)).
On Hermes versions without this fix, the plugin installs and registers
correctly but the `crawl4ai` extract backend cannot be selected. The fix
is merged into the Hermes main branch; run `hermes update` or upgrade to
a release that includes it.

## Usage

Once installed and configured, use it automatically:

```bash
# Explicit backend
hermes chat -q "extract https://example.com using crawl4ai"

# Or if set as default backend in config.yaml:
hermes chat -q "extract https://example.com"
```

## Requirements

- **crawl4ai instance** -- run via Docker:

  ```bash
  docker run -d -p 11235:11235 unclecode/crawl4ai
  ```

  The API token will be logged on startup.

## How It Works

- Calls crawl4ai's `/md` endpoint for clean markdown extraction
- Handles JavaScript-rendered pages via crawl4ai's built-in browser
- Returns normalized document format compatible with Hermes web tools
- Self-hosted -- no third-party API costs, no data leaves your infrastructure

## License

MIT -- same as crawl4ai and Hermes.
