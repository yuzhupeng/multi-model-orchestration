"""
总结生成器模块

从转录文本生成总结，支持多种 LLM 模型和动态模型选择。
"""
import os
from typing import Optional, Dict, List
import hashlib

from video_processor.exceptions import SummarizationError
from video_processor.cache import LRUCache, CacheKeyGenerator
from video_processor.logger import get_logger

logger = get_logger(__name__)


class ModelSelector:
    """模型选择器
    
    根据转录长度和内容类型动态选择最合适的 LLM 模型。
    """
    
    # 模型配置
    MODELS = {
        "gpt-3.5-turbo": {
            "name": "gpt-3.5-turbo",
            "max_tokens": 4096,
            "cost_per_1k": 0.0015,
            "tier": "light"
        },
        "gpt-4": {
            "name": "gpt-4",
            "max_tokens": 8192,
            "cost_per_1k": 0.03,
            "tier": "standard"
        },
        "gpt-4-turbo": {
            "name": "gpt-4-turbo",
            "max_tokens": 128000,
            "cost_per_1k": 0.01,
            "tier": "advanced"
        },
    }
    
    # 转录长度阈值（字符数）
    SHORT_THRESHOLD = 1000
    MEDIUM_THRESHOLD = 5000
    LONG_THRESHOLD = 10000
    
    def __init__(self):
        """初始化模型选择器"""
        self.logger = get_logger(__name__)
    
    def select_model(
        self,
        transcript: str,
        content_type: str = "general",
        user_preference: Optional[str] = None
    ) -> str:
        """根据多个因素选择最合适的模型
        
        Args:
            transcript: 转录文本
            content_type: 内容类型（"general", "technical", "news", "entertainment"）
            user_preference: 用户偏好的模型（如果指定则使用该模型）
            
        Returns:
            选择的模型名称
            
        Raises:
            SummarizationError: 模型选择失败
        """
        # 如果用户指定了偏好模型，直接使用
        if user_preference:
            if user_preference not in self.MODELS:
                raise SummarizationError(f"不支持的模型: {user_preference}")
            self.logger.info(f"使用用户指定的模型: {user_preference}")
            return user_preference
        
        # 根据转录长度选择模型
        transcript_length = len(transcript)
        
        if content_type == "technical":
            return self._select_technical_model(transcript_length)
        elif content_type == "news":
            return self._select_news_model(transcript_length)
        elif content_type == "entertainment":
            return self._select_entertainment_model(transcript_length)
        else:
            return self._select_general_model(transcript_length)
    
    def _select_general_model(self, transcript_length: int) -> str:
        """为通用内容选择模型"""
        if transcript_length < self.SHORT_THRESHOLD:
            return "gpt-3.5-turbo"
        elif transcript_length < self.MEDIUM_THRESHOLD:
            return "gpt-4"
        else:
            return "gpt-4-turbo"
    
    def _select_technical_model(self, transcript_length: int) -> str:
        """为技术内容选择模型"""
        if transcript_length < self.SHORT_THRESHOLD:
            return "gpt-4"
        elif transcript_length < self.LONG_THRESHOLD:
            return "gpt-4-turbo"
        else:
            return "gpt-4-turbo"
    
    def _select_news_model(self, transcript_length: int) -> str:
        """为新闻内容选择模型"""
        if transcript_length < self.MEDIUM_THRESHOLD:
            return "gpt-3.5-turbo"
        else:
            return "gpt-4"
    
    def _select_entertainment_model(self, transcript_length: int) -> str:
        """为娱乐内容选择模型"""
        if transcript_length < self.LONG_THRESHOLD:
            return "gpt-3.5-turbo"
        else:
            return "gpt-4"
    
    def get_model_info(self, model_name: str) -> Dict:
        """获取模型信息
        
        Args:
            model_name: 模型名称
            
        Returns:
            模型信息字典
            
        Raises:
            SummarizationError: 模型不存在
        """
        if model_name not in self.MODELS:
            raise SummarizationError(f"不支持的模型: {model_name}")
        return self.MODELS[model_name]


