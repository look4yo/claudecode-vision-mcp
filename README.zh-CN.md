# Claudecode Vision MCP

> 为 Claude Code 中无原生视觉能力的基座模型提供识图能力。

[English](README.md) | [简体中文](README.zh-CN.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)

Claudecode Vision MCP 是一个面向 Claude Code 的轻量 MCP server。它可以让 DeepSeek、本地模型、纯文本模型等无法直接读取图片的基座模型，通过调用支持视觉能力的 OpenAI-compatible API 来理解图片内容。

DeepSeek 是主要验证场景之一，但这个工具并不绑定 DeepSeek。只要 Claude Code 中的基座模型能够遵循指令并调用 MCP 工具，就可以使用这个 server。

## 工作原理

```text
用户在 Claude Code 中发送或引用图片
          |
          v
  无视觉能力的基座模型收到图片路径或 unsupported-image 标记
          |
          v
  模型调用 describe_image(image_path, question)
          |
          v
  MCP server 读取本地图片，并以 base64 data URL 发送给视觉 API
          |
          v
  视觉 API 返回文字描述
          |
          v
  无视觉模型基于文字描述回答用户问题
```

## 示例：启用前后对比

下图是一个用于测试 OCR、表格提取、图表读取、形状计数和短备注查找的能力测试页。同一张图片、同一类详细读取提示词，在未启用和启用本 MCP server 后得到的结果如下。

![Vision capability test sheet](assets/vision-capability-test-sheet.png)

| 任务 | 未启用 MCP server | 启用 MCP server 后 |
| --- | --- | --- |
| 读取图片 | 模型返回 `[Unsupported Image]`，并且没有猜测。 | 模型调用 `describe_image`，返回结构化图片内容。 |
| 主标题 | `uncertain` | `Vision Capability Test Sheet` |
| A 区实验表 | 所有样本字段均为 `uncertain`。 | 提取出 A1-A5 的数值，包括 A4 为 `HOLD`，Temp `23.6`，Pressure `97.5`，Yield `66.3`。 |
| 需要 follow-up 的样本 | 空结果。 | `A2`、`A4` |
| B 区月度柱状图 | Jan-Jun 数值均为 `null`。 | Jan `14`，Feb `22`，Mar `19`，Apr `27`，May `25`，Jun `31`；峰值月份为 `June`。 |
| C 区形状计数 | 形状数量均为 `null`。 | 红色圆形 `5`，蓝色三角形 `7`，绿色正方形 `4`；蓝色三角形数量超过 6。 |
| D 区短备注 | 备注字段均为 `uncertain`。 | Meeting room `C204`，Inspector `Lina Zhou`，Device ID `KX-17`，Retry threshold `0.85`，Backup date `2026-05-08`。 |
| Verification code | `uncertain` | `VX-2749` |

总结：未启用视觉桥接时，基座模型没有编造答案，但也无法完成视觉任务。启用本 MCP server 后，同一个无视觉工作流可以把图片交给视觉模型处理，再基于返回的文字内容回答问题。这个示例是功能演示，不是 benchmark，也不保证所有模型、供应商或图片都能达到同样准确率。

## 前置要求

- Python 3.10+
- 支持 MCP 的 Claude Code
- 一个支持视觉输入的 OpenAI-compatible API key

## 快速开始

### 1. 克隆并安装

```bash
git clone https://github.com/look4yo/claudecode-vision-mcp.git
cd claudecode-vision-mcp
pip install -r requirements.txt
```

Conda 示例：

```bash
conda create -n vision-mcp python=3.12
conda activate vision-mcp
pip install -r requirements.txt
```

### 2. 配置 API

```bash
cp .env.example .env
# 编辑 .env，并填写 VISION_API_KEY。
```

常见后端：

