# Grok Search
<div align="center">

English | [简体中文](../README.md)

**Grok Search — SERP API Service Powered by Grok's Built-in Search**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

</div>

---

## Overview

Grok Search is a lightweight **SERP (Search Engine Results Page) API service** that leverages Grok model's built-in search capabilities to provide standardized search result endpoints.

Simply provide your Grok API URL and key to deploy a private search API service.

```
Client ──HTTP GET──► Grok Search API ──► Grok API (AI Search)
                         │
                         └─► Standard SERP JSON Response
```

### Features

- **Standard SERP API**: `/search` endpoint returning structured search results
- **Grok Built-in Search**: Leverages Grok model's web search capabilities
- **Auto Time Injection**: Injects local time context for time-sensitive queries
- **API Key Authentication**: Customizable API key to protect your service
- **Smart Retry**: Retry-After header parsing + exponential backoff
- **OpenAI Compatible**: Works with any Grok-compatible API endpoint

## Quick Start

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (recommended) or pip

### Install

```bash
# Using uv
uv pip install git+https://github.com/MeowLynxSea/GrokSearch

# Or using pip
pip install git+https://github.com/MeowLynxSea/GrokSearch
```

### Run

```bash
# Set required environment variables
export GROK_API_URL="https://api.x.ai/v1"
export GROK_API_KEY="your-grok-api-key"

# (Optional) Set service API key
export API_KEY="your-custom-api-key"

# Start the server
grok-search
```

The service starts at `http://0.0.0.0:8000` by default.

### Docker Deployment

**Using GitHub Container Registry (recommended):**

```bash
docker run -d \
  --name grok-search \
  -e GROK_API_URL="https://api.x.ai/v1" \
  -e GROK_API_KEY="your-grok-api-key" \
  -e API_KEY="your-custom-api-key" \
  -p 8000:8000 \
  ghcr.io/meowlynxsea/groksearch:main
```

**Build locally:**

```bash
git clone https://github.com/MeowLynxSea/GrokSearch.git
cd GrokSearch
docker build -t grok-search .
docker run -d \
  --name grok-search \
  -e GROK_API_URL="https://api.x.ai/v1" \
  -e GROK_API_KEY="your-grok-api-key" \
  -e API_KEY="your-custom-api-key" \
  -p 8000:8000 \
  grok-search
```

**Docker Compose:**

```yaml
# docker-compose.yml
services:
  grok-search:
    image: ghcr.io/meowlynxsea/groksearch:main
    # Or build locally: build: .
    ports:
      - "8000:8000"
    environment:
      GROK_API_URL: "https://api.x.ai/v1"
      GROK_API_KEY: "your-grok-api-key"
      API_KEY: "your-custom-api-key"
      # GROK_MODEL: "grok-4-fast"
    restart: unless-stopped
```

```bash
docker compose up -d
```

## API Documentation

### Search Endpoint

```
GET /search?q=<query>
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | ✅ | Search query |
| `model` | string | ❌ | Override Grok model |
| `platform` | string | ❌ | Focus platform (e.g. `Twitter`, `GitHub`) |

**Headers (required when `API_KEY` is configured):**

```
Authorization: Bearer <your-api-key>
```
or
```
X-API-Key: <your-api-key>
```

**Response:**

```json
{
  "searchParameters": {
    "q": "FastAPI latest version",
    "model": "grok-4-fast"
  },
  "answer": "Full Grok search response...",
  "organic": [
    {
      "position": 1,
      "title": "FastAPI Official Documentation",
      "link": "https://fastapi.tiangolo.com/",
      "snippet": ""
    }
  ],
  "searchInformation": {
    "totalResults": 5,
    "timeTakenMs": 2345.67
  }
}
```

### Health Check

```
GET /health
```

```json
{
  "status": "ok",
  "model": "grok-4-fast",
  "version": "1.0.0"
}
```

## Configuration

All configuration via environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROK_API_URL` | ✅ | — | Grok API URL (OpenAI-compatible) |
| `GROK_API_KEY` | ✅ | — | Grok API key |
| `GROK_MODEL` | ❌ | `grok-4-fast` | Default Grok model |
| `API_KEY` | ❌ | — | Service API key (empty = no auth) |
| `API_HOST` | ❌ | `0.0.0.0` | Listen address |
| `API_PORT` | ❌ | `8000` | Listen port |
| `GROK_DEBUG` | ❌ | `false` | Debug mode |
| `GROK_LOG_LEVEL` | ❌ | `INFO` | Log level |
| `GROK_LOG_DIR` | ❌ | `logs` | Log directory |
| `GROK_RETRY_MAX_ATTEMPTS` | ❌ | `3` | Max retry attempts |
| `GROK_RETRY_MULTIPLIER` | ❌ | `1` | Retry backoff multiplier |
| `GROK_RETRY_MAX_WAIT` | ❌ | `10` | Max retry wait (seconds) |

## Usage Examples

### cURL

```bash
curl "http://localhost:8000/search?q=what+is+quantum+computing" \
  -H "Authorization: Bearer your-api-key"
```

### Python

```python
import requests

resp = requests.get(
    "http://localhost:8000/search",
    params={"q": "latest news about AI"},
    headers={"Authorization": "Bearer your-api-key"},
)
data = resp.json()
print(data["answer"])
for result in data["organic"]:
    print(f"{result['position']}. {result['title']} - {result['link']}")
```

### JavaScript

```javascript
const resp = await fetch(
  "http://localhost:8000/search?q=latest+news+about+AI",
  { headers: { "Authorization": "Bearer your-api-key" } }
);
const data = await resp.json();
console.log(data.answer);
data.organic.forEach(r => console.log(`${r.position}. ${r.title} - ${r.link}`));
```

## License

[MIT License](LICENSE)

---

<div align="center">

**If this project helps you, please give it a Star!**

[![Star History Chart](https://api.star-history.com/svg?repos=MeowLynxSea/GrokSearch&type=date&legend=top-left)](https://www.star-history.com/#MeowLynxSea/GrokSearch&type=date&legend=top-left)
</div>
