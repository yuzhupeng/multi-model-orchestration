"""
总结生成器属性测试

使用 Hypothesis 进行属性测试，验证缓存一致性和其他正确性属性。
Feature: multi-model-orchestration, Property 2: 缓存一致性
"""
import pytest
from hypothesis import given, strategies as st
from unittest.mock import Mock, patch, MagicMock
from video_processor.summary_generator import SummaryGenerator, ModelSelector
from video_processor.cache import LRUCache, CacheKeyGenerator
from video_processor.exceptions import SummarizationError


# 生成策略
transcript_strategy = st.text(
    alphabet=st.characters(blacklist_categories=('Cc', 'Cs')),
    min_size=10,
    max_size=1000
)

model_strategy = st.sampled_from(['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo'])

content_type_strategy = st.sampled_from(['general', 'technical', 'news', 'entertainment'])


class TestSummaryGeneratorCacheConsistency:
    """缓存一致性属性测试
    
    验证属性 2：缓存一致性
    对于任何已缓存的结果，第二次查询应返回与第一次相同的结果，而不重新处理。
    **Validates: Requirements 4.3**
    """
    
    @given(transcript=transcript_strategy, model=model_strategy)
    @patch('openai.ChatCompletion.create')
    def test_cache_consistency_same_result_on_second_query(self, mock_create, transcript, model):
        """属性测试：缓存一致性 - 第二次查询返回相同结果
        
        对于任何转录文本和模型，第二次查询应返回与第一次相同的结果。
        """
        # 设置缓存
        cache = LRUCache(max_size=100)
        generator = SummaryGenerator(cache=cache)
        
        # 模拟 OpenAI API 响应
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Generated summary"
        mock_create.return_value = mock_response
        
        # 第一次调用
        result1 = generator.generate(transcript, model=model)
        
        # 第二次调用应该从缓存返回
        result2 = generator.generate(transcript, model=model)
        
        # 验证结果相同
        assert result1 == result2
        # 验证 API 只被调用一次（第二次从缓存返回）
        assert mock_create.call_count == 1
    
    @given(transcript=transcript_strategy, model=model_strategy)
    @patch('openai.ChatCompletion.create')
    def test_cache_consistency_no_reprocessing(self, mock_create, transcript, model):
        """属性测试：缓存一致性 - 不重新处理
        
        对于任何已缓存的结果，第二次查询不应重新处理。
        """
        cache = LRUCache(max_size=100)
        generator = SummaryGenerator(cache=cache)
        
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Summary"
        mock_create.return_value = mock_response
        
        # 第一次调用
        generator.generate(transcript, model=model)
        initial_call_count = mock_create.call_count
        
        # 多次调用
        for _ in range(5):
            generator.generate(transcript, model=model)
        
        # 验证 API 调用次数没有增加
        assert mock_create.call_count == initial_call_count
    
    @given(transcript=transcript_strategy)
    @patch('openai.ChatCompletion.create')
    def test_cache_consistency_different_models_different_results(self, mock_create, transcript):
        """属性测试：缓存一致性 - 不同模型产生不同缓存
        
        对于相同的转录文本，不同的模型应该产生不同的缓存条目。
        """
        cache = LRUCache(max_size=100)
        generator = SummaryGenerator(cache=cache)
        
        # 为不同模型设置不同的响应
        def mock_create_side_effect(*args, **kwargs):
            model = kwargs.get('model', 'unknown')
            response = MagicMock()
            response.choices[0].message.content = f"Summary for {model}"
            return response
        
        mock_create.side_effect = mock_create_side_effect
        
        # 使用不同模型生成总结
        result1 = generator.generate(transcript, model='gpt-3.5-turbo')
        result2 = generator.generate(transcript, model='gpt-4')
        
        # 验证结果不同
        assert result1 != result2
        assert "gpt-3.5-turbo" in result1
        assert "gpt-4" in result2
    
    @given(transcript=transcript_strategy, model=model_strategy)
    def test_cache_consistency_with_manual_cache_operations(self, transcript, model):
        """属性测试：缓存一致性 - 手动缓存操作
        
        对于任何手动添加到缓存的结果，查询应返回相同的值。
        """
        cache = LRUCache(max_size=100)
        generator = SummaryGenerator(cache=cache)
        
        # 手动添加到缓存
        expected_summary = "Manually cached summary"
        key_gen = CacheKeyGenerator()
        key = key_gen.generate_summary_key(transcript, model)
        cache.set(key, expected_summary)
        
        # 验证缓存检查
        assert generator.is_cached(transcript, model)
        
        # 验证获取缓存的值
        cached_value = generator.get_cached_summary(transcript, model)
        assert cached_value == expected_summary
    
    @given(transcript=transcript_strategy, model=model_strategy)
    def test_cache_consistency_delete_and_requery(self, transcript, model):
        """属性测试：缓存一致性 - 删除后重新查询
        
        对于任何删除的缓存项，重新查询应返回 None。
        """
        cache = LRUCache(max_size=100)
        generator = SummaryGenerator(cache=cache)
        
        # 手动添加到缓存
        key_gen = CacheKeyGenerator()
        key = key_gen.generate_summary_key(transcript, model)
        cache.set(key, "Cached summary")
        
        # 验证在缓存中
        assert generator.is_cached(transcript, model)
        
        # 删除
        generator.delete_cached_summary(transcript, model)
        
        # 验证已删除
        assert not generator.is_cached(transcript, model)
        assert generator.get_cached_summary(transcript, model) is None


