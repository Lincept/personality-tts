import json
from typing import List, Dict, Any
from mem import BaseMemory

def _to_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _truncate_items(items: List[Dict[str, str]], max_chars: int) -> str:
    if not items:
        return "[]"
    payload = json.dumps(items, ensure_ascii=False)
    if len(payload) <= max_chars:
        return payload

    trimmed = [dict(item) for item in items]
    while trimmed and len(json.dumps(trimmed, ensure_ascii=False)) > max_chars:
        last = trimmed[-1]
        content = last.get("content", "")
        if len(content) > 80:
            last["content"] = content[:-200]
        else:
            trimmed.pop()
    return json.dumps(trimmed, ensure_ascii=False)


async def build_external_rag_payload(
    memory_client: BaseMemory,
    query: str,
    max_items: int = 3,
    max_chars: int = 3800,
) -> str:
    """
    生成ChatRAGText所需的external_rag JSON数组字符串。
    约束：总长度不超过4K字符。
    """
    items: List[Dict[str, str]] = []

    try:
        events = await memory_client.search_events_by_query(query, limit=max_items)
    except Exception:
        events = None

    if events is not None:
        items.append({
            "title": "相关事件",
            "content": _to_text(events),
        })

    if not items:
        return "[]"

    return _truncate_items(items, max_chars)