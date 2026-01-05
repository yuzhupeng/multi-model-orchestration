"""
缓存系统单元测试
"""
import pytest
from video_processor.cache import LRUCache, CacheKeyGenerator
from video_processor.exceptions import CacheError


class TestLRUCacheUnit:
    """LRU 缓存单元测试"""
    
    def test_cache_initialization(self):
        """测试缓存初始化"""
        cache = LRUCache(max_size=10)
        assert cache.max_size == 10
        assert cache.size() == 0
    
    def test_cache_set_and_get(self):
        """测试缓存设置和获取"""
        cache = LRUCache(max_size=10)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
    
    def test_cache_miss(self):
        """测试缓存未命中"""
        cache = LRUCache(max_size=10)
        assert cache.get("nonexistent") is None
    
    def test_cache_delete(self):
        """测试缓存删除"""
        cache = LRUCache(max_size=10)
        cache.set("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None
    
    def test_cache_clear(self):
        """测试缓存清空"""
        cache = LRUCache(max_size=10)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.size() == 0
        assert cache.get("key1") is None
    
    def test_cache_max_size_exceeded(self):
        """测试缓存超过最大大小时的驱逐"""
        cache = LRUCache(max_size=3)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # 缓存已满
        assert cache.size() == 3
        
        # 添加新项，应该驱逐最旧的项
        cache.set("key4", "value4")
        assert cache.size() == 3
        assert cache.get("key1") is None  # key1 被驱逐
        assert cache.get("key4") == "value4"
    
    def test_cache_lru_order(self):
        """测试 LRU 顺序"""
        cache = LRUCache(max_size=3)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # 访问 key1，使其成为最近使用的
        cache.get("key1")
        
        # 添加新项，应该驱逐 key2（最近最少使用）
        cache.set("key4", "value4")
        assert cache.get("key2") is None
        assert cache.get("key1") == "value1"
    
    def test_cache_contains(self):
        """测试缓存包含检查"""
        cache = LRUCache(max_size=10)
        cache.set("key1", "value1")
        assert "key1" in cache
        assert "key2" not in cache
    
    def test_cache_stats(self):
        """测试缓存统计"""
        cache = LRUCache(max_size=10)
        cache.set("key1", "value1")
        cache.get("key1")  # 命中
        cache.get("key2")  # 未命中
        
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1
    
    def test_cache_invalid_max_size(self):
        """测试无效的最大大小"""
        with pytest.raises(CacheError):
            LRUCache(max_size=0)
        
        with pytest.raises(CacheError):
            LRUCache(max_size=-1)
    
    def test_cache_ttl_expiration(self):
        """测试 TTL 过期"""
        import time
        cache = LRUCache(max_size=10, ttl=1)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # 等待过期
        time.sleep(1.1)
        assert cache.get("key1") is None


class TestCacheKeyGenerator:
    """缓存键生成器单元测试"""
    
    def test_generate_download_key(self):
        """测试下载键生成"""
        gen = CacheKeyGenerator()
        key1 = gen.generate_download_key("https://youtube.com/watch?v=1")
        key2 = gen.generate_download_key("https://youtube.com/watch?v=1")
        
        # 相同输入应该生成相同的键
        assert key1 == key2
        
        # 不同输入应该生成不同的键
        key3 = gen.generate_download_key("https://youtube.com/watch?v=2")
        assert key1 != key3
    
    def test_generate_extract_key(self):
        """测试提取键生成"""
        gen = CacheKeyGenerator()
        key1 = gen.generate_extract_key("/path/to/video1.mp4")
        key2 = gen.generate_extract_key("/path/to/video1.mp4")
        
        assert key1 == key2
        
        key3 = gen.generate_extract_key("/path/to/video2.mp4")
        assert key1 != key3
    
    def test_generate_transcript_key(self):
        """测试转录键生成"""
        gen = CacheKeyGenerator()
        key1 = gen.generate_transcript_key("/path/to/audio1.mp3")
        key2 = gen.generate_transcript_key("/path/to/audio1.mp3")
        
        assert key1 == key2
        
        key3 = gen.generate_transcript_key("/path/to/audio2.mp3")
        assert key1 != key3
    
    def test_generate_summary_key(self):
        """测试总结键生成"""
        gen = CacheKeyGenerator()
        key1 = gen.generate_summary_key("transcript1", "gpt-3.5")
        key2 = gen.generate_summary_key("transcript1", "gpt-3.5")
        
        assert key1 == key2
        
        # 不同的转录应该生成不同的键
        key3 = gen.generate_summary_key("transcript2", "gpt-3.5")
        assert key1 != key3
        
        # 不同的模型应该生成不同的键
        key4 = gen.generate_summary_key("transcript1", "gpt-4")
        assert key1 != key4
    
    def test_generate_generic_key(self):
        """测试通用键生成"""
        gen = CacheKeyGenerator()
        key1 = gen.generate_key("arg1", "arg2", kwarg1="value1")
        key2 = gen.generate_key("arg1", "arg2", kwarg1="value1")
        
        assert key1 == key2
        
        key3 = gen.generate_key("arg1", "arg2", kwarg1="value2")
        assert key1 != key3
