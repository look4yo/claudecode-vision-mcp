# Claude Vision MCP

> Give vision to visionless LLMs. / 为没有视觉能力的模型提供识图能力。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)

An MCP server that enables LLMs without native vision capability (DeepSeek, non-vision GPT, local models, etc.) to "see" and understand images in Claude Code.

## How It Works

```
User sends image in Claude Code
          │
          ▼
  Non-vision LLM (e.g. DeepSeek)
  receives [Unsupported Image] + file path
          │
          ▼
  Calls describe_image(path, question)   ← CLAUDE.md triggers this
          │
          ▼
  MCP Server reads image → base64
          │
          ▼
  Vision Model API (Qwen / GPT / Claude)
  returns text description
          │
          ▼
  Non-vision LLM answers based on text
```

The MCP server acts as a bridge between your non-vision LLM and a vision-capable API.

## Prerequisites

- Python 3.10+
- A vision API key (see [Backend Options](#backend-options))

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/your-username/claude-vision-mcp.git
cd claude-vision-mcp
pip install -r requirements.txt
```

### 2. Configure API Key

```bash
cp .env.example .env
# Edit .env and fill in your VISION_API_KEY
```

**Get an API key** (pick one):

| Backend | Get Key | Free Tier |
|---------|---------|-----------|
| **DashScope** (default) | [bailian.console.aliyun.com](https://bailian.console.aliyun.com/) | 1M tokens (new users) |
| **OpenAI** | [platform.openai.com](https://platform.openai.com/api-keys) | $5 credit |
| **Anthropic** | [console.anthropic.com](https://console.anthropic.com/) | $5 credit |

### 3. Register in Claude Code

**Method A — User-level (all projects):**

```bash
claude mcp add vision -- python /path/to/claude-vision-mcp/server.py
```

**Method B — Project-level:**

Create `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "vision": {
      "command": "python",
      "args": ["/path/to/claude-vision-mcp/server.py"]
    }
  }
}
```

### 4. Update CLAUDE.md

Add this to your `CLAUDE.md` so the LLM knows to use the tool:

```markdown
## Image Recognition

Your underlying model does not have native vision capability. When you receive
an image, use the `describe_image` MCP tool to get its content. Do NOT use the
Read tool for image files.

Trigger: messages containing [Unsupported Image] or [Image: source: ...]
Usage: describe_image(image_path="path/to/image.jpg", question="Describe in detail")
```

### 5. Restart Claude Code

Quit and restart `claude`. You'll be prompted to approve the `vision` MCP server — select **Trust**.

Then send an image. The LLM will automatically call `describe_image` and describe what it sees.

## Model Fallback Strategy

If the primary model fails (quota exceeded, unavailable, timeout), the server
automatically tries the next model in sequence:

```
wanx-v1 → qwen3.5-omni-plus-2026-03-15 → qwen3.5-omni-plus
```

To customize, set `VISION_MODELS` in `.env` (comma-separated):

```bash
VISION_MODELS=gpt-4o,gpt-4o-mini,claude-sonnet-4-6
```

## Backend Options

Switch backends by changing `VISION_API_BASE_URL` and `VISION_API_KEY` in `.env`:

### DashScope (Alibaba Qwen) — Default

```bash
VISION_API_KEY=sk-xxxxxxxxxxxxxxxx
VISION_API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
VISION_MODELS=qwen-vl-max,qwen3.5-omni-plus
```

Cheap (~¥0.02/image), excellent Chinese OCR.

### OpenAI (GPT-4V / GPT-4o)

```bash
VISION_API_KEY=sk-xxxxxxxxxxxxxxxx
VISION_API_BASE_URL=https://api.openai.com/v1
VISION_MODELS=gpt-4o,gpt-4o-mini
```

### Anthropic (Claude Sonnet / Opus)

Requires a proxy/gateway that translates Anthropic API to OpenAI format
(e.g. [LiteLLM](https://github.com/BerriAI/litellm)).

### Any OpenAI-Compatible API

Any endpoint that implements `/chat/completions` with `image_url` support will work.

## Manual Usage

If auto-trigger via CLAUDE.md doesn't work, you can manually call:

```
Please describe this image:
describe_image(image_path="C:\Users\xxx\Desktop\photo.png")
```

Or with a specific question:

```
describe_image(image_path="photo.png", question="What table data is in region A?")
```

## How It Applies to Different LLMs

This tool works with **any** LLM in Claude Code that lacks vision:

| Model | Status |
|-------|--------|
| DeepSeek v4 (flash/pro) | ✅ Tested |
| DeepSeek v3/R1 | ✅ Compatible |
| Non-vision GPT variants | ✅ Compatible |
| Local models via Ollama/vLLM | ✅ Compatible |
| Any model behind a CC provider | ✅ Compatible (MCP is CC-layer, model-agnostic) |

The only requirement: the LLM must follow CLAUDE.md instructions to auto-trigger
the tool. For weaker models, use manual invocation as fallback.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `describe_image` tool not visible | Run `claude mcp list` — if missing, re-run `claude mcp add` |
| API returns 401 | Check `VISION_API_KEY` in `.env` |
| All models fail | Check `VISION_API_BASE_URL` or run `echo $VISION_API_KEY` |
| Image not found error | Use full absolute path, check for CJK characters in path |

## License

MIT — see [LICENSE](LICENSE) for details.
