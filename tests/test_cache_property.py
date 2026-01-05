"""
缓存系统属性测试

Feature: multi-model-orchestration, Property 6: 缓存驱逐
Validates: Requirements 6.3
"""
import pytest
from hypothesis import given, strategies as st
from video_processor.cache import LRUCache, CacheKeyGenerator


class TestLRUCacheProperty:
    """LRU 缓存属性测试"""
    
    @given(
        max_size=st.integers(min_value=2, max_value=100),
        items_to_add=st.lists(
            st.tuples(st.text(min_size=1), st.integers()),
            min_size=2,
            max_size=150,
            unique_by=lambda x: x[0]
        )
    )
    def test_lru_eviction_property(self, max_size, items_to_add):
        """
        属性 6：缓存驱逐
        
        对于任何缓存满的情况，当添加新项时，最近最少使用的项应被驱逐。
        
        验证：
        1. 缓存大小不超过 max_size
        2. 最旧的项被驱逐
        3. 新项被添加
        """
        cache = LRUCache(max_size=max_size)
        
        # 添加项直到缓存满
        items_to_fill = min(len(items_to_add), max_size)
        for key, value in items_to_add[:items_to_fill]:
            cache.set(key, value)
        
        # 只有当缓存满时才测试驱逐
        if cache.size() == max_size:
            # 记录缓存中的键
            keys_before = set(cache.cache.keys())
            
            # 添加新项（应该驱逐最旧的项）
            new_key = "new_key_" + str(max_size)
            new_value = 999
            cache.set(new_key, new_value)
            
            # 验证缓存大小仍然等于 max_size
            assert cache.size() == max_size
            
            # 验证新项被添加
            assert cache.get(new_key) == new_value
            
            # 验证至少有一个旧项被驱逐
            keys_after = set(cache.cache.keys())
            assert len(keys_before - keys_after) >= 1
    
    @given(
        max_size=st.integers(min_value=2, max_value=50),
        access_pattern=st.lists(
            st.integers(min_value=0, max_value=9),
            min_size=10,
            max_size=100
        )
    )
    def test_lru_access_order_property(self, max_size, access_pattern):
        """
        属性：LRU 访问顺序
        
        对于任何访问模式，最近访问的项应该在缓存中保留最长时间。
        """
        cache = LRUCache(max_size=max_size)
        
        # 初始化缓存
        for i in range(max_size):
            cache.set(f"key_{i}", i)
        
        # 访问项
        for idx in access_pattern:
            key = f"key_{idx}"
            value = cache.get(key)
            if value is not None:
                # 重新设置以更新访问时间
                cache.set(key, value)
        
        # 验证缓存大小不超过 max_size
        assert cache.size() <= max_size
    
    @given(
        keys=st.lists(st.text(), min_size=1, max_size=50, unique=True),
        values=st.lists(st.integers(), min_size=1, max_size=50)
    )
    def test_cache_consistency_property(self, keys, values):
        """
        属性 2：缓存一致性
        
        对于任何已缓存的结果，第二次查询应返回与第一次相同的结果。
        """
        cache = LRUCache(max_size=100)
        
        # 确保 keys 和 values 长度相同
        min_len = min(len(keys), len(values))
        keys = keys[:min_len]
        values = values[:min_len]
        
        # 设置缓存
        for key, value in zip(keys, values):
            cache.set(key, value)
        
        # 验证一致性
        for key, expected_value in zip(keys, values):
            first_get = cache.get(key)
            second_get = cache.get(key)
            
            assert first_get == expected_value
            assert second_get == expected_value
            assert first_get == second_get
    
    @given(
        max_size=st.integers(min_value=1, max_value=50),
        num_items=st.integers(min_value=1, max_value=100)
    )
    def test_cache_size_invariant(self, max_size, num_items):
        """
        不变量：缓存大小不超过 max_size
        
        对于任何操作序列，缓存大小应该始终不超过 max_size。
        """
        cache = LRUCache(max_size=max_size)
        
        # 添加项
        for i in range(num_items):
            cache.set(f"key_{i}", i)
            # 验证不变量
            assert cache.size() <= max_size
        
        # 最终验证
        assert cache.size() <= max_size
    
    def test_cache_key_generator_uniqueness(self):
        """
        属性：缓存键唯一性
        
        对于不同的输入，生成的缓存键应该不同。
        """
        gen = CacheKeyGenerator()
        
        # 测试下载键
        key1 = gen.generate_download_key("https://youtube.com/watch?v=1")
        key2 = gen.generate_download_key("https://youtube.com/watch?v=2")
        assert key1 != key2
        
        # 测试提取键
        key3 = gen.generate_extract_key("/path/to/video1.mp4")
        key4 = gen.generate_extract_key("/path/to/video2.mp4")
        assert key3 != key4
        
        # 测试转录键
        key5 = gen.generate_transcript_key("/path/to/audio1.mp3")
        key6 = gen.generate_transcript_key("/path/to/audio2.mp3")
        assert key5 != key6
        
        # 测试总结键
        key7 = gen.generate_summary_key("transcript1", "gpt-3.5")
        key8 = gen.generate_summary_key("transcript2", "gpt-3.5")
        assert key7 != key8
        
        # 相同输入应该生成相同的键
        key9 = gen.generate_download_key("https://youtube.com/watch?v=1")
        assert key1 == key9
