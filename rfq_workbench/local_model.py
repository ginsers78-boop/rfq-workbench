"""The only model HTTP transport: fixed loopback, no paid/external provider."""
import json
import time
import urllib.error
import urllib.request

from .errors import ExtractionError, OutputLimitError

MODEL = "qwen3.5:9b"


def chat(messages: list[dict], schema: dict, model: str = MODEL) -> tuple[str, float]:
    text_only = [{key: value for key, value in message.items() if key != "images"} for message in messages]
    if len(json.dumps({"messages": text_only, "format": schema}, ensure_ascii=False).encode("utf-8")) > 22_000:
        raise ExtractionError("The prompt and configuration exceed the local model input budget.")
    body = {"model": model, "stream": False, "think": False, "format": schema,
            "options": {"temperature": 0, "num_ctx": 32768, "num_predict": 8192}, "messages": messages}
    started = time.perf_counter()
    request = urllib.request.Request("http://127.0.0.1:11434/api/chat", data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=240) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        try:
            detail = json.loads(error.read(4096)).get("error", "The model service rejected the request.")
        except (ValueError, AttributeError):
            detail = "The model service rejected the request."
        raise ExtractionError(f"Local model returned HTTP {error.code}: {detail}") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ExtractionError("The local Ollama service is unavailable or exceeded the four-minute model-call timeout.") from None
    except ValueError:
        raise ExtractionError("The local model service returned invalid JSON.") from None
    if isinstance(payload, dict) and payload.get("done_reason") == "length":
        raise OutputLimitError("The model reached its output limit. No partial output was accepted.")
    if not isinstance(payload, dict) or payload.get("done") is not True:
        raise ExtractionError("The local model did not complete its response. No partial output was accepted.")
    try:
        content = payload["message"]["content"]
        if not isinstance(content, str):
            raise ValueError()
    except (KeyError, TypeError, ValueError):
        raise ExtractionError("The local model response envelope is invalid.") from None
    return content, round(time.perf_counter() - started, 2)
