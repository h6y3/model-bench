"""OpenAI-compatible chat client for Ollama Cloud. Stdlib only."""
import json
import time
import urllib.error
import urllib.request

from .checks import strip_think


class ClientError(Exception):
    def __init__(self, kind, detail):
        super().__init__(f"{kind}: {detail}")
        self.kind = kind
        self.detail = detail


def _parse_response(payload):
    choices = payload.get("choices")
    if not choices:
        raise ClientError("json", f"no choices in response: {json.dumps(payload)[:200]}")
    msg = choices[0].get("message", {})
    finish = choices[0].get("finish_reason")
    content, inline_reasoning = strip_think(msg.get("content") or "")
    field_reasoning = (msg.get("reasoning") or "").strip()
    parts = [p for p in (field_reasoning, inline_reasoning) if p]
    usage = payload.get("usage") or {}
    return {
        "content": content,
        "reasoning": "\n".join(parts),
        "finish_reason": finish,
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
        },
    }


def chat(base_url, model, messages, *, api_key="ollama", timeout_s=120.0,
         max_tokens=700, temperature=0.2):
    url = base_url.rstrip("/") + "/chat/completions"
    body = json.dumps({"model": model, "messages": messages, "max_tokens": max_tokens,
                       "temperature": temperature}).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    })
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode()[:200]
        except Exception:
            pass
        raise ClientError("http", f"status {e.code} {detail}") from e
    except urllib.error.URLError as e:
        raise ClientError("timeout" if "timed out" in str(e) else "http", str(e)) from e
    except json.JSONDecodeError as e:
        raise ClientError("json", str(e)) from e
    result = _parse_response(payload)
    result["latency_s"] = time.monotonic() - start
    return result