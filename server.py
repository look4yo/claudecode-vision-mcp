"""MCP Vision Server — Give vision to visionless LLMs.

Call a vision-capable model API to convert image content into text descriptions.
Supports automatic model fallback: wanx-v1 → qwen3.5-omni-plus-2026-03-15 → qwen3.5-omni-plus
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import httpx

load_dotenv(Path(__file__).resolve().parent / ".env")

API_KEY = os.getenv("VISION_API_KEY", "")
BASE_URL = os.getenv("VISION_API_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
MAX_TOKENS = int(os.getenv("VISION_MAX_TOKENS", "4096"))

VISION_MODELS = [
    "wanx-v1",
    "qwen3.5-omni-plus-2026-03-15",
    "qwen3.5-omni-plus",
]

MIME_MAP = {
    ".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png",
    ".gif": "gif", ".webp": "webp", ".bmp": "bmp",
    ".tiff": "tiff", ".tif": "tiff",
}


def file_to_data_uri(image_path: str) -> str:
    p = Path(image_path).resolve()
    if not p.exists():
        raise FileNotFoundError(f"Image not found: {p}")
    ext = p.suffix.lower()
    mime = MIME_MAP.get(ext, "jpeg")
    data = p.read_bytes()
    encoded = base64_encode(data)
    return f"data:image/{mime};base64,{encoded}"


def base64_encode(data: bytes) -> str:
    import base64
    return base64.b64encode(data).decode("ascii")


async def call_vision_api(data_uri: str, question: str, client: httpx.AsyncClient) -> str:
    last_error = None
    for model in VISION_MODELS:
        try:
            payload = {
                "model": model,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": data_uri}},
                        {"type": "text", "text": question},
                    ],
                }],
                "stream": False,
                "max_tokens": MAX_TOKENS,
            }
            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            }
            url = f"{BASE_URL.rstrip('/')}/chat/completions"
            resp = await client.post(url, json=payload, headers=headers, timeout=120.0)

            if resp.status_code >= 400:
                body = resp.text[:500]
                if resp.status_code in (404, 503, 429) or "quota" in body.lower():
                    last_error = f"[{model}] API {resp.status_code}, trying next model"
                    continue
                raise RuntimeError(f"API {resp.status_code}: {body}")

            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if content:
                return content
            last_error = f"[{model}] empty response, trying next model"

        except httpx.TimeoutException:
            last_error = f"[{model}] timeout, trying next model"
        except Exception as e:
            if "FileNotFoundError" in type(e).__name__:
                raise
            last_error = f"[{model}] {e}"

        if len(VISION_MODELS) > 1:
            await asyncio.sleep(0.5)

    raise RuntimeError(f"All models unavailable. Last error: {last_error}")


async def main():
    if not API_KEY:
        print("Error: Please set VISION_API_KEY in environment or .env file.", file=sys.stderr)
        sys.exit(1)

    server = Server("mcp-vision")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="describe_image",
                description=(
                    "Analyze image content using a vision model and return a text description. "
                    "Use this tool when you receive an image but your underlying model lacks "
                    "native vision capability. Suitable for: reading text in images, extracting "
                    "table data, interpreting charts, analyzing UI screenshots, photo content, etc. "
                    "[中文] 使用视觉模型分析图片内容并返回文字描述。"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "image_path": {
                            "type": "string",
                            "description": (
                                "Absolute path to the image file, "
                                "e.g. /home/user/photo.png or C:\\Users\\name\\Desktop\\photo.png"
                            ),
                        },
                        "question": {
                            "type": "string",
                            "description": (
                                "Question to ask about the image. "
                                "Defaults to a detailed description if not provided."
                            ),
                        },
                    },
                    "required": ["image_path"],
                },
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name != "describe_image":
            return [TextContent(type="text", text=f"Unknown tool: {name}", isError=True)]

        image_path = arguments.get("image_path", "")
        question = arguments.get("question", "") or (
            "Please describe this image in detail, including all text, numbers, "
            "colors, shapes, layout, and other specifics."
        )

        try:
            data_uri = file_to_data_uri(image_path)
        except FileNotFoundError as e:
            return [TextContent(type="text", text=str(e), isError=True)]
        except Exception as e:
            return [TextContent(type="text", text=f"Failed to read image: {e}", isError=True)]

        async with httpx.AsyncClient() as client:
            try:
                desc = await call_vision_api(data_uri, question, client)
                return [TextContent(type="text", text=desc)]
            except Exception as e:
                return [TextContent(type="text", text=f"Vision API call failed: {e}", isError=True)]

    async with stdio_server() as (reader, writer):
        await server.run(reader, writer, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
