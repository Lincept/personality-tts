from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class LogConfig:
    level: str = "INFO"
    save: bool = True
    save_dest: str = "log"

@dataclass
class WSConnectConfig:
    base_url: str
    headers: Dict[str, Any]

@dataclass
class DoubaoRealTimeConfig:
    asr: Dict[str, Any]
    tts: Dict[str, Any]
    dialog: Dict[str, Any]

@dataclass
class AudioConfig:
    format: str
    bit_size: Any
    channels: int
    sample_rate: int
    chunk: int

@dataclass
class MemoryMeta:
    collection: str = "test1"
    user_id: str = "1"
    assistant_id: str = "111"
    user_name: str = "User"
    assistant_name: str = "Assistant"

@dataclass
class VikingConfig:
    ak: str
    sk: str

@dataclass
class Mem0Config:
    llm: Dict[str, Any]
    embedder: Dict[str, Any]
    vector_store: Dict[str, Any]
    graph_store: Optional[Dict[str, Any]] = None
