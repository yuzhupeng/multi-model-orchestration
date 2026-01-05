"""
音频提取器属性测试

Feature: multi-model-orchestration, Property 2: 缓存一致性
Validates: Requirements 2.3
"""
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from pathlib import Path
import tempfile
from unittest.mock import patch

from video_processor.audio_extractor import AudioExtractor
from video_processor.cache import LRUCache


class TestAudioExtractorProperty:
    """音频提取器属性测试"""
    
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        audio_formats=st.lists(
            st.sampled_from(["mp3", "wav", "aac"]),
            min_size=1,
            max_size=3,
            unique=True
        )
    )
    def test_audio_format_consistency_property(self, audio_formats):
        """
        属性：音频格式一致性
        
        对于任何指定的音频格式，提取的文件应该使用该格式。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            
            for audio_format in audio_formats:
                cache = LRUCache(max_size=10, ttl=3600)
                extractor = AudioExtractor(
                    output_dir=temp_dir,
                    cache=cache,
                    audio_format=audio_format
                )
                
                video_path = temp_dir / f"video_{audio_format}.mp4"
                video_path.touch()
                
                with patch.object(extractor, '_extract_with_ffmpeg'):
                    result = extractor.extract(str(video_path))
                    assert result.endswith(f".{audio_format}")
    
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        num_videos=st.integers(min_value=1, max_value=10)
    )
    def test_cache_consistency_property(self, num_videos):
        """
        属性 2：缓存一致性
        
        对于任何已缓存的音频提取结果，第二次查询应返回与第一次相同的结果。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            cache = LRUCache(max_size=100, ttl=3600)
            extractor = AudioExtractor(output_dir=temp_dir, cache=cache)
            
            # 创建视频文件
            video_path = temp_dir / "video_0.mp4"
            video_path.touch()
            
            with patch.object(extractor, '_extract_with_ffmpeg'):
                # 第一次提取
                first_result = extractor.extract(str(video_path))
                
                # 第二次提取应该从缓存返回相同结果
                second_result = extractor.extract(str(video_path))
                
                # 验证一致性
                assert first_result == second_result
