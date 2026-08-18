"""S5冒烟区分首事件和首文本token。"""

from __future__ import annotations

import sys
from pathlib import Path


TEST_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TEST_ROOT))

from benchmark.runners.sse import smoke_sse  # noqa: E402


class _Response:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def __iter__(self):
        return iter([
            b"event: status\n", b'data: {"message":"working"}\n', b"\n",
            b"event: token\n", b'data: "answer"\n', b"\n",
            b"event: end\n", b'data: {"ok":true}\n', b"\n",
        ])


def test_sse_smoke_uses_first_text_token_for_ttft() -> None:
    times = iter([0.0, 0.1, 0.4, 0.5, 0.6])
    result = smoke_sse(
        "http://example.test/chat/stream",
        "question",
        opener=lambda *_args, **_kwargs: _Response(),
        clock=lambda: next(times),
    )

    assert result["completed"] is True
    assert result["first_event_seconds"] == 0.1
    assert result["ttft_seconds"] == 0.4
    assert result["total_seconds"] == 0.6
