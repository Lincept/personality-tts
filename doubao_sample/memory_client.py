import asyncio
import json
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests
from volcenginesdkcore.signv4 import SignerV4


class VikingDBMemoryException(Exception):
    def __init__(self, code: int, request_id: str, message: Optional[str] = None):
        self.code = code
        self.request_id = request_id
        self.message = f"{message}, code:{self.code}，request_id:{self.request_id}"

    def __str__(self) -> str:
        return self.message


class VikingDBMemoryService:
    """Viking 记忆库 API 的最小封装（SearchMemory / AddSession / Ping）。

    说明：
    - 鉴权方式为 AK/SK + SignV4
    - 默认 host/region 与官方文档一致
    """

    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not hasattr(VikingDBMemoryService, "_instance"):
            with VikingDBMemoryService._instance_lock:
                if not hasattr(VikingDBMemoryService, "_instance"):
                    VikingDBMemoryService._instance = object.__new__(cls)
        return VikingDBMemoryService._instance

    def __init__(
        self,
        host: str = "api-knowledgebase.mlp.cn-beijing.volces.com",
        region: str = "cn-beijing",
        ak: str = "",
        sk: str = "",
        sts_token: str = "",
        scheme: str = "https",
        timeout: int = 30,
        service: str = "air",
    ) -> None:
        self.host = host
        self.region = region
        self.ak = ak
        self.sk = sk
        self.sts_token = sts_token
        self.scheme = scheme
        self.timeout = timeout
        self.service = service

        if not self.ak or not self.sk:
            raise ValueError("ak/sk is required")

        try:
            self.ping()
        except Exception as e:
            raise VikingDBMemoryException(1000028, "missed", "ping failed") from e

    def _request(self, method: str, path: str, body_obj: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.scheme}://{self.host}{path}"
        body = json.dumps(body_obj or {}, ensure_ascii=False)

        headers: Dict[str, str] = {
            "Host": self.host,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Traffic-Source": "SDK",
        }

        SignerV4.sign(
            path=path,
            method=method.upper(),
            headers=headers,
            body=body,
            post_params=None,
            query={},
            ak=self.ak,
            sk=self.sk,
            region=self.region,
            service=self.service,
            session_token=self.sts_token or None,
        )

        resp = requests.request(method=method.upper(), url=url, headers=headers, data=body, timeout=self.timeout)
        try:
            data = resp.json()
        except Exception:
            raise VikingDBMemoryException(resp.status_code, "missed", resp.text)

        if resp.status_code != 200:
            raise VikingDBMemoryException(
                int(data.get("code", resp.status_code)),
                str(data.get("request_id", "missed")),
                str(data.get("message", resp.text)),
            )

        code = data.get("code")
        if code not in (None, 0, "0"):
            raise VikingDBMemoryException(
                int(code) if str(code).isdigit() else 1000028,
                str(data.get("request_id", "missed")),
                str(data.get("message", "unknown error")),
            )

        return data

    def ping(self) -> Dict[str, Any]:
        return self._request("GET", "/api/memory/ping", {})

    def search_memory(
        self,
        collection_name: str,
        query: str,
        filter: Dict[str, Any],
        limit: int = 3,
    ) -> Dict[str, Any]:
        params = {
            "collection_name": collection_name,
            "query": query,
            "limit": limit,
            "filter": filter,
        }
        return self._request("POST", "/api/memory/search", params)

    def add_session(
        self,
        collection_name: str,
        session_id: str,
        messages: Any,
        metadata: Dict[str, Any],
        profiles: Optional[Any] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "collection_name": collection_name,
            "session_id": session_id,
            "messages": messages,
            "metadata": metadata,
        }
        if profiles is not None:
            params["profiles"] = profiles

        return self._request("POST", "/api/memory/session/add", params)


@dataclass
class MemorySettings:
    enable: bool
    collection_name: str
    user_id: str
    assistant_id: str
    memory_types: List[str]
    ak: str = ""
    sk: str = ""
    limit: int = 3
    transition_words: str = "根据你的历史记录："


