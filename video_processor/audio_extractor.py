"""
音频提取器模块

从视频文件中提取音频流，支持多种音频格式和并发处理。
"""
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict
import hashlib

from video_processor.exceptions import ExtractionError
from video_processor.cache import LRUCache, CacheKeyGenerator
from video_processor.logger import get_logger

logger = get_logger(__name__)


class AudioExtractor:
    """音频提取器类
    
    从视频文件中提取音频，支持缓存和并发处理。
    """
    
    def __init__(
        self,
        output_dir: Path = Path("data/audio"),
        cache: Optional[LRUCache] = None,
        audio_format: str = "mp3"
    ):
        """初始化音频提取器
        
        Args:
            output_dir: 音频输出目录
            cache: LRU 缓存实例（可选）
            audio_format: 音频格式（默认 mp3）
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cache = cache
        self.audio_format = audio_format
        self.key_generator = CacheKeyGenerator()
    
    def extract(self, video_path: str) -> str:
        """提取音频
        
        从视频文件中提取音频，支持缓存。
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            音频文件路径
            
        Raises:
            AudioExtractionError: 提取失败
            ProcessorFileNotFoundError: 视频文件不存在
        """
        # 保存原始路径用于缓存键生成
        original_video_path = video_path
        video_path_obj = Path(video_path)
        
        if not video_path_obj.exists():
            logger.error(f"视频文件不存在: {video_path_obj}")
            raise FileNotFoundError(f"视频文件不存在: {video_path_obj}")
        
        # 生成缓存键 - 使用原始视频路径
        cache_key = self.key_generator.generate_extract_key(original_video_path)
        
        # 检查缓存
        if self.cache is not None:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.info(f"从缓存返回音频: {cached_result}")
                return cached_result
        
        # 生成输出文件路径
        video_hash = hashlib.md5(original_video_path.encode()).hexdigest()
        audio_file = self.output_dir / f"{video_hash}.{self.audio_format}"
        
        try:
            # 使用 ffmpeg 提取音频
            self._extract_with_ffmpeg(str(video_path_obj), str(audio_file))
            
            # 缓存结果
            if self.cache is not None:
                self.cache.set(cache_key, str(audio_file))
            
            logger.info(f"成功提取音频: {audio_file}")
            return str(audio_file)
        
        except Exception as e:
            logger.error(f"音频提取失败: {e}")
            raise ExtractionError(f"音频提取失败: {e}")
    
    def _extract_with_ffmpeg(self, video_path: str, audio_path: str) -> None:
        """使用 ffmpeg 提取音频
        
        Args:
            video_path: 视频文件路径
            audio_path: 输出音频文件路径
            
        Raises:
            ExtractionError: 提取失败
        """
        try:
            # 构建 ffmpeg 命令
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-q:a", "0",
                "-map", "a",
                "-y",  # 覆盖输出文件
                audio_path
            ]
            
            # 执行命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 分钟超时
            )
            
            if result.returncode != 0:
                raise ExtractionError(
                    f"ffmpeg 命令失败: {result.stderr}"
                )
        
        except subprocess.TimeoutExpired:
            raise ExtractionError("音频提取超时")
        except FileNotFoundError:
            raise ExtractionError("ffmpeg 未安装或不在 PATH 中")
    
    def is_cached(self, video_path: str) -> bool:
        """检查音频是否已缓存
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            是否已缓存
        """
        if self.cache is None:
            return False
        
        cache_key = self.key_generator.generate_extract_key(str(video_path))
        return self.cache.get(cache_key) is not None
    
    def get_cached_audio(self, video_path: str) -> Optional[str]:
        """获取缓存的音频文件
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            缓存的音频文件路径，如果不存在则返回 None
        """
        if self.cache is None:
            return None
        
        cache_key = self.key_generator.generate_extract_key(str(video_path))
        return self.cache.get(cache_key)
    
    def delete_cached_audio(self, video_path: str) -> None:
        """删除缓存的音频
        
        Args:
            video_path: 视频文件路径
        """
        if self.cache is None:
            return
        
        cache_key = self.key_generator.generate_extract_key(str(video_path))
        self.cache.delete(cache_key)
        logger.info(f"已删除缓存的音频: {video_path}")
    
    def extract_concurrent(self, video_paths: list, thread_pool=None) -> Dict[str, str]:
        """并发提取多个视频的音频
        
        Args:
            video_paths: 视频文件路径列表
            thread_pool: 线程池实例（可选）
        
        Returns:
            视频路径到音频路径的映射字典
        """
        results = {}
        
        if thread_pool is None:
            # 如果没有提供线程池，直接顺序提取
            for video_path in video_paths:
                try:
                    audio_path = self.extract(video_path)
                    results[video_path] = audio_path
                except Exception as e:
                    logger.error(f"提取 {video_path} 的音频失败: {e}")
                    results[video_path] = None
        else:
            # 使用线程池并发提取
            futures = {}
            for video_path in video_paths:
                task_id = f"extract_{hash(video_path)}"
                future = thread_pool.submit(task_id, self.extract, video_path)
                futures[video_path] = future
            
            # 收集结果
            for video_path, future in futures.items():
                try:
                    audio_path = thread_pool.get_result(f"extract_{hash(video_path)}")
                    results[video_path] = audio_path
                except Exception as e:
                    logger.error(f"提取 {video_path} 的音频失败: {e}")
                    results[video_path] = None
        
        return results