class SummaryGenerator:
    """总结生成器类
    
    从转录文本生成总结，支持多种 LLM 模型、缓存和并发处理。
    """
    
    def __init__(
        self,
        cache: Optional[LRUCache] = None,
        api_key: Optional[str] = None,
        model_selector: Optional[ModelSelector] = None
    ):
        """初始化总结生成器
        
        Args:
            cache: LRU 缓存实例（可选）
            api_key: OpenAI API 密钥（可选）
            model_selector: 模型选择器实例（可选）
        """
        self.cache = cache
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_selector = model_selector or ModelSelector()
        self.key_generator = CacheKeyGenerator()
    
    def generate(
        self,
        transcript: str,
        model: Optional[str] = None,
        content_type: str = "general",
        max_length: int = 500
    ) -> str:
        """生成总结
        
        从转录文本生成总结，支持缓存和动态模型选择。
        
        Args:
            transcript: 转录文本
            model: 使用的模型（如果为 None 则自动选择）
            content_type: 内容类型
            max_length: 总结最大长度（字符数）
            
        Returns:
            生成的总结
            
        Raises:
            SummarizationError: 总结生成失败
            ValueError: 输入参数无效
        """
        if not transcript or not transcript.strip():
            raise ValueError("转录文本不能为空")
        
        # 选择模型
        if model is None:
            model = self.model_selector.select_model(
                transcript,
                content_type=content_type
            )
        
        logger.info(f"使用模型 {model} 生成总结")
        
        # 生成缓存键 - 使用转录文本、模型和最大长度
        cache_key = self.key_generator.generate_summary_key(transcript, model)
        
        # 检查缓存
        if self.cache is not None:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.info(f"从缓存返回总结: {cached_result[:50]}...")
                return cached_result
        
        try:
            # 调用 OpenAI API 生成总结
            summary = self._generate_with_openai(
                transcript,
                model,
                max_length
            )
            
            # 缓存结果
            if self.cache is not None:
                self.cache.set(cache_key, summary)
            
            logger.info(f"成功生成总结，长度: {len(summary)}")
            return summary
        
        except Exception as e:
            logger.error(f"总结生成失败: {e}")
            raise SummarizationError(f"总结生成失败: {e}")
    
    def _generate_with_openai(
        self,
        transcript: str,
        model: str,
        max_length: int
    ) -> str:
        """使用 OpenAI API 生成总结
        
        Args:
            transcript: 转录文本
            model: 模型名称
            max_length: 总结最大长度
            
        Returns:
            生成的总结
            
        Raises:
            SummarizationError: 生成失败
        """
        try:
            # 尝试导入 openai
            try:
                import openai
            except ImportError:
                raise SummarizationError("openai 库未安装，请运行 pip install openai")
            
            # 设置 API 密钥
            if not self.api_key:
                raise SummarizationError("未设置 OPENAI_API_KEY 环境变量")
            
            openai.api_key = self.api_key
            
            # 构建提示词
            prompt = self._build_prompt(transcript, max_length)
            
            # 调用 OpenAI API
            response = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的内容总结助手。请根据提供的转录文本生成简洁、准确的总结。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=max_length // 4,  # 粗略估计：1 个 token ≈ 4 个字符
            )
            
            # 提取总结
            summary = response.choices[0].message.content.strip()
            
            if not summary:
                raise SummarizationError("OpenAI API 返回空总结")
            
            return summary
        
        except SummarizationError:
            raise
        except Exception as e:
            raise SummarizationError(f"OpenAI API 调用失败: {str(e)}")
    
    def _build_prompt(self, transcript: str, max_length: int) -> str:
        """构建提示词
        
        Args:
            transcript: 转录文本
            max_length: 总结最大长度
            
        Returns:
            提示词
        """
        return f"""请根据以下转录文本生成一个总结。总结应该：
1. 简洁明了，最多 {max_length} 个字符
2. 保留关键信息和主要观点
3. 使用清晰的语言
4. 避免冗余和重复

转录文本：
{transcript}

请生成总结："""
    
    def is_cached(self, transcript: str, model: str) -> bool:
        """检查总结是否已缓存
        
        Args:
            transcript: 转录文本
            model: 模型名称
            
        Returns:
            是否已缓存
        """
        if self.cache is None:
            return False
        
        cache_key = self.key_generator.generate_summary_key(transcript, model)
        return self.cache.get(cache_key) is not None
    
    def get_cached_summary(self, transcript: str, model: str) -> Optional[str]:
        """获取缓存的总结
        
        Args:
            transcript: 转录文本
            model: 模型名称
            
        Returns:
            缓存的总结，如果不存在则返回 None
        """
        if self.cache is None:
            return None
        
        cache_key = self.key_generator.generate_summary_key(transcript, model)
        return self.cache.get(cache_key)
    
    def delete_cached_summary(self, transcript: str, model: str) -> None:
        """删除缓存的总结
        
        Args:
            transcript: 转录文本
            model: 模型名称
        """
        if self.cache is None:
            return
        
        cache_key = self.key_generator.generate_summary_key(transcript, model)
        self.cache.delete(cache_key)
        logger.info(f"已删除缓存的总结")
    
    def generate_concurrent(
        self,
        transcripts: List[str],
        models: Optional[List[str]] = None,
        thread_pool=None
    ) -> Dict[str, str]:
        """并发生成多个转录文本的总结
        
        Args:
            transcripts: 转录文本列表
            models: 模型列表（如果为 None 则自动选择）
            thread_pool: 线程池实例（可选）
        
        Returns:
            转录文本到总结的映射字典
        """
        results = {}
        
        if models is None:
            models = [None] * len(transcripts)
        
        if thread_pool is None:
            # 如果没有提供线程池，直接顺序生成
            for transcript, model in zip(transcripts, models):
                try:
                    summary = self.generate(transcript, model=model)
                    results[transcript[:50]] = summary
                except Exception as e:
                    logger.error(f"生成总结失败: {e}")
                    results[transcript[:50]] = None
        else:
            # 使用线程池并发生成
            futures = {}
            for i, (transcript, model) in enumerate(zip(transcripts, models)):
                task_id = f"summarize_{i}"
                future = thread_pool.submit(task_id, self.generate, transcript, model)
                futures[i] = (transcript, future)
            
            # 收集结果
            for i, (transcript, future) in futures.items():
                try:
                    summary = thread_pool.get_result(f"summarize_{i}")
                    results[transcript[:50]] = summary
                except Exception as e:
                    logger.error(f"生成总结失败: {e}")
                    results[transcript[:50]] = None
        
        return results