def _extract_text(payload: Any) -> Optional[str]:
    if payload is None:
        return None

    if isinstance(payload, str):
        text = payload.strip()
        return text or None

    if isinstance(payload, dict):
        for key in ["text", "content", "query", "asr_text", "utterance", "message"]:
            val = payload.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()

        # 有些协议会把文字放在嵌套字段里
        for key in ["result", "data", "payload"]:
            val = payload.get(key)
            if isinstance(val, dict):
                nested = _extract_text(val)
                if nested:
                    return nested

    return None


class MemoryClient:
    def __init__(self, settings: MemorySettings):
        self.settings = settings
        self._service: Optional[VikingDBMemoryService] = None

    def _get_service(self) -> VikingDBMemoryService:
        if self._service is not None:
            return self._service

        ak = os.environ.get("VOLC_ACCESSKEY", "").strip() or (self.settings.ak or "").strip()
        sk = os.environ.get("VOLC_SECRETKEY", "").strip() or (self.settings.sk or "").strip()
        if not ak or not sk:
            raise ValueError("缺少环境变量 VOLC_ACCESSKEY / VOLC_SECRETKEY（用于 Viking 记忆库鉴权）")

        self._service = VikingDBMemoryService(ak=ak, sk=sk)
        return self._service

    def search_memories_sync(self, query: str) -> List[Tuple[float, Any]]:
        if not self.settings.enable:
            return []

        query = (query or "").strip()
        if not query:
            return []

        filter_params: Dict[str, Any] = {}
        if self.settings.user_id:
            filter_params["user_id"] = [self.settings.user_id]
        if self.settings.assistant_id:
            filter_params["assistant_id"] = [self.settings.assistant_id]
        if self.settings.memory_types:
            filter_params["memory_type"] = list(self.settings.memory_types)

        svc = self._get_service()
        resp = svc.search_memory(
            collection_name=self.settings.collection_name,
            query=query,
            filter=filter_params,
            limit=self.settings.limit,
        )

        results: List[Tuple[float, Any]] = []
        data = resp.get("data", {}) if isinstance(resp, dict) else {}
        for item in data.get("result_list", []) or []:
            score = item.get("score", 0.0)
            memory_info = item.get("memory_info")
            if memory_info is None:
                continue
            try:
                score_f = float(score)
            except Exception:
                score_f = 0.0
            results.append((score_f, memory_info))

        # 相关度高的放前面
        results.sort(key=lambda x: x[0], reverse=True)
        return results

    async def search_external_rag(self, query: str) -> Optional[str]:
        """异步检索并组装 external_rag 字符串（JSON 数组）。"""
        if not self.settings.enable:
            return None

        try:
            memories = await asyncio.to_thread(self.search_memories_sync, query)
        except VikingDBMemoryException as e:
            # 1000023: 索引构建中（文档提示首次写入后 3-5 分钟）
            if "1000023" in str(e):
                return None
            raise

        if not memories:
            return None

        items: List[Dict[str, str]] = []
        for score, memory_info in memories:
            title = f"历史记忆（相关度 {score:.3f}）"
            if isinstance(memory_info, dict):
                content = json.dumps(memory_info, ensure_ascii=False)
            else:
                content = str(memory_info)
            items.append({"title": title, "content": content})

        return json.dumps(items, ensure_ascii=False)

    def add_session_sync(self, session_id: str, messages: List[Dict[str, str]]) -> None:
        if not self.settings.enable:
            return
        if not messages:
            return

        svc = self._get_service()
        metadata = {
            "default_user_id": self.settings.user_id,
            "default_assistant_id": self.settings.assistant_id,
            "time": int(time.time() * 1000),
        }
        svc.add_session(
            collection_name=self.settings.collection_name,
            session_id=session_id,
            messages=messages,
            metadata=metadata,
        )

    async def add_session(self, session_id: str, messages: List[Dict[str, str]]) -> None:
        await asyncio.to_thread(self.add_session_sync, session_id, messages)


def extract_user_query_from_asr(payload_msg: Any) -> Optional[str]:
    return _extract_text(payload_msg)


def extract_assistant_text(payload_msg: Any) -> Optional[str]:
    return _extract_text(payload_msg)
