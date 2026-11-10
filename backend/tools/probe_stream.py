"""Manual end-to-end probe for the NEXUS SSE endpoint.

Usage:  python tools/probe_stream.py "your question here"
"""

from __future__ import annotations

import json
import sys

import httpx

BASE = "http://127.0.0.1:8000"


def main() -> int:
    question = " ".join(sys.argv[1:]) or "What are the latest developments in renewable energy?"
    payload = {"message": question, "run_id": "probe-run-1"}

    tool_calls = 0
    events: list[str] = []
    final_text = ""

    with httpx.Client(timeout=300.0) as client:
        with client.stream(
            "POST",
            f"{BASE}/api/chat/stream",
            json=payload,
            headers={"Accept": "text/event-stream"},
        ) as response:
            print(f"HTTP {response.status_code} {response.headers.get('content-type')}")
            if response.status_code != 200:
                print(response.read().decode()[:2000])
                return 1

            event_name = ""
            data_lines: list[str] = []
            for line in response.iter_lines():
                if line.startswith(":"):
                    continue
                if line.startswith("event:"):
                    event_name = line[6:].strip()
                elif line.startswith("data:"):
                    data_lines.append(line[5:].strip())
                elif line == "":
                    if data_lines:
                        raw = "\n".join(data_lines)
                        data_lines = []
                        try:
                            payload_obj = json.loads(raw)
                        except json.JSONDecodeError:
                            payload_obj = {"raw": raw}
                        events.append(event_name)
                        _print_event(event_name, payload_obj)
                        if event_name == "tool_call":
                            tool_calls += 1
                        if event_name == "final_answer":
                            final_text = payload_obj.get("data", {}).get("content", "")
                        event_name = ""

    print("\n" + "=" * 78)
    print(f"events      : {len(events)}")
    print(f"tool calls  : {tool_calls}")
    print(f"final chars : {len(final_text)}")
    print("=" * 78)
    print(final_text[:3000])
    return 0 if tool_calls > 0 else 2


def _print_event(name: str, obj: dict) -> None:
    data = obj.get("data", {})
    detail = (obj.get("detail") or "")[:150]
    title = obj.get("title", "")
    extra = ""
    if name == "tool_call":
        extra = f" args={data.get('args')}"
    elif name == "tool_result":
        extra = f" results={data.get('result_count')} ok={data.get('ok')} {data.get('duration_ms')}ms"
    elif name == "token":
        extra = f" +{len(data.get('text',''))}ch"
    elif name == "final_answer":
        extra = f" {len(data.get('content',''))} chars"
    elif name == "agent_completed":
        extra = (
            f" iterations={data.get('iterations')} tool_calls={data.get('tool_calls')}"
            f" sources={data.get('source_count')} {data.get('duration_ms')}ms"
        )
    print(f"[{name:16}] {title} | {detail}{extra}")


if __name__ == "__main__":
    raise SystemExit(main())
