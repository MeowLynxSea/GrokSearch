# Grok Search

<div align="center">

[English](./docs/README_EN.md) | 简体中文

**Grok Search — 基于 Grok 内置搜索的 SERP API 服务**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

</div>

---

## 概述

Grok Search 是一个轻量级的 **SERP（Search Engine Results Page）API 服务**，利用 Grok 模型的内置搜索能力，对外提供标准化的搜索结果接口。

用户只需提供 Grok API 地址和密钥，即可快速部署一个私有的搜索 API 服务。

```
Client ──HTTP GET──► Grok Search API ──► Grok API（AI 搜索）
                         │
                         └─► 标准 SERP JSON 响应
```

### 功能特性

- **标准 SERP API**：提供 `/search` 端点，返回结构化搜索结果
- **Grok 内置搜索**：利用 Grok 模型的联网搜索能力
- **自动时间注入**：自动注入本地时间上下文，提升时效性搜索准确度
- **API Key 鉴权**：支持自定义 API 密钥保护服务
- **智能重试**：支持 Retry-After 头解析 + 指数退避
- **OpenAI 兼容接口**：支持任意 Grok 镜像站

## 快速开始

### 前置条件

- Python 3.10+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)（推荐）或 pip

### 安装

```bash
# 使用 uv
uv pip install git+https://github.com/MeowLynxSea/GrokSearch

# 或使用 pip
pip install git+https://github.com/MeowLynxSea/GrokSearch
```

### 运行

```bash
# 设置必要的环境变量
export GROK_API_URL="https://api.x.ai/v1"
export GROK_API_KEY="your-grok-api-key"

# （可选）设置服务 API 密钥
export API_KEY="your-custom-api-key"

# 启动服务
grok-search
```

服务默认在 `http://0.0.0.0:8000` 启动。

### Docker 部署

**使用 GitHub Container Registry（推荐）：**

```bash
docker run -d \
  --name grok-search \
  -e GROK_API_URL="https://api.x.ai/v1" \
  -e GROK_API_KEY="your-grok-api-key" \
  -e API_KEY="your-custom-api-key" \
  -p 8000:8000 \
  ghcr.io/meowlynxsea/groksearch:main
```

**本地构建：**

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

**Docker Compose：**

```yaml
# docker-compose.yml
services:
  grok-search:
    image: ghcr.io/meowlynxsea/groksearch:main
    # 或本地构建: build: .
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

## API 文档

### 搜索接口

```
GET /search?q=<query>
```

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `q` | string | ✅ | 搜索查询语句 |
| `model` | string | ❌ | 指定 Grok 模型（覆盖默认值） |
| `platform` | string | ❌ | 聚焦平台（如 `Twitter`, `GitHub`） |

**请求头（当配置了 `API_KEY` 时必须）：**

```
Authorization: Bearer <your-api-key>
```
或
```
X-API-Key: <your-api-key>
```

**响应示例：**

```json
{
  "searchParameters": {
    "q": "FastAPI latest version",
    "model": "grok-4-fast"
  },
  "answer": "Grok 的搜索回答全文...",
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

### 健康检查

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

## 配置参数

通过环境变量配置：

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `GROK_API_URL` | ✅ | — | Grok API 地址（OpenAI 兼容格式） |
| `GROK_API_KEY` | ✅ | — | Grok API 密钥 |
| `GROK_MODEL` | ❌ | `grok-4-fast` | 默认使用的 Grok 模型 |
| `API_KEY` | ❌ | — | 本服务的 API 密钥（留空则不校验） |
| `API_HOST` | ❌ | `0.0.0.0` | 服务监听地址 |
| `API_PORT` | ❌ | `8000` | 服务监听端口 |
| `GROK_DEBUG` | ❌ | `false` | 调试模式 |
| `GROK_LOG_LEVEL` | ❌ | `INFO` | 日志级别 |
| `GROK_LOG_DIR` | ❌ | `logs` | 日志目录 |
| `GROK_RETRY_MAX_ATTEMPTS` | ❌ | `3` | 最大重试次数 |
| `GROK_RETRY_MULTIPLIER` | ❌ | `1` | 重试退避乘数 |
| `GROK_RETRY_MAX_WAIT` | ❌ | `10` | 重试最大等待秒数 |

## 使用示例

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

## 致谢

- 感谢 [linux.do](https://linux.do) 社区的支持与分享
- 本项目基于 [GuDaStudio/GrokSearch](https://github.com/GuDaStudio/GrokSearch) 改造，感谢原项目的贡献

## 许可证

[MIT License](LICENSE)

---

<div align="center">

**如果这个项目对您有帮助，请给个 Star！**

</div>