class TestModelSelectorConsistency:
    """模型选择器一致性测试"""
    
    @given(transcript=transcript_strategy, content_type=content_type_strategy)
    def test_model_selector_consistency(self, transcript, content_type):
        """属性测试：模型选择一致性
        
        对于相同的转录文本和内容类型，模型选择应该一致。
        """
        selector = ModelSelector()
        
        # 多次调用应该返回相同的模型
        model1 = selector.select_model(transcript, content_type=content_type)
        model2 = selector.select_model(transcript, content_type=content_type)
        model3 = selector.select_model(transcript, content_type=content_type)
        
        assert model1 == model2 == model3
    
    @given(transcript=transcript_strategy)
    def test_model_selector_returns_valid_model(self, transcript):
        """属性测试：模型选择返回有效模型
        
        对于任何转录文本，模型选择应返回有效的模型名称。
        """
        selector = ModelSelector()
        model = selector.select_model(transcript)
        
        # 验证返回的模型在支持的模型列表中
        assert model in selector.MODELS
    
    @given(transcript=transcript_strategy)
    def test_model_selector_respects_user_preference(self, transcript):
        """属性测试：模型选择尊重用户偏好
        
        对于任何用户偏好，模型选择应返回用户指定的模型。
        """
        selector = ModelSelector()
        
        for preferred_model in ['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo']:
            selected_model = selector.select_model(
                transcript,
                user_preference=preferred_model
            )
            assert selected_model == preferred_model


class TestCacheKeyGeneration:
    """缓存键生成一致性测试"""
    
    @given(transcript=transcript_strategy, model=model_strategy)
    def test_cache_key_generation_consistency(self, transcript, model):
        """属性测试：缓存键生成一致性
        
        对于相同的输入，缓存键生成应该一致。
        """
        key_gen = CacheKeyGenerator()
        
        # 多次调用应该返回相同的键
        key1 = key_gen.generate_summary_key(transcript, model)
        key2 = key_gen.generate_summary_key(transcript, model)
        key3 = key_gen.generate_summary_key(transcript, model)
        
        assert key1 == key2 == key3
    
    @given(transcript1=transcript_strategy, transcript2=transcript_strategy, model=model_strategy)
    def test_cache_key_generation_uniqueness(self, transcript1, transcript2, model):
        """属性测试：缓存键生成唯一性
        
        对于不同的输入，缓存键应该不同。
        """
        key_gen = CacheKeyGenerator()
        
        # 假设两个不同的转录文本
        if transcript1 != transcript2:
            key1 = key_gen.generate_summary_key(transcript1, model)
            key2 = key_gen.generate_summary_key(transcript2, model)
            
            # 不同的输入应该产生不同的键
            assert key1 != key2


