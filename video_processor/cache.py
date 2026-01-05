"""
缓存系统 - LRU 缓存实现
"""
import hashlib
import time
from typing import Any, Optional, Dict
from collections import OrderedDict
from threading import Lock

from .logger import get_logger
from .exceptions import CacheError

logger = get_logger(__name__)


class LRUCache:
    """
    LRU (Least Recently Used) 缓存实现
    
    特性：
    - 支持最大容量限制
    - 自动驱逐最近最少使用的项
    - 线程安全
    - 支持 TTL (Time To Live)
    """
    
    def __init__(self, max_size: int = 1000, ttl: Optional[int] = None):
        """
        初始化 LRU 缓存
        
        Args:
            max_size: 最大缓存项数
            ttl: 缓存过期时间（秒），None 表示不过期
        """
        if max_size <= 0:
            raise CacheError("max_size 必须大于 0")
        
        self.max_size = max_size
        self.ttl = ttl
        self.cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self.lock = Lock()
        self.hits = 0
        self.misses = 0
    
    def _generate_key(self, *args, **kwargs) -> str:
        """
        生成缓存键
        
        Args:
            *args: 位置参数
            **kwargs: 关键字参数
        
        Returns:
            缓存键
        """
        key_str = str((args, sorted(kwargs.items())))
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _is_expired(self, timestamp: float) -> bool:
        """
        检查缓存项是否过期
        
        Args:
            timestamp: 缓存项的时间戳
        
        Returns:
            是否过期
        """
        if self.ttl is None:
            return False
        return time.time() - timestamp > self.ttl
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
        
        Returns:
            缓存值，如果不存在或已过期则返回 None
        """
        with self.lock:
            if key not in self.cache:
                self.misses += 1
                logger.debug(f"缓存未命中: {key}")
                return None
            
            value, timestamp = self.cache[key]
            
            # 检查是否过期
            if self._is_expired(timestamp):
                del self.cache[key]
                self.misses += 1
                logger.debug(f"缓存已过期: {key}")
                return None
            
            # 移到末尾（最近使用）
            self.cache.move_to_end(key)
            self.hits += 1
            logger.debug(f"缓存命中: {key}")
            return value
    
    def set(self, key: str, value: Any) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
        
        Raises:
            CacheError: 如果缓存操作失败
        """
        with self.lock:
            try:
                # 如果键已存在，删除它
                if key in self.cache:
                    del self.cache[key]
                
                # 如果缓存满，驱逐最近最少使用的项
                if len(self.cache) >= self.max_size:
                    lru_key, _ = self.cache.popitem(last=False)
                    logger.debug(f"驱逐 LRU 项: {lru_key}")
                
                # 添加新项
                self.cache[key] = (value, time.time())
                logger.debug(f"缓存设置: {key}")
            except Exception as e:
                raise CacheError(f"缓存设置失败: {str(e)}")
    
    def delete(self, key: str) -> bool:
        """
        删除缓存项
        
        Args:
            key: 缓存键
        
        Returns:
            是否成功删除
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                logger.debug(f"缓存删除: {key}")
                return True
            return False
    
    def clear(self) -> None:
        """清空所有缓存"""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
            logger.info("缓存已清空")
    
    def size(self) -> int:
        """获取当前缓存大小"""
        with self.lock:
            return len(self.cache)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        with self.lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0
            
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": f"{hit_rate:.2f}%",
                "total_requests": total,
            }
    
    def __len__(self) -> int:
        """获取缓存大小"""
        return self.size()
    
    def __contains__(self, key: str) -> bool:
        """检查键是否在缓存中"""
        with self.lock:
            return key in self.cache


class CacheKeyGenerator:
    """缓存键生成器"""
    
    @staticmethod
    def generate_download_key(url: str) -> str:
        """生成下载缓存键"""
        return hashlib.md5(f"download:{url}".encode()).hexdigest()
    
    @staticmethod
    def generate_extract_key(video_path: str) -> str:
        """生成提取缓存键"""
        return hashlib.md5(f"extract:{video_path}".encode()).hexdigest()
    
    @staticmethod
    def generate_transcript_key(audio_path: str) -> str:
        """生成转录缓存键"""
        return hashlib.md5(f"transcript:{audio_path}".encode()).hexdigest()
    
    @staticmethod
    def generate_summary_key(transcript: str, model: str = "default") -> str:
        """生成总结缓存键"""
        key_str = f"summary:{transcript}:{model}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    @staticmethod
    def generate_key(*args, **kwargs) -> str:
        """生成通用缓存键"""
        key_str = str((args, sorted(kwargs.items())))
        return hashlib.md5(key_str.encode()).hexdigest()
