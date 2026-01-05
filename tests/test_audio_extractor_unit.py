"""
音频提取器单元测试

Feature: multi-model-orchestration, Task 6.2
Validates: Requirements 2.1, 2.2
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import tempfile

from video_processor.audio_extractor import AudioExtractor
from video_processor.cache import LRUCache
from video_processor.exceptions import ExtractionError


class TestAudioExtractorUnit:
    """音频提取器单元测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def extractor(self, temp_dir):
        """音频提取器实例"""
        return AudioExtractor(output_dir=temp_dir)
    
    @pytest.fixture
    def extractor_with_cache(self, temp_dir):
        """带缓存的音频提取器实例"""
        cache = LRUCache(max_size=10, ttl=3600)
        return AudioExtractor(output_dir=temp_dir, cache=cache)
    
    def test_extract_with_valid_video(self, extractor, temp_dir):
        """测试提取有效视频的音频"""
        video_path = temp_dir / "test_video.mp4"
        video_path.touch()
        
        with patch.object(extractor, '_extract_with_ffmpeg') as mock_ffmpeg:
            result = extractor.extract(str(video_path))
            
            assert result is not None
            assert result.endswith('.mp3')
            mock_ffmpeg.assert_called_once()
    
    def test_extract_with_nonexistent_video(self, extractor):
        """测试提取不存在的视频"""
        with pytest.raises(FileNotFoundError):
            extractor.extract("/nonexistent/video.mp4")
    
    def test_extract_with_ffmpeg_failure(self, extractor, temp_dir):
        """测试 ffmpeg 失败"""
        video_path = temp_dir / "test_video.mp4"
        video_path.touch()
        
        with patch.object(extractor, '_extract_with_ffmpeg') as mock_ffmpeg:
            mock_ffmpeg.side_effect = ExtractionError("ffmpeg 失败")
            
            with pytest.raises(ExtractionError):
                extractor.extract(str(video_path))
    
    def test_extract_caches_result(self, extractor_with_cache, temp_dir):
        """测试提取结果被缓存"""
        video_path = temp_dir / "test_video.mp4"
        video_path.touch()
        
        with patch.object(extractor_with_cache, '_extract_with_ffmpeg') as mock_ffmpeg:
            # 第一次提取
            result1 = extractor_with_cache.extract(str(video_path))
            assert mock_ffmpeg.call_count == 1
            
            # 第二次提取应该从缓存返回
            result2 = extractor_with_cache.extract(str(video_path))
            
            # ffmpeg 不应该被调用第二次
            assert mock_ffmpeg.call_count == 1
            assert result1 == result2
    
    def test_is_cached_returns_true_for_cached_audio(self, extractor_with_cache, temp_dir):
        """测试 is_cached 对已缓存的音频返回 True"""
        video_path = temp_dir / "test_video.mp4"
        video_path.touch()
        
        with patch.object(extractor_with_cache, '_extract_with_ffmpeg'):
            extractor_with_cache.extract(str(video_path))
            
            assert extractor_with_cache.is_cached(str(video_path))
    
    def test_is_cached_returns_false_for_uncached_audio(self, extractor_with_cache):
        """测试 is_cached 对未缓存的音频返回 False"""
        assert not extractor_with_cache.is_cached("/nonexistent/video.mp4")
    
    def test_is_cached_returns_false_without_cache(self, extractor):
        """测试没有缓存时 is_cached 返回 False"""
        assert not extractor.is_cached("/any/video.mp4")
    
    def test_get_cached_audio_returns_cached_path(self, extractor_with_cache, temp_dir):
        """测试 get_cached_audio 返回缓存的路径"""
        video_path = temp_dir / "test_video.mp4"
        video_path.touch()
        
        with patch.object(extractor_with_cache, '_extract_with_ffmpeg'):
            result = extractor_with_cache.extract(str(video_path))
            cached = extractor_with_cache.get_cached_audio(str(video_path))
            
            assert cached == result
    
    def test_get_cached_audio_returns_none_for_uncached(self, extractor_with_cache):
        """测试 get_cached_audio 对未缓存的返回 None"""
        result = extractor_with_cache.get_cached_audio("/nonexistent/video.mp4")
        assert result is None
    
    def test_get_cached_audio_returns_none_without_cache(self, extractor):
        """测试没有缓存时 get_cached_audio 返回 None"""
        result = extractor.get_cached_audio("/any/video.mp4")
        assert result is None
    
    def test_delete_cached_audio(self, extractor_with_cache, temp_dir):
        """测试删除缓存的音频"""
        video_path = temp_dir / "test_video.mp4"
        video_path.touch()
        
        with patch.object(extractor_with_cache, '_extract_with_ffmpeg'):
            extractor_with_cache.extract(str(video_path))
            assert extractor_with_cache.is_cached(str(video_path))
            
            extractor_with_cache.delete_cached_audio(str(video_path))
            assert not extractor_with_cache.is_cached(str(video_path))
    
    def test_delete_cached_audio_without_cache(self, extractor):
        """测试没有缓存时删除不会出错"""
        # 应该不抛出异常
        extractor.delete_cached_audio("/any/video.mp4")
    
    def test_extract_with_different_audio_formats(self, temp_dir):
        """测试不同的音频格式"""
        for audio_format in ["mp3", "wav", "aac"]:
            extractor = AudioExtractor(output_dir=temp_dir, audio_format=audio_format)
            video_path = temp_dir / f"test_video_{audio_format}.mp4"
            video_path.touch()
            
            with patch.object(extractor, '_extract_with_ffmpeg'):
                result = extractor.extract(str(video_path))
                assert result.endswith(f".{audio_format}")
    
    def test_extract_creates_output_directory(self):
        """测试提取时创建输出目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "audio" / "nested"
            extractor = AudioExtractor(output_dir=output_dir)
            
            assert output_dir.exists()
    
    @patch('subprocess.run')
    def test_extract_with_ffmpeg_timeout(self, mock_run, extractor, temp_dir):
        """测试 ffmpeg 超时"""
        video_path = temp_dir / "test_video.mp4"
        video_path.touch()
        
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("ffmpeg", 300)
        
        with pytest.raises(ExtractionError, match="超时"):
            extractor.extract(str(video_path))
    
    @patch('subprocess.run')
    def test_extract_with_ffmpeg_not_found(self, mock_run, extractor, temp_dir):
        """测试 ffmpeg 未安装"""
        video_path = temp_dir / "test_video.mp4"
        video_path.touch()
        
        mock_run.side_effect = FileNotFoundError("ffmpeg not found")
        
        with pytest.raises(ExtractionError, match="未安装"):
            extractor.extract(str(video_path))
    
    @patch('subprocess.run')
    def test_extract_with_ffmpeg_error(self, mock_run, extractor, temp_dir):
        """测试 ffmpeg 返回错误"""
        video_path = temp_dir / "test_video.mp4"
        video_path.touch()
        
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "ffmpeg error message"
        mock_run.return_value = mock_result
        
        with pytest.raises(ExtractionError, match="ffmpeg 命令失败"):
            extractor.extract(str(video_path))
    
    def test_extract_multiple_videos_independently(self, extractor_with_cache, temp_dir):
        """测试独立提取多个视频"""
        videos = []
        for i in range(3):
            video_path = temp_dir / f"test_video_{i}.mp4"
            video_path.touch()
            videos.append(video_path)
        
        with patch.object(extractor_with_cache, '_extract_with_ffmpeg'):
            results = []
            for video_path in videos:
                result = extractor_with_cache.extract(str(video_path))
                results.append(result)
            
            # 所有结果应该不同
            assert len(set(results)) == len(results)
            
            # 所有结果都应该被缓存
            for video_path in videos:
                assert extractor_with_cache.is_cached(str(video_path))
