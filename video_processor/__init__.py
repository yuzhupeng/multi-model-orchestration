"""
多模型视频处理编排系统
"""

__version__ = "0.1.0"

from .models import (
    VideoMetadata,
    Task,
    ProcessingResult,
    TaskStatus,
    TaskType,
)
from .exceptions import (
    VideoProcessingError,
    DownloadError,
    ExtractionError,
    TranscriptionError,
    SummarizationError,
    CacheError,
    QueueError,
    ThreadPoolError,
)
from .logger import setup_logger, get_logger
from .summary_generator import SummaryGenerator, ModelSelector
from .orchestrator import Orchestrator

__all__ = [
    "VideoMetadata",
    "Task",
    "ProcessingResult",
    "TaskStatus",
    "TaskType",
    "VideoProcessingError",
    "DownloadError",
    "ExtractionError",
    "TranscriptionError",
    "SummarizationError",
    "CacheError",
    "QueueError",
    "ThreadPoolError",
    "setup_logger",
    "get_logger",
    "SummaryGenerator",
    "ModelSelector",
    "Orchestrator",
]
