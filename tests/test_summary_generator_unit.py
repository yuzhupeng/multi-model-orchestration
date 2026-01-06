"""
总结生成器单元测试

测试总结生成、模型选择和缓存集成。
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from video_processor.summary_generator import SummaryGenerator, ModelSelector
from video_processor.cache import LRUCache
from video_processor.exceptions import SummarizationError


class TestModelSelector:
    """模型选择器测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.selector = ModelSelector()
    
    def test_select_model_with_user_preference(self):
        """测试用户偏好模型选择"""
        transcript = "This is a test transcript."
        model = self.selector.select_model(
            transcript,
            user_preference="gpt-4"
        )
        assert model == "gpt-4"
    
    def test_select_model_invalid_preference(self):
        """测试无效的用户偏好模型"""
        transcript = "This is a test transcript."
        with pytest.raises(SummarizationError):
            self.selector.select_model(
                transcript,
                user_preference="invalid-model"
            )
    
    def test_select_general_model_short_transcript(self):
        """测试短转录文本的通用模型选择"""
        transcript = "Short text" * 50  # ~500 字符
        model = self.selector.select_model(transcript, content_type="general")
        assert model == "gpt-3.5-turbo"
    
    def test_select_general_model_medium_transcript(self):
        """测试中等转录文本的通用模型选择"""
        transcript = "Medium text" * 300  # ~3300 字符
        model = self.selector.select_model(transcript, content_type="general")
        assert model == "gpt-4"
    
    def test_select_general_model_long_transcript(self):
        """测试长转录文本的通用模型选择"""
        transcript = "Long text" * 1000  # ~9000 字符
        model = self.selector.select_model(transcript, content_type="general")
        assert model == "gpt-4-turbo"
    
    def test_select_technical_model(self):
        """测试技术内容模型选择"""
        transcript = "Technical content" * 100  # ~1700 字符
        model = self.selector.select_model(
            transcript,
            content_type="technical"
        )
        assert model == "gpt-4"
    
    def test_select_news_model(self):
        """测试新闻内容模型选择"""
        transcript = "News content" * 200  # ~2400 字符
        model = self.selector.select_model(
            transcript,
            content_type="news"
        )
        assert model == "gpt-3.5-turbo"
    
    def test_select_entertainment_model(self):
        """测试娱乐内容模型选择"""
        transcript = "Entertainment" * 500  # ~6500 字符
        model = self.selector.select_model(
            transcript,
            content_type="entertainment"
        )
        assert model == "gpt-4"
    
    def test_get_model_info(self):
        """测试获取模型信息"""
        info = self.selector.get_model_info("gpt-4")
        assert info["name"] == "gpt-4"
        assert info["max_tokens"] == 8192
        assert info["tier"] == "standard"
    
    def test_get_model_info_invalid(self):
        """测试获取无效模型信息"""
        with pytest.raises(SummarizationError):
            self.selector.get_model_info("invalid-model")