| 后端 | API key 页面 | 说明 |
| --- | --- | --- |
| DashScope / Alibaba Qwen | [bailian.console.aliyun.com](https://bailian.console.aliyun.com/) | 本仓库默认 base URL。推荐原因之一是阿里云百炼通常会为新用户提供较充足的多模态千问模型免费额度；具体额度和有效期请以官方免费额度页面为准。 |
| OpenAI | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | 需要选择支持视觉输入的 chat model |
| Anthropic | [console.anthropic.com](https://console.anthropic.com/) | 需要 LiteLLM 等 OpenAI-compatible gateway |
| 其他供应商 | 供应商文档 | 必须支持带 `image_url` 输入的 `/chat/completions` |

### 3. 注册到 Claude Code

用户级注册：

```bash
claude mcp add vision -- python /absolute/path/to/claudecode-vision-mcp/server.py
```

Windows 示例：

```powershell
claude mcp add vision -- C:\Users\you\.conda\envs\vision-mcp\python.exe D:\tools\claudecode-vision-mcp\server.py
```

项目级 `.mcp.json` 示例：

```json
{
  "mcpServers": {
    "vision": {
      "command": "python",
      "args": ["/absolute/path/to/claudecode-vision-mcp/server.py"]
    }
  }
}
```

Windows 项目级示例：

```json
{
  "mcpServers": {
    "vision": {
      "command": "C:\\Users\\you\\.conda\\envs\\vision-mcp\\python.exe",
      "args": ["D:\\tools\\claudecode-vision-mcp\\server.py"]
    }
  }
}
```

### 4. 告诉基座模型何时使用工具

在项目的 `CLAUDE.md` 中加入类似指令：

```markdown
## Image Recognition

Your underlying model does not have native vision capability. When the user
sends an image, references an image path, or you see an unsupported-image
marker, call the `describe_image` MCP tool before answering.

Do not use the Read tool for binary image files. Use:

describe_image(image_path="/absolute/path/to/image.png", question="Describe the image in detail")
```

自动触发依赖基座模型遵循这些指令。如果较弱模型没有主动调用工具，可以手动提示：

```text
Use describe_image on D:\path\to\image.png and answer based on the result.
```

## 配置

server 会从 `server.py` 同目录下读取 `.env`。

```bash
VISION_API_KEY=sk-your-key-here
VISION_API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
VISION_MAX_TOKENS=4096
VISION_MODELS=qwen3.5-plus,qwen3.5-omni-plus-2026-03-15,qwen3.5-omni-plus
```

`VISION_MODELS` 是可选项。未设置或留空时，默认使用：

```text
qwen3.5-plus -> qwen3.5-omni-plus-2026-03-15 -> qwen3.5-omni-plus
```

fallback 只用于 quota、模型不可用、模型不存在、限流、服务不可用等可重试失败。`400`、`401`、`403` 这类配置或认证错误会直接返回。

## 后端示例

DashScope / Alibaba Qwen：

```bash
VISION_API_KEY=sk-xxxxxxxxxxxxxxxx
VISION_API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
VISION_MODELS=qwen3.5-plus,qwen3.5-omni-plus
```

OpenAI：

```bash
VISION_API_KEY=sk-xxxxxxxxxxxxxxxx
VISION_API_BASE_URL=https://api.openai.com/v1
VISION_MODELS=gpt-4o,gpt-4o-mini
```

任意 OpenAI-compatible endpoint 都可以使用，前提是它支持如下 `image_url` 输入：

```json
{"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
```

## 工具

`describe_image`

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `image_path` | 是 | 本地图片文件的绝对路径 |
| `question` | 否 | 针对图片的具体问题；未提供时默认要求详细描述 |

支持的扩展名：`.jpg`、`.jpeg`、`.png`、`.gif`、`.webp`、`.bmp`、`.tiff`、`.tif`。

## 适用范围

最适合能稳定遵循工具调用指令的 Claude Code 基座模型：

| 基座模型类型 | 预期状态 |
| --- | --- |
| Claude Code 中的 DeepSeek | 主要验证场景 |
| 通过 Claude Code provider 接入的本地文本模型 | 能可靠调用 MCP 工具时兼容 |
| 无原生视觉能力的托管模型 | 能调用 MCP 工具时兼容 |
| 原生视觉模型 | 通常不需要本工具 |

## 排查问题

| 问题 | 处理方式 |
| --- | --- |
| 看不到 `describe_image` 工具 | 运行 `claude mcp list`，如果不存在则重新添加 server |
| 缺少 API key | 在 `.env` 或进程环境变量中设置 `VISION_API_KEY` |
| API 返回 `401` 或 `403` | 检查 API key、区域、供应商权限和 base URL |
| API 返回 `400` | 检查所选模型是否支持 `image_url` chat-completions 输入 |
| 所有模型都失败 | 检查 `VISION_MODELS`、`VISION_API_BASE_URL`、供应商额度和网络访问 |
| 图片不存在 | 使用绝对路径，并确认 Claude Code 可以访问该文件 |
| 模型没有自动调用工具 | 加强 `CLAUDE.md` 指令，或手动要求调用 `describe_image` |

## License

MIT。见 [LICENSE](LICENSE)。