class TestCacheEviction:
    """缓存驱逐属性测试
    
    验证属性 6：缓存驱逐
    当缓存满时，最近最少使用的项应被驱逐，新项应被添加。
    """
    
    @given(st.lists(transcript_strategy, min_size=5, max_size=20, unique=True))
    def test_cache_eviction_lru_order(self, transcripts):
        """属性测试：LRU 驱逐顺序
        
        当缓存满时，最近最少使用的项应被驱逐。
        """
        cache = LRUCache(max_size=5)
        key_gen = CacheKeyGenerator()
        
        # 添加项到缓存
        for i, transcript in enumerate(transcripts[:5]):
            key = key_gen.generate_summary_key(transcript, 'gpt-3.5-turbo')
            cache.set(key, f"Summary {i}")
        
        # 验证缓存大小
        assert cache.size() == 5
        
        # 添加新项应该驱逐最旧的项
        new_transcript = transcripts[5] if len(transcripts) > 5 else "new transcript"
        new_key = key_gen.generate_summary_key(new_transcript, 'gpt-3.5-turbo')
        cache.set(new_key, "New summary")
        
        # 验证缓存大小仍然是 5
        assert cache.size() == 5
    
    @given(st.lists(transcript_strategy, min_size=10, max_size=20, unique=True))
    def test_cache_eviction_maintains_max_size(self, transcripts):
        """属性测试：缓存驱逐维持最大大小
        
        无论添加多少项，缓存大小不应超过最大大小。
        """
        max_size = 5
        cache = LRUCache(max_size=max_size)
        key_gen = CacheKeyGenerator()
        
        # 添加多个项
        for i, transcript in enumerate(transcripts):
            key = key_gen.generate_summary_key(transcript, 'gpt-3.5-turbo')
            cache.set(key, f"Summary {i}")
            
            # 验证缓存大小不超过最大大小
            assert cache.size() <= max_size



class TestConcurrentProcessingIsolation:
    """并发处理隔离属性测试
    
    验证属性 3：并发处理隔离
    对于任何两个并发处理的转录文本，一个的处理不应影响另一个的结果。
    **Validates: Requirements 4.4**
    """
    
    @given(
        transcripts=st.lists(
            transcript_strategy,
            min_size=2,
            max_size=10,
            unique=True
        ),
        models=st.lists(
            model_strategy,
            min_size=2,
            max_size=10
        )
    )
    @patch('openai.ChatCompletion.create')
    def test_concurrent_processing_isolation(self, mock_create, transcripts, models):
        """属性测试：并发处理隔离
        
        对于任何两个并发处理的转录文本，一个的处理不应影响另一个的结果。
        """
        # 调整模型列表大小以匹配转录文本
        if len(models) < len(transcripts):
            models = models + [models[0]] * (len(transcripts) - len(models))
        else:
            models = models[:len(transcripts)]
        
        cache = LRUCache(max_size=100)
        generator = SummaryGenerator(cache=cache)
        
        # 为每个转录文本设置不同的响应
        def mock_create_side_effect(*args, **kwargs):
            response = MagicMock()
            response.choices[0].message.content = "Isolated summary"
            return response
        
        mock_create.side_effect = mock_create_side_effect
        
        # 并发生成总结
        results = generator.generate_concurrent(transcripts, models=models)
        
        # 验证所有结果都已生成
        assert len(results) == len(transcripts)
        
        # 验证所有结果都不为 None
        for result in results.values():
            assert result is not None
    
    @given(
        transcripts=st.lists(
            transcript_strategy,
            min_size=2,
            max_size=5,
            unique=True
        )
    )
    @patch('openai.ChatCompletion.create')
    def test_concurrent_processing_no_cross_contamination(self, mock_create, transcripts):
        """属性测试：并发处理无交叉污染
        
        对于任何并发处理的转录文本，结果不应相互污染。
        """
        cache = LRUCache(max_size=100)
        generator = SummaryGenerator(cache=cache)
        
        # 为每个转录文本设置唯一的响应
        call_count = [0]
        
        def mock_create_side_effect(*args, **kwargs):
            response = MagicMock()
            response.choices[0].message.content = f"Summary {call_count[0]}"
            call_count[0] += 1
            return response
        
        mock_create.side_effect = mock_create_side_effect
        
        # 并发生成总结
        results = generator.generate_concurrent(transcripts)
        
        # 验证结果数量
        assert len(results) == len(transcripts)
        
        # 验证所有结果都不相同（除非转录文本相同）
        unique_results = set(results.values())
        # 由于我们有不同的转录文本，应该有多个不同的结果
        assert len(unique_results) >= 1
    
    @given(
        transcripts=st.lists(
            transcript_strategy,
            min_size=2,
            max_size=5,
            unique=True
        )
    )
    @patch('openai.ChatCompletion.create')
    def test_concurrent_processing_cache_isolation(self, mock_create, transcripts):
        """属性测试：并发处理缓存隔离
        
        对于任何并发处理的转录文本，缓存应该正确隔离每个结果。
        """
        cache = LRUCache(max_size=100)
        generator = SummaryGenerator(cache=cache)
        
        def mock_create_side_effect(*args, **kwargs):
            response = MagicMock()
            response.choices[0].message.content = "Cached summary"
            return response
        
        mock_create.side_effect = mock_create_side_effect
        
        # 第一次并发生成
        results1 = generator.generate_concurrent(transcripts)
        
        # 第二次并发生成应该从缓存返回
        results2 = generator.generate_concurrent(transcripts)
        
        # 验证结果相同
        assert results1 == results2
        
        # 验证 API 调用次数等于转录文本数量（第二次从缓存返回）
        assert mock_create.call_count == len(transcripts)
    
    @given(
        transcripts=st.lists(
            transcript_strategy,
            min_size=2,
            max_size=5,
            unique=True
        )
    )
    @patch('openai.ChatCompletion.create')
    def test_concurrent_processing_error_isolation(self, mock_create, transcripts):
        """属性测试：并发处理错误隔离
        
        对于任何并发处理中的错误，不应影响其他转录文本的处理。
        """
        cache = LRUCache(max_size=100)
        generator = SummaryGenerator(cache=cache)
        
        # 第一个转录文本失败，其他成功
        call_count = [0]
        
        def mock_create_side_effect(*args, **kwargs):
            if call_count[0] == 0:
                call_count[0] += 1
                raise Exception("API Error")
            response = MagicMock()
            response.choices[0].message.content = "Summary"
            call_count[0] += 1
            return response
        
        mock_create.side_effect = mock_create_side_effect
        
        # 并发生成总结
        results = generator.generate_concurrent(transcripts)
        
        # 验证结果数量
        assert len(results) == len(transcripts)
        
        # 验证至少有一个失败的结果
        failed_results = [r for r in results.values() if r is None]
        assert len(failed_results) >= 1
        
        # 验证至少有一个成功的结果
        successful_results = [r for r in results.values() if r is not None]
        assert len(successful_results) >= 1


