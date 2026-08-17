"""使用标准库执行 HTTP/SSE 冒烟并测量文本 TTFT。"""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from collections.abc import Callable
from typing import Any


def smoke_sse(
    url: str,
    question: str,
    *,
    timeout: float = 120.0,
    opener: Callable[..., Any] = urllib.request.urlopen,
    clock: Callable[[], float] = time.perf_counter,
) -> dict[str, Any]:
    """发起一次SSE请求，保留事件并区分首事件与首文本token。"""

    payload = json.dumps({"question": question, "history": [], "explore": False}).encode()
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
        method="POST",
    )
    started = clock()
    first_event_at = None
    first_text_at = None
    current_event = "message"
    events: list[dict[str, Any]] = []
    completed = False
    http_status = None

    try:
        with opener(request, timeout=timeout) as response:
            http_status = response.status
            for raw_line in response:
                line = raw_line.decode("utf-8").rstrip("\r\n")
                if line.startswith("event:"):
                    current_event = line.split(":", 1)[1].strip()
                elif line.startswith("data:"):
                    now = clock()
                    if first_event_at is None:
                        first_event_at = now
                    raw_data = line.split(":", 1)[1].strip()
                    try:
                        data = json.loads(raw_data)
                    except json.JSONDecodeError:
                        data = raw_data
                    events.append({"type": current_event, "data": data})
                    if current_event == "token" and data and first_text_at is None:
                        first_text_at = now
                    if current_event == "end":
                        completed = bool(isinstance(data, dict) and data.get("ok"))
    except Exception as exc:
        ended = clock()
        return {
            "url": url,
            "http_status": http_status,
            "completed": False,
            "first_event_seconds": None if first_event_at is None else first_event_at - started,
            "ttft_seconds": None if first_text_at is None else first_text_at - started,
            "total_seconds": ended - started,
            "events": events,
            "error": {"type": type(exc).__name__, "message": str(exc)},
        }

    ended = clock()
    return {
        "url": url,
        "http_status": http_status,
        "completed": completed,
        "first_event_seconds": None if first_event_at is None else first_event_at - started,
        "ttft_seconds": None if first_text_at is None else first_text_at - started,
        "total_seconds": ended - started,
        "events": events,
        "error": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("urls", nargs="+")
    parser.add_argument("--question", default="请简要说明你能提供哪些帮助。")
    parser.add_argument("--output")
    args = parser.parse_args()
    results = [smoke_sse(url, args.question) for url in args.urls]
    rendered = json.dumps(results, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "x", encoding="utf-8") as stream:
            stream.write(rendered + "\n")
    print(rendered)
    return 0 if all(result["completed"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
