"""Data models for CRTubeGet."""

import threading
from dataclasses import dataclass, field


@dataclass
class VideoEntry:
    """Represents a single video in a download queue."""
    index: int
    title: str
    url: str
    duration: str = ""
    checked: bool = True
    status: str = "pending"       # pending | downloading | completed | error
    progress: float = 0.0
    speed: str = ""
    eta: str = ""
    error_msg: str = ""
    cancel_event: threading.Event = field(default_factory=threading.Event)
