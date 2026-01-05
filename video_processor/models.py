"""
核心数据模型定义
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskType(str, Enum):
    """任务类型枚举"""
    DOWNLOAD = "download"
    EXTRACT = "extract"
    TRANSCRIBE = "transcribe"
    SUMMARIZE = "summarize"


@dataclass
class VideoMetadata:
    """视频元数据"""
    url: str
    title: Optional[str] = None
    duration: Optional[int] = None  # 秒
    platform: Optional[str] = None  # "youtube" 或 "bilibili"
    upload_date: Optional[str] = None
    channel: Optional[str] = None


@dataclass
class Task:
    """处理任务"""
    task_id: str
    task_type: TaskType
    input_data: Dict[str, Any]
    retry_count: int = 0
    max_retries: int = 3
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    error_message: Optional[str] = None


@dataclass
class ProcessingResult:
    """处理结果"""
    task_id: str
    video_metadata: VideoMetadata
    video_path: str
    audio_path: str
    transcript: str
    summary: str
    processing_time: float  # 秒
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "video_metadata": {
                "url": self.video_metadata.url,
                "title": self.video_metadata.title,
                "duration": self.video_metadata.duration,
                "platform": self.video_metadata.platform,
                "upload_date": self.video_metadata.upload_date,
                "channel": self.video_metadata.channel,
            },
            "video_path": self.video_path,
            "audio_path": self.audio_path,
            "transcript": self.transcript,
            "summary": self.summary,
            "processing_time": self.processing_time,
            "created_at": self.created_at.isoformat(),
        }
