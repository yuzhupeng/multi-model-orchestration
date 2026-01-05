"""
转录生成器属性测试

Feature: multi-model-orchestration, Property 2: 缓存一致性
Validates: Requirements 3.3
"""
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from pathlib import Path
import tempfile
from unittest.mock import patch

from video_processor.transcript_generator import TranscriptGenerator
from video_processor.cache import LRUCache


class TestTranscriptGeneratorProperty:
    """转录生成器属性测试"""
    
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        languages=st.lists(
            st.sampled_from(["zh", "en", "auto"]),
            min_size=1,
            max_size=3,
            unique=True
        )
    )
    def test_language_consistency_property(self, languages):
        """
        属性：语言一致性
        
        对于任何指定的语言，生成的转录应该使用该语言。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            
            for language in languages:
                cache = LRUCache(max_size=10, ttl=3600)
                generator = TranscriptGenerator(cache=cache)
                
                audio_path = temp_dir / f"audio_{language}.mp3"
                audio_path.touch()
                
                with patch.object(generator, '_transcribe_with_whisper') as mock_whisper:
                    mock_whisper.return_value = f"转录文本 ({language})"
                    result = generator.generate(str(audio_path), language=language)
                    assert result == f"转录文本 ({language})"
    
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        num_audios=st.integers(min_value=1, max_value=10)
    )
    def test_cache_consistency_property(self, num_audios):
        """
        属性 2：缓存一致性
        
        对于任何已缓存的转录结果，第二次查询应返回与第一次相同的结果。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            cache = LRUCache(max_size=100, ttl=3600)
            generator = TranscriptGenerator(cache=cache)
            
            # 创建音频文件
            audio_path = temp_dir / "audio_0.mp3"
            audio_path.touch()
            
            with patch.object(generator, '_transcribe_with_whisper') as mock_whisper:
                mock_whisper.return_value = "测试转录文本"
                
                # 第一次生成
                first_result = generator.generate(str(audio_path))
                
                # 第二次生成应该从缓存返回相同结果
                second_result = generator.generate(str(audio_path))
                
                # 验证一致性
                assert first_result == second_result
