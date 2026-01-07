"""
编排器模块 - 协调管道执行

编排器是系统的核心组件，负责协调所有处理阶段的执行，
包括视频下载、音频提取、转录生成和总结生成。
"""
import uuid
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from .models import (
    VideoMetadata,
    Task,
    ProcessingResult,
    TaskStatus,
    TaskType,
)
from .downloader import VideoDownloader
from .audio_extractor import AudioExtractor
from .transcript_generator import TranscriptGenerator
from .summary_generator import SummaryGenerator, ModelSelector
from .cache import LRUCache, CacheKeyGenerator
from .queue import MessageQueue
from .thread_pool import ThreadPool
from .logger import get_logger
from .exceptions import (
    VideoProcessingError,
    DownloadError,
    ExtractionError,
    TranscriptionError,
    SummarizationError,
)

logger = get_logger(__name__)


class Orchestrator:
    """
    编排器类
    
    协调管道各阶段的执行，包括：
    - 视频下载
    - 音频提取
    - 转录生成
    - 总结生成
    
    特性：
    - 顺序执行管道阶段
    - 错误处理和重试
    - 缓存支持
    - 消息队列集成
    - 多线程并发处理
    """
    
    def __init__(
        self,
        cache_size: int = 1000,
        max_workers: Optional[int] = None,
        queue_size: int = 10000,
    ):
        """
        初始化编排器
        
        Args:
            cache_size: 缓存大小
            max_workers: 最大工作线程数
            queue_size: 消息队列大小
        """
        # 初始化缓存
        self.cache = LRUCache(max_size=cache_size)
        self.cache_key_generator = CacheKeyGenerator()
        
        # 初始化各个处理器
        self.downloader = VideoDownloader()
        self.audio_extractor = AudioExtractor(cache=self.cache)
        self.transcript_generator = TranscriptGenerator(cache=self.cache)
        self.summary_generator = SummaryGenerator(cache=self.cache)
        self.model_selector = ModelSelector()
        
        # 初始化消息队列和线程池
        self.message_queue = MessageQueue(max_size=queue_size)
        self.thread_pool = ThreadPool(max_workers=max_workers)
        
        # 任务结果存储
        self.results: Dict[str, ProcessingResult] = {}
        self.task_metadata: Dict[str, Dict[str, Any]] = {}
        
        logger.info("编排器初始化完成")
    
    def process_video(self, video_url: str, use_queue: bool = False) -> str:
        """
        处理单个视频
        
        按顺序执行：下载 → 提取音频 → 生成转录 → 生成总结
        
        Args:
            video_url: 视频 URL
            use_queue: 是否使用消息队列（True 为异步，False 为同步）
        
        Returns:
            任务 ID
        
        Raises:
            VideoProcessingError: 如果处理失败
        """
        try:
            # 生成任务 ID
            task_id = str(uuid.uuid4())
            start_time = time.time()
            
            logger.info(f"开始处理视频: {video_url} (任务 ID: {task_id})")
            
            # 记录任务元数据
            self.task_metadata[task_id] = {
                "video_url": video_url,
                "start_time": start_time,
                "status": "processing",
            }
            
            if use_queue:
                # 使用消息队列进行异步处理
                self._enqueue_pipeline_tasks(task_id, video_url)
                logger.info(f"[{task_id}] 任务已入队，等待处理")
            else:
                # 同步处理
                self._process_video_sync(task_id, video_url, start_time)
            
            return task_id
        
        except Exception as e:
            logger.error(f"视频处理失败: {str(e)}")
            if task_id in self.task_metadata:
                self.task_metadata[task_id]["status"] = "failed"
                self.task_metadata[task_id]["error"] = str(e)
            raise VideoProcessingError(f"视频处理失败: {str(e)}")
    
    def _process_video_sync(self, task_id: str, video_url: str, start_time: float) -> None:
        """
        同步处理视频
        
        Args:
            task_id: 任务 ID
            video_url: 视频 URL
            start_time: 开始时间
        """
        # 步骤 1: 下载视频
        logger.info(f"[{task_id}] 步骤 1: 下载视频")
        video_path = self._download_video(task_id, video_url)
        
        # 步骤 2: 提取音频
        logger.info(f"[{task_id}] 步骤 2: 提取音频")
        audio_path = self._extract_audio(task_id, video_path)
        
        # 步骤 3: 生成转录
        logger.info(f"[{task_id}] 步骤 3: 生成转录")
        transcript = self._generate_transcript(task_id, audio_path)
        
        # 步骤 4: 生成总结
        logger.info(f"[{task_id}] 步骤 4: 生成总结")
        summary = self._generate_summary(task_id, transcript)
        
        # 获取视频元数据
        video_metadata = self._get_video_metadata(video_url)
        
        # 创建处理结果
        processing_time = time.time() - start_time
        result = ProcessingResult(
            task_id=task_id,
            video_metadata=video_metadata,
            video_path=video_path,
            audio_path=audio_path,
            transcript=transcript,
            summary=summary,
            processing_time=processing_time,
        )
        
        # 存储结果
        self.results[task_id] = result
        self.task_metadata[task_id]["status"] = "completed"
        self.task_metadata[task_id]["end_time"] = time.time()
        
        logger.info(f"[{task_id}] 视频处理完成，耗时: {processing_time:.2f}s")
    
    def process_batch(self, video_urls: List[str]) -> List[str]:
        """
        批量处理多个视频
        
        Args:
            video_urls: 视频 URL 列表
        
        Returns:
            任务 ID 列表
        """
        task_ids = []
        
        for video_url in video_urls:
            try:
                task_id = self.process_video(video_url)
                task_ids.append(task_id)
            except Exception as e:
                logger.error(f"处理视频失败: {video_url}, 错误: {str(e)}")
                task_ids.append(None)
        
        return task_ids
    
    def get_result(self, task_id: str) -> Optional[ProcessingResult]:
        """
        获取处理结果
        
        Args:
            task_id: 任务 ID
        
        Returns:
            处理结果，如果不存在则返回 None
        """
        return self.results.get(task_id)
    
    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态
        
        Args:
            task_id: 任务 ID
        
        Returns:
            任务状态信息
        """
        if task_id not in self.task_metadata:
            return None
        
        metadata = self.task_metadata[task_id]
        status_info = {
            "task_id": task_id,
            "video_url": metadata.get("video_url"),
            "status": metadata.get("status"),
            "start_time": metadata.get("start_time"),
            "end_time": metadata.get("end_time"),
            "error": metadata.get("error"),
        }
        
        # 如果有处理时间，添加到状态信息
        if "end_time" in metadata and "start_time" in metadata:
            status_info["processing_time"] = (
                metadata["end_time"] - metadata["start_time"]
            )
        
        return status_info
    
    def _download_video(self, task_id: str, video_url: str) -> str:
        """
        下载视频
        
        Args:
            task_id: 任务 ID
            video_url: 视频 URL
        
        Returns:
            视频文件路径
        
        Raises:
            DownloadError: 如果下载失败
        """
        try:
            # 检查缓存
            cached_file = self.downloader.get_cached_file(video_url)
            if cached_file:
                logger.info(f"[{task_id}] 从缓存返回视频: {cached_file}")
                return cached_file
            
            # 下载视频
            video_path = self.downloader.download(video_url)
            logger.info(f"[{task_id}] 视频下载完成: {video_path}")
            
            return video_path
        
        except DownloadError:
            raise
        except Exception as e:
            raise DownloadError(f"视频下载失败: {str(e)}")
    
    def _extract_audio(self, task_id: str, video_path: str) -> str:
        """
        提取音频
        
        Args:
            task_id: 任务 ID
            video_path: 视频文件路径
        
        Returns:
            音频文件路径
        
        Raises:
            ExtractionError: 如果提取失败
        """
        try:
            # 检查缓存
            cached_audio = self.audio_extractor.get_cached_audio(video_path)
            if cached_audio:
                logger.info(f"[{task_id}] 从缓存返回音频: {cached_audio}")
                return cached_audio
            
            # 提取音频
            audio_path = self.audio_extractor.extract(video_path)
            logger.info(f"[{task_id}] 音频提取完成: {audio_path}")
            
            return audio_path
        
        except ExtractionError:
            raise
        except Exception as e:
            raise ExtractionError(f"音频提取失败: {str(e)}")
    
    def _generate_transcript(self, task_id: str, audio_path: str) -> str:
        """
        生成转录文本
        
        Args:
            task_id: 任务 ID
            audio_path: 音频文件路径
        
        Returns:
            转录文本
        
        Raises:
            TranscriptionError: 如果生成失败
        """
        try:
            # 检查缓存
            cached_transcript = self.transcript_generator.get_cached_transcript(audio_path)
            if cached_transcript:
                logger.info(f"[{task_id}] 从缓存返回转录文本")
                return cached_transcript
            
            # 生成转录
            transcript = self.transcript_generator.generate(audio_path)
            logger.info(f"[{task_id}] 转录生成完成，长度: {len(transcript)}")
            
            return transcript
        
        except TranscriptionError:
            raise
        except Exception as e:
            raise TranscriptionError(f"转录生成失败: {str(e)}")
    
    def _generate_summary(self, task_id: str, transcript: str) -> str:
        """
        生成总结
        
        Args:
            task_id: 任务 ID
            transcript: 转录文本
        
        Returns:
            总结文本
        
        Raises:
            SummarizationError: 如果生成失败
        """
        try:
            # 动态选择模型
            model = self.model_selector.select_model(transcript)
            logger.info(f"[{task_id}] 选择模型: {model}")
            
            # 检查缓存
            cached_summary = self.summary_generator.get_cached_summary(transcript, model)
            if cached_summary:
                logger.info(f"[{task_id}] 从缓存返回总结")
                return cached_summary
            
            # 生成总结
            summary = self.summary_generator.generate(transcript, model=model)
            logger.info(f"[{task_id}] 总结生成完成，长度: {len(summary)}")
            
            return summary
        
        except SummarizationError:
            raise
        except Exception as e:
            raise SummarizationError(f"总结生成失败: {str(e)}")
    
    def _get_video_metadata(self, video_url: str) -> VideoMetadata:
        """
        获取视频元数据
        
        Args:
            video_url: 视频 URL
        
        Returns:
            视频元数据
        """
        try:
            info = self.downloader.get_video_info(video_url)
            
            if info:
                return VideoMetadata(
                    url=video_url,
                    title=info.get("title"),
                    duration=info.get("duration"),
                    upload_date=info.get("upload_date"),
                    channel=info.get("uploader"),
                )
            else:
                return VideoMetadata(url=video_url)
        
        except Exception as e:
            logger.warning(f"获取视频元数据失败: {str(e)}")
            return VideoMetadata(url=video_url)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return self.cache.get_stats()
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """获取消息队列统计信息"""
        return self.message_queue.get_stats()
    
    def get_thread_pool_stats(self) -> Dict[str, Any]:
        """获取线程池统计信息"""
        return self.thread_pool.get_stats()
    
    def shutdown(self) -> None:
        """关闭编排器"""
        logger.info("关闭编排器...")
        self.thread_pool.shutdown(wait=True)
        self.message_queue.clear()
        logger.info("编排器已关闭")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.shutdown()

    def _enqueue_pipeline_tasks(self, task_id: str, video_url: str) -> None:
        """
        将管道任务入队到消息队列
        
        按顺序入队：下载 → 提取音频 → 生成转录 → 生成总结
        
        Args:
            task_id: 任务 ID
            video_url: 视频 URL
        """
        try:
            # 入队下载任务
            download_task_id = self.message_queue.enqueue(
                TaskType.DOWNLOAD,
                {
                    "parent_task_id": task_id,
                    "video_url": video_url,
                }
            )
            logger.info(f"[{task_id}] 下载任务已入队: {download_task_id}")
            
            # 记录任务链
            if task_id not in self.task_metadata:
                self.task_metadata[task_id] = {}
            
            self.task_metadata[task_id]["queue_tasks"] = {
                "download": download_task_id,
            }
        
        except Exception as e:
            logger.error(f"入队任务失败: {str(e)}")
            raise VideoProcessingError(f"入队任务失败: {str(e)}")
    
    def process_queue_task(self, task: Task) -> None:
        """
        处理消息队列中的任务
        
        Args:
            task: 消息队列任务
        """
        try:
            parent_task_id = task.input_data.get("parent_task_id")
            
            if task.task_type == TaskType.DOWNLOAD:
                self._process_download_task(task, parent_task_id)
            elif task.task_type == TaskType.EXTRACT:
                self._process_extract_task(task, parent_task_id)
            elif task.task_type == TaskType.TRANSCRIBE:
                self._process_transcribe_task(task, parent_task_id)
            elif task.task_type == TaskType.SUMMARIZE:
                self._process_summarize_task(task, parent_task_id)
            else:
                raise ValueError(f"未知的任务类型: {task.task_type}")
            
            # 标记任务完成
            self.message_queue.mark_completed(task.task_id)
        
        except Exception as e:
            logger.error(f"处理队列任务失败: {str(e)}")
            self.message_queue.mark_failed(task.task_id, str(e))
    
    def _process_download_task(self, task: Task, parent_task_id: str) -> None:
        """处理下载任务"""
        video_url = task.input_data.get("video_url")
        logger.info(f"[{parent_task_id}] 处理下载任务: {video_url}")
        
        try:
            video_path = self._download_video(parent_task_id, video_url)
            
            # 入队提取任务
            extract_task_id = self.message_queue.enqueue(
                TaskType.EXTRACT,
                {
                    "parent_task_id": parent_task_id,
                    "video_path": video_path,
                }
            )
            
            # 更新任务链
            if parent_task_id in self.task_metadata:
                self.task_metadata[parent_task_id]["queue_tasks"]["extract"] = extract_task_id
            
            logger.info(f"[{parent_task_id}] 提取任务已入队: {extract_task_id}")
        
        except Exception as e:
            logger.error(f"[{parent_task_id}] 下载任务失败: {str(e)}")
            raise
    
    def _process_extract_task(self, task: Task, parent_task_id: str) -> None:
        """处理提取任务"""
        video_path = task.input_data.get("video_path")
        logger.info(f"[{parent_task_id}] 处理提取任务: {video_path}")
        
        try:
            audio_path = self._extract_audio(parent_task_id, video_path)
            
            # 入队转录任务
            transcribe_task_id = self.message_queue.enqueue(
                TaskType.TRANSCRIBE,
                {
                    "parent_task_id": parent_task_id,
                    "audio_path": audio_path,
                }
            )
            
            # 更新任务链
            if parent_task_id in self.task_metadata:
                self.task_metadata[parent_task_id]["queue_tasks"]["transcribe"] = transcribe_task_id
            
            logger.info(f"[{parent_task_id}] 转录任务已入队: {transcribe_task_id}")
        
        except Exception as e:
            logger.error(f"[{parent_task_id}] 提取任务失败: {str(e)}")
            raise
    
    def _process_transcribe_task(self, task: Task, parent_task_id: str) -> None:
        """处理转录任务"""
        audio_path = task.input_data.get("audio_path")
        logger.info(f"[{parent_task_id}] 处理转录任务: {audio_path}")
        
        try:
            transcript = self._generate_transcript(parent_task_id, audio_path)
            
            # 入队总结任务
            summarize_task_id = self.message_queue.enqueue(
                TaskType.SUMMARIZE,
                {
                    "parent_task_id": parent_task_id,
                    "transcript": transcript,
                }
            )
            
            # 更新任务链
            if parent_task_id in self.task_metadata:
                self.task_metadata[parent_task_id]["queue_tasks"]["summarize"] = summarize_task_id
            
            logger.info(f"[{parent_task_id}] 总结任务已入队: {summarize_task_id}")
        
        except Exception as e:
            logger.error(f"[{parent_task_id}] 转录任务失败: {str(e)}")
            raise
    
    def _process_summarize_task(self, task: Task, parent_task_id: str) -> None:
        """处理总结任务"""
        transcript = task.input_data.get("transcript")
        logger.info(f"[{parent_task_id}] 处理总结任务")
        
        try:
            summary = self._generate_summary(parent_task_id, transcript)
            
            # 标记父任务完成
            if parent_task_id in self.task_metadata:
                self.task_metadata[parent_task_id]["status"] = "completed"
                self.task_metadata[parent_task_id]["end_time"] = time.time()
            
            logger.info(f"[{parent_task_id}] 总结任务完成")
        
        except Exception as e:
            logger.error(f"[{parent_task_id}] 总结任务失败: {str(e)}")
            raise

    def process_batch_concurrent(self, video_urls: List[str]) -> List[str]:
        """
        并发处理多个视频
        
        支持多个视频的并发处理，每个视频在单独的线程中执行。
        
        Args:
            video_urls: 视频 URL 列表
        
        Returns:
            任务 ID 列表
        """
        task_ids = []
        futures = {}
        
        logger.info(f"开始并发处理 {len(video_urls)} 个视频")
        
        # 为每个视频提交任务到线程池
        for i, video_url in enumerate(video_urls):
            task_id = str(uuid.uuid4())
            task_ids.append(task_id)
            
            # 提交到线程池
            try:
                future = self.thread_pool.submit(
                    task_id,
                    self._process_video_isolated,
                    task_id,
                    video_url
                )
                futures[task_id] = future
                logger.info(f"视频处理任务已提交到线程池: {task_id}")
            except Exception as e:
                logger.error(f"提交任务失败: {str(e)}")
                task_ids[-1] = None
        
        # 等待所有任务完成
        logger.info("等待所有视频处理完成...")
        self.thread_pool.wait_all()
        
        logger.info(f"并发处理完成，共处理 {len([t for t in task_ids if t])} 个视频")
        
        return task_ids
    
    def _process_video_isolated(self, task_id: str, video_url: str) -> None:
        """
        在隔离的线程中处理视频
        
        确保每个视频的处理不会影响其他视频。
        
        Args:
            task_id: 任务 ID
            video_url: 视频 URL
        """
        try:
            start_time = time.time()
            
            logger.info(f"[{task_id}] 在线程中开始处理视频: {video_url}")
            
            # 记录任务元数据
            self.task_metadata[task_id] = {
                "video_url": video_url,
                "start_time": start_time,
                "status": "processing",
                "thread_isolated": True,
            }
            
            # 同步处理视频
            self._process_video_sync(task_id, video_url, start_time)
            
            logger.info(f"[{task_id}] 线程中的视频处理完成")
        
        except Exception as e:
            logger.error(f"[{task_id}] 线程中的视频处理失败: {str(e)}")
            if task_id in self.task_metadata:
                self.task_metadata[task_id]["status"] = "failed"
                self.task_metadata[task_id]["error"] = str(e)
    
    def process_queue_worker(self, worker_id: int, timeout: float = 1.0) -> None:
        """
        消息队列工作线程
        
        从消息队列中获取任务并处理，支持多个工作线程并发处理。
        
        Args:
            worker_id: 工作线程 ID
            timeout: 队列获取超时时间（秒）
        """
        logger.info(f"工作线程 {worker_id} 启动")
        
        while True:
            try:
                # 从队列中获取任务
                task = self.message_queue.dequeue(timeout=timeout)
                
                if task is None:
                    # 队列为空，继续等待
                    continue
                
                logger.info(f"工作线程 {worker_id} 获取任务: {task.task_id}")
                
                # 处理任务
                self.process_queue_task(task)
                
                logger.info(f"工作线程 {worker_id} 完成任务: {task.task_id}")
            
            except KeyboardInterrupt:
                logger.info(f"工作线程 {worker_id} 被中断")
                break
            except Exception as e:
                logger.error(f"工作线程 {worker_id} 出错: {str(e)}")
                continue
    
    def start_queue_workers(self, num_workers: int = 2) -> List[str]:
        """
        启动消息队列工作线程
        
        Args:
            num_workers: 工作线程数
        
        Returns:
            工作线程任务 ID 列表
        """
        worker_task_ids = []
        
        logger.info(f"启动 {num_workers} 个工作线程")
        
        for i in range(num_workers):
            worker_id = str(uuid.uuid4())
            
            try:
                future = self.thread_pool.submit(
                    worker_id,
                    self.process_queue_worker,
                    i
                )
                worker_task_ids.append(worker_id)
                logger.info(f"工作线程 {i} 已启动: {worker_id}")
            except Exception as e:
                logger.error(f"启动工作线程失败: {str(e)}")
        
        return worker_task_ids
    
    def submit_batch_to_queue(self, video_urls: List[str]) -> List[str]:
        """
        将多个视频提交到消息队列进行异步处理
        
        Args:
            video_urls: 视频 URL 列表
        
        Returns:
            任务 ID 列表
        """
        task_ids = []
        
        logger.info(f"将 {len(video_urls)} 个视频提交到消息队列")
        
        for video_url in video_urls:
            try:
                task_id = self.process_video(video_url, use_queue=True)
                task_ids.append(task_id)
            except Exception as e:
                logger.error(f"提交视频失败: {video_url}, 错误: {str(e)}")
                task_ids.append(None)
        
        return task_ids

    def get_result_dict(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取处理结果的字典表示
        
        返回完整的管道输出，包含所有必需字段。
        
        Args:
            task_id: 任务 ID
        
        Returns:
            结果字典，如果不存在则返回 None
        """
        result = self.get_result(task_id)
        
        if result is None:
            logger.warning(f"结果不存在: {task_id}")
            return None
        
        return result.to_dict()
    
    def get_batch_results(self, task_ids: List[str]) -> List[Dict[str, Any]]:
        """
        获取多个任务的处理结果
        
        Args:
            task_ids: 任务 ID 列表
        
        Returns:
            结果字典列表
        """
        results = []
        
        for task_id in task_ids:
            if task_id is None:
                results.append(None)
                continue
            
            result_dict = self.get_result_dict(task_id)
            results.append(result_dict)
        
        return results
    
    def get_all_results(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有处理结果
        
        Returns:
            任务 ID 到结果字典的映射
        """
        all_results = {}
        
        for task_id, result in self.results.items():
            all_results[task_id] = result.to_dict()
        
        return all_results
    
    def get_result_summary(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取结果摘要
        
        返回结果的简化版本，包含关键信息。
        
        Args:
            task_id: 任务 ID
        
        Returns:
            结果摘要字典
        """
        result = self.get_result(task_id)
        
        if result is None:
            return None
        
        return {
            "task_id": result.task_id,
            "video_url": result.video_metadata.url,
            "video_title": result.video_metadata.title,
            "transcript_length": len(result.transcript),
            "summary_length": len(result.summary),
            "processing_time": result.processing_time,
            "created_at": result.created_at.isoformat(),
        }
    
    def export_result_json(self, task_id: str) -> Optional[str]:
        """
        导出结果为 JSON 字符串
        
        Args:
            task_id: 任务 ID
        
        Returns:
            JSON 字符串，如果不存在则返回 None
        """
        import json
        
        result_dict = self.get_result_dict(task_id)
        
        if result_dict is None:
            return None
        
        try:
            return json.dumps(result_dict, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"导出结果为 JSON 失败: {str(e)}")
            return None
    
    def export_batch_results_json(self, task_ids: List[str]) -> Optional[str]:
        """
        导出多个结果为 JSON 字符串
        
        Args:
            task_ids: 任务 ID 列表
        
        Returns:
            JSON 字符串，如果导出失败则返回 None
        """
        import json
        
        results = self.get_batch_results(task_ids)
        
        try:
            return json.dumps(results, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"导出批量结果为 JSON 失败: {str(e)}")
            return None
    
    def save_result_to_file(self, task_id: str, filepath: str) -> bool:
        """
        将结果保存到文件
        
        Args:
            task_id: 任务 ID
            filepath: 文件路径
        
        Returns:
            是否成功保存
        """
        import json
        
        result_json = self.export_result_json(task_id)
        
        if result_json is None:
            logger.error(f"无法导出结果: {task_id}")
            return False
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(result_json)
            
            logger.info(f"结果已保存到文件: {filepath}")
            return True
        
        except Exception as e:
            logger.error(f"保存结果到文件失败: {str(e)}")
            return False
    
    def save_batch_results_to_file(self, task_ids: List[str], filepath: str) -> bool:
        """
        将多个结果保存到文件
        
        Args:
            task_ids: 任务 ID 列表
            filepath: 文件路径
        
        Returns:
            是否成功保存
        """
        import json
        
        results_json = self.export_batch_results_json(task_ids)
        
        if results_json is None:
            logger.error(f"无法导出批量结果")
            return False
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(results_json)
            
            logger.info(f"批量结果已保存到文件: {filepath}")
            return True
        
        except Exception as e:
            logger.error(f"保存批量结果到文件失败: {str(e)}")
            return False