class TestSummaryGenerator:
    """总结生成器测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.cache = LRUCache(max_size=100)
        self.generator = SummaryGenerator(cache=self.cache)
    
    def test_generate_empty_transcript(self):
        """测试空转录文本"""
        with pytest.raises(ValueError):
            self.generator.generate("")
    
    def test_generate_whitespace_transcript(self):
        """测试仅空格的转录文本"""
        with pytest.raises(ValueError):
            self.generator.generate("   ")
    
    @patch('openai.ChatCompletion.create')
    def test_generate_success(self, mock_create):
        """测试成功生成总结"""
        # 模拟 OpenAI API 响应
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "This is a summary."
        mock_create.return_value = mock_response
        
        transcript = "This is a test transcript with some content."
        summary = self.generator.generate(transcript)
        
        assert summary == "This is a summary."
        assert mock_create.called
    
    @patch('openai.ChatCompletion.create')
    def test_generate_with_model_selection(self, mock_create):
        """测试带模型选择的总结生成"""
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Summary with model selection."
        mock_create.return_value = mock_response
        
        transcript = "Test transcript" * 100
        summary = self.generator.generate(
            transcript,
            content_type="technical"
        )
        
        assert summary == "Summary with model selection."
        # 验证调用了 OpenAI API
        assert mock_create.called
    
    @patch('openai.ChatCompletion.create')
    def test_generate_with_explicit_model(self, mock_create):
        """测试使用显式模型的总结生成"""
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Summary with explicit model."
        mock_create.return_value = mock_response
        
        transcript = "Test transcript"
        summary = self.generator.generate(
            transcript,
            model="gpt-4"
        )
        
        assert summary == "Summary with explicit model."
        # 验证使用了正确的模型
        call_args = mock_create.call_args
        assert call_args[1]["model"] == "gpt-4"
    
    @patch('openai.ChatCompletion.create')
    def test_generate_caching(self, mock_create):
        """测试总结生成缓存"""
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Cached summary."
        mock_create.return_value = mock_response
        
        transcript = "Test transcript for caching"
        
        # 第一次调用
        summary1 = self.generator.generate(transcript)
        assert summary1 == "Cached summary."
        assert mock_create.call_count == 1
        
        # 第二次调用应该从缓存返回
        summary2 = self.generator.generate(transcript)
        assert summary2 == "Cached summary."
        assert mock_create.call_count == 1  # 没有增加
    
    @patch('openai.ChatCompletion.create')
    def test_generate_api_error(self, mock_create):
        """测试 API 错误处理"""
        mock_create.side_effect = Exception("API Error")
        
        transcript = "Test transcript"
        with pytest.raises(SummarizationError):
            self.generator.generate(transcript)
    
    @patch('openai.ChatCompletion.create')
    def test_generate_empty_response(self, mock_create):
        """测试空 API 响应"""
        mock_response = MagicMock()
        mock_response.choices[0].message.content = ""
        mock_create.return_value = mock_response
        
        transcript = "Test transcript"
        with pytest.raises(SummarizationError):
            self.generator.generate(transcript)
    
    def test_is_cached(self):
        """测试缓存检查"""
        transcript = "Test transcript"
        model = "gpt-3.5-turbo"
        
        # 初始状态不在缓存中
        assert not self.generator.is_cached(transcript, model)
        
        # 手动添加到缓存
        from video_processor.cache import CacheKeyGenerator
        key_gen = CacheKeyGenerator()
        key = key_gen.generate_summary_key(transcript, model)
        self.cache.set(key, "Cached summary")
        
        # 现在应该在缓存中
        assert self.generator.is_cached(transcript, model)
    
    def test_get_cached_summary(self):
        """测试获取缓存的总结"""
        transcript = "Test transcript"
        model = "gpt-3.5-turbo"
        
        # 初始状态返回 None
        assert self.generator.get_cached_summary(transcript, model) is None
        
        # 手动添加到缓存
        from video_processor.cache import CacheKeyGenerator
        key_gen = CacheKeyGenerator()
        key = key_gen.generate_summary_key(transcript, model)
        self.cache.set(key, "Cached summary")
        
        # 现在应该返回缓存的值
        assert self.generator.get_cached_summary(transcript, model) == "Cached summary"
    
    def test_delete_cached_summary(self):
        """测试删除缓存的总结"""
        transcript = "Test transcript"
        model = "gpt-3.5-turbo"
        
        # 手动添加到缓存
        from video_processor.cache import CacheKeyGenerator
        key_gen = CacheKeyGenerator()
        key = key_gen.generate_summary_key(transcript, model)
        self.cache.set(key, "Cached summary")
        
        # 验证在缓存中
        assert self.generator.is_cached(transcript, model)
        
        # 删除
        self.generator.delete_cached_summary(transcript, model)
        
        # 验证已删除
        assert not self.generator.is_cached(transcript, model)
    
    def test_generator_without_cache(self):
        """测试没有缓存的生成器"""
        generator = SummaryGenerator(cache=None)
        
        # 应该能够创建生成器
        assert generator.cache is None
        
        # 缓存检查应该返回 False
        assert not generator.is_cached("test", "gpt-3.5-turbo")
    
    @patch('openai.ChatCompletion.create')
    def test_generate_with_max_length(self, mock_create):
        """测试带最大长度的总结生成"""
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Short summary."
        mock_create.return_value = mock_response
        
        transcript = "Test transcript"
        summary = self.generator.generate(
            transcript,
            max_length=200
        )
        
        assert summary == "Short summary."
        # 验证 max_tokens 参数
        call_args = mock_create.call_args
        assert call_args[1]["max_tokens"] == 50  # 200 // 4
    
    @patch('openai.ChatCompletion.create')
    def test_generate_concurrent(self, mock_create):
        """测试并发生成总结"""
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Summary"
        mock_create.return_value = mock_response
        
        transcripts = [
            "Transcript 1",
            "Transcript 2",
            "Transcript 3"
        ]
        
        results = self.generator.generate_concurrent(transcripts)
        
        # 应该返回字典
        assert isinstance(results, dict)
        # 应该有 3 个结果
        assert len(results) == 3
        # 所有值都应该是 "Summary"
        for value in results.values():
            assert value == "Summary"
    
    def test_build_prompt(self):
        """测试提示词构建"""
        transcript = "Test transcript content"
        max_length = 500
        
        prompt = self.generator._build_prompt(transcript, max_length)
        
        assert "Test transcript content" in prompt
        assert "500" in prompt
        assert "总结" in prompt or "summary" in prompt.lower()