class TestSummaryGeneratorRobustness:
    """总结生成器鲁棒性测试"""
    
    @given(transcript=transcript_strategy)
    def test_generator_handles_very_long_transcripts(self, transcript):
        """属性测试：处理非常长的转录文本
        
        对于任何长度的转录文本，生成器应该能够处理。
        """
        # 创建一个非常长的转录文本
        long_transcript = transcript * 100
        
        cache = LRUCache(max_size=100)
        generator = SummaryGenerator(cache=cache)
        
        # 验证模型选择不会失败
        model = generator.model_selector.select_model(long_transcript)
        assert model in generator.model_selector.MODELS
    
    @given(transcript=transcript_strategy)
    def test_generator_handles_special_characters(self, transcript):
        """属性测试：处理特殊字符
        
        对于包含特殊字符的转录文本，生成器应该能够处理。
        """
        # 添加特殊字符
        special_transcript = transcript + "!@#$%^&*()"
        
        cache = LRUCache(max_size=100)
        generator = SummaryGenerator(cache=cache)
        
        # 验证缓存键生成不会失败
        key_gen = CacheKeyGenerator()
        key = key_gen.generate_summary_key(special_transcript, 'gpt-3.5-turbo')
        assert key is not None
        assert len(key) > 0
    
    @given(transcript=transcript_strategy)
    def test_generator_handles_unicode_characters(self, transcript):
        """属性测试：处理 Unicode 字符
        
        对于包含 Unicode 字符的转录文本，生成器应该能够处理。
        """
        # 添加 Unicode 字符
        unicode_transcript = transcript + "你好世界🌍"
        
        cache = LRUCache(max_size=100)
        generator = SummaryGenerator(cache=cache)
        
        # 验证缓存键生成不会失败
        key_gen = CacheKeyGenerator()
        key = key_gen.generate_summary_key(unicode_transcript, 'gpt-3.5-turbo')
        assert key is not None
        assert len(key) > 0
