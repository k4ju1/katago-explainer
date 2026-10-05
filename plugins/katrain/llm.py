"""Chat with a large language model: OpenAI-compatible and Anthropic (Claude) APIs.

Only the standard library is used. Replies are streamed; ``stream_chat`` yields
text fragments as they arrive and can be stopped between fragments.
"""
from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request

OPENAI = "openai"
ANTHROPIC = "anthropic"
ANTHROPIC_VERSION = "2023-06-01"

# name, protocol, base URL, default model. The model field stays editable.
PRESETS = [
    ("DeepSeek", OPENAI, "https://api.deepseek.com/v1", "deepseek-chat"),
    ("通义千问 (DashScope)", OPENAI, "https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-plus"),
    ("Kimi (Moonshot)", OPENAI, "https://api.moonshot.cn/v1", "moonshot-v1-32k"),
    ("智谱 GLM", OPENAI, "https://open.bigmodel.cn/api/paas/v4", "glm-4-plus"),
    ("OpenAI", OPENAI, "https://api.openai.com/v1", "gpt-4o"),
    ("Ollama（本机）", OPENAI, "http://localhost:11434/v1", "qwen2.5"),
    ("Claude (Anthropic)", ANTHROPIC, "https://api.anthropic.com", "claude-sonnet-5-5"),
    ("自定义 OpenAI 兼容接口", OPENAI, "", ""),
]


class LLMError(RuntimeError):
    pass


def build_request(config, system, messages):
    """Return (url, headers, body) for one streamed chat request."""
    protocol = config.get("protocol", OPENAI)
    base = (config.get("base_url") or "").strip().rstrip("/")
    model = (config.get("model") or "").strip()
    key = (config.get("api_key") or "").strip()
    if not base or not model:
        raise LLMError("请先在设置里填写大模型的接口地址和模型名称。")
    if not base.startswith(("http://", "https://")):
        raise LLMError("接口地址应以 http:// 或 https:// 开头。")
    try:
        temperature = float(config.get("temperature", 0.5))
        max_tokens = int(config.get("max_tokens", 2000))
    except (TypeError, ValueError):
        temperature, max_tokens = 0.5, 2000
    headers = {"Content-Type": "application/json", "Accept": "text/event-stream",
               "User-Agent": "KataGoExplainer/1.0"}
    turns = [{"role": item["role"], "content": item["content"]} for item in messages
             if item.get("role") in ("user", "assistant") and item.get("content")]
    if protocol == ANTHROPIC:
        if not key:
            raise LLMError("请先在设置里填写 Claude 的 API Key。")
        url = base + ("/messages" if base.endswith("/v1") else "/v1/messages")
        headers.update({"x-api-key": key, "anthropic-version": ANTHROPIC_VERSION})
        body = {"model": model, "max_tokens": max_tokens, "system": system, "messages": turns, "stream": True}
    else:
        url = base + "/chat/completions"
        if key:
            headers["Authorization"] = "Bearer " + key
        body = {"model": model, "stream": True, "temperature": temperature, "max_tokens": max_tokens,
                "messages": [{"role": "system", "content": system}] + turns}
    return url, headers, body


def parse_event(protocol, data):
    """Text carried by one server-sent event payload, or '' if it carries none."""
    if not data or data == "[DONE]":
        return ""
    try:
        event = json.loads(data)
    except json.JSONDecodeError:
        return ""
    if not isinstance(event, dict):
        return ""
    if event.get("type") == "error" or (isinstance(event.get("error"), dict) and "choices" not in event):
        detail = event.get("error") or {}
        raise LLMError("大模型返回错误：" + str(detail.get("message") or detail))
    if protocol == ANTHROPIC:
        if event.get("type") == "content_block_delta":
            delta = event.get("delta") or {}
            if delta.get("type") == "text_delta":
                return delta.get("text") or ""
        return ""
    for choice in event.get("choices") or []:
        delta = choice.get("delta") or {}
        text = delta.get("content")
        if isinstance(text, str) and text:
            return text
    return ""


def _explain_http_error(error):
    try:
        raw = error.read().decode("utf-8", "replace")
    except Exception:
        raw = ""
    detail = raw[:400]
    try:
        payload = json.loads(raw)
        inner = payload.get("error", payload)
        detail = inner.get("message", detail) if isinstance(inner, dict) else str(inner)
    except (json.JSONDecodeError, AttributeError):
        pass
    hints = {401: "API Key 无效或未填写", 403: "没有访问权限", 404: "接口地址或模型名称不对",
             429: "请求过于频繁或余额不足", 400: "请求被拒绝"}
    hint = hints.get(error.code, "服务器错误" if error.code >= 500 else "请求失败")
    return LLMError(f"{hint}（HTTP {error.code}）{'：' + detail if detail else ''}")


def stream_chat(config, system, messages, should_stop=lambda: False, timeout=60):
    """Yield the reply piece by piece. Raises LLMError with a readable message."""
    url, headers, body = build_request(config, system, messages)
    protocol = config.get("protocol", OPENAI)
    request = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                                     headers=headers, method="POST")
    try:
        response = urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.HTTPError as error:
        raise _explain_http_error(error) from None
    except (urllib.error.URLError, socket.timeout, TimeoutError, OSError) as error:
        reason = getattr(error, "reason", error)
        raise LLMError(f"连接不上大模型接口：{reason}") from None
    try:
        with response:
            content_type = response.headers.get("Content-Type", "")
            if "event-stream" not in content_type:
                # Some servers ignore "stream" and answer in one piece.
                payload = json.loads(response.read().decode("utf-8", "replace") or "{}")
                if protocol == ANTHROPIC:
                    text = "".join(part.get("text", "") for part in payload.get("content", [])
                                   if isinstance(part, dict))
                else:
                    text = ((payload.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
                if not text:
                    raise LLMError("大模型没有返回内容。")
                yield text
                return
            for raw in response:
                if should_stop():
                    return
                line = raw.decode("utf-8", "replace").strip()
                if line.startswith("data:"):
                    piece = parse_event(protocol, line[5:].strip())
                    if piece:
                        yield piece
    except (socket.timeout, TimeoutError):
        raise LLMError("大模型响应超时。") from None
    except (OSError, json.JSONDecodeError) as error:
        raise LLMError(f"读取大模型回复时出错：{error}") from None
