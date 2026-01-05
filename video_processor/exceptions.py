"""
自定义异常类定义
"""


class VideoProcessingError(Exception):
    """基础异常 - 视频处理错误"""
    pass


class DownloadError(VideoProcessingError):
    """下载失败异常"""
    pass


class ExtractionError(VideoProcessingError):
    """音频提取失败异常"""
    pass


class TranscriptionError(VideoProcessingError):
    """转录失败异常"""
    pass


class SummarizationError(VideoProcessingError):
    """总结失败异常"""
    pass


class CacheError(VideoProcessingError):
    """缓存错误异常"""
    pass


class QueueError(VideoProcessingError):
    """队列错误异常"""
    pass


class ThreadPoolError(VideoProcessingError):
    """线程池错误异常"""
    pass
