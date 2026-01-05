"""
转录生成器模块

从音频文件生成转录文本，支持多种语言和并发处理。
"""
import os
from pathlib import Path
from typing import Optional, Dict
import hashlib

from video_processor.exceptions import TranscriptionError
from video_processor.cache import LRUCache, CacheKeyGenerator
from video_processor.logger import get_logger

logger = get_logger(__name__)


class TranscriptGenerator:
    """转录生成器类
    
    从音频文件生成转录文本，支持缓存和并发处理。
    """
    
    def __init__(
        self,
        cache: Optional[LRUCache] = None,
        api_key: Optional[str] = None,
        model: str = "base"
    ):
        """初始化转录生成器
        
        Args:
            cache: LRU 缓存实例（可选）
            api_key: OpenAI API 密钥（可选）
            model: 使用的模型（默认 "base"）
        """
        self.cache = cache
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.key_generator = CacheKeyGenerator()
    
    def generate(self, audio_path: str, language: str = "auto") -> str:
        """生成转录文本
        
        从音频文件生成转录文本，支持缓存。
        
        Args:
            audio_path: 音频文件路径
            language: 语言代码（默认 "auto" 自动检测）
            
        Returns:
            转录文本
            
        Raises:
            TranscriptionError: 转录失败
            FileNotFoundError: 音频文件不存在
        """
        audio_path_obj = Path(audio_path)
        
        if not audio_path_obj.exists():
            logger.error(f"音频文件不存在: {audio_path_obj}")
            raise FileNotFoundError(f"音频文件不存在: {audio_path_obj}")
        
        # 生成缓存键 - 使用原始音频路径和语言
        cache_key = self.key_generator.generate_transcript_key(audio_path)
        
        # 检查缓存
        if self.cache is not None:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.info(f"从缓存返回转录文本: {cached_result[:50]}...")
                return cached_result
        
        try:
            # 调用 Whisper API 生成转录
            transcript = self._transcribe_with_whisper(str(audio_path_obj), language)
            
            # 缓存结果
            if self.cache is not None:
                self.cache.set(cache_key, transcript)
            
            logger.info(f"成功生成转录文本，长度: {len(transcript)}")
            return transcript
        
        except Exception as e:
            logger.error(f"转录生成失败: {e}")
            raise TranscriptionError(f"转录生成失败: {e}")
    
    def _transcribe_with_whisper(self, audio_path: str, language: str = "auto") -> str:
        """使用 Whisper API 生成转录
        
        Args:
            audio_path: 音频文件路径
            language: 语言代码
            
        Returns:
            转录文本
            
        Raises:
            TranscriptionError: 转录失败
        """
        try:
            # 尝试导入 openai
            try:
                import openai
            except ImportError:
                raise TranscriptionError("openai 库未安装，请运行 pip install openai")
            
            # 设置 API 密钥
            if not self.api_key:
                raise TranscriptionError("未设置 OPENAI_API_KEY 环境变量")
            
            openai.api_key = self.api_key
            
            # 打开音频文件
            with open(audio_path, "rb") as audio_file:
                # 调用 Whisper API
                transcript_response = openai.Audio.transcribe(
                    model="whisper-1",
                    file=audio_file,
                    language=language if language != "auto" else None
                )
            
            # 提取转录文本
            transcript = transcript_response.get("text", "")
            
            if not transcript:
                raise TranscriptionError("Whisper API 返回空转录文本")
            
            return transcript
        
        except TranscriptionError:
            raise
        except FileNotFoundError:
            raise TranscriptionError(f"音频文件不存在: {audio_path}")
        except Exception as e:
            raise TranscriptionError(f"Whisper API 调用失败: {str(e)}")
    
    def is_cached(self, audio_path: str) -> bool:
        """检查转录文本是否已缓存
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            是否已缓存
        """
        if self.cache is None:
            return False
        
        cache_key = self.key_generator.generate_transcript_key(str(audio_path))
        return self.cache.get(cache_key) is not None
    
    def get_cached_transcript(self, audio_path: str) -> Optional[str]:
        """获取缓存的转录文本
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            缓存的转录文本，如果不存在则返回 None
        """
        if self.cache is None:
            return None
        
        cache_key = self.key_generator.generate_transcript_key(str(audio_path))
        return self.cache.get(cache_key)
    
    def delete_cached_transcript(self, audio_path: str) -> None:
        """删除缓存的转录文本
        
        Args:
            audio_path: 音频文件路径
        """
        if self.cache is None:
            return
        
        cache_key = self.key_generator.generate_transcript_key(str(audio_path))
        self.cache.delete(cache_key)
        logger.info(f"已删除缓存的转录文本: {audio_path}")
    
    def generate_concurrent(self, audio_paths: list, thread_pool=None) -> Dict[str, str]:
        """并发生成多个音频的转录文本
        
        Args:
            audio_paths: 音频文件路径列表
            thread_pool: 线程池实例（可选）
        
        Returns:
            音频路径到转录文本的映射字典
        """
        results = {}
        
        if thread_pool is None:
            # 如果没有提供线程池，直接顺序生成
            for audio_path in audio_paths:
                try:
                    transcript = self.generate(audio_path)
                    results[audio_path] = transcript
                except Exception as e:
                    logger.error(f"生成 {audio_path} 的转录失败: {e}")
                    results[audio_path] = None
        else:
            # 使用线程池并发生成
            futures = {}
            for audio_path in audio_paths:
                task_id = f"transcribe_{hash(audio_path)}"
                future = thread_pool.submit(task_id, self.generate, audio_path)
                futures[audio_path] = future
            
            # 收集结果
            for audio_path, future in futures.items():
                try:
                    transcript = thread_pool.get_result(f"transcribe_{hash(audio_path)}")
                    results[audio_path] = transcript
                except Exception as e:
                    logger.error(f"生成 {audio_path} 的转录失败: {e}")
                    results[audio_path] = None
        
        return results
