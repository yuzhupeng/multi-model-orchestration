"""
转录生成器单元测试

Feature: multi-model-orchestration, Task 7.2
Validates: Requirements 3.1, 3.2
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile

from video_processor.transcript_generator import TranscriptGenerator
from video_processor.cache import LRUCache
from video_processor.exceptions import TranscriptionError


class TestTranscriptGeneratorUnit:
    """转录生成器单元测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def generator(self):
        """转录生成器实例"""
        return TranscriptGenerator()
    
    @pytest.fixture
    def generator_with_cache(self):
        """带缓存的转录生成器实例"""
        cache = LRUCache(max_size=10, ttl=3600)
        return TranscriptGenerator(cache=cache)
    
    def test_generate_with_valid_audio(self, generator, temp_dir):
        """测试生成有效音频的转录"""
        audio_path = temp_dir / "test_audio.mp3"
        audio_path.touch()
        
        with patch.object(generator, '_transcribe_with_whisper') as mock_whisper:
            mock_whisper.return_value = "这是一个测试转录文本"
            result = generator.generate(str(audio_path))
            
            assert result == "这是一个测试转录文本"
            mock_whisper.assert_called_once()
    
    def test_generate_with_nonexistent_audio(self, generator):
        """测试生成不存在的音频"""
        with pytest.raises(FileNotFoundError):
            generator.generate("/nonexistent/audio.mp3")
    
    def test_generate_with_whisper_failure(self, generator, temp_dir):
        """测试 Whisper 失败"""
        audio_path = temp_dir / "test_audio.mp3"
        audio_path.touch()
        
        with patch.object(generator, '_transcribe_with_whisper') as mock_whisper:
            mock_whisper.side_effect = TranscriptionError("Whisper 失败")
            
            with pytest.raises(TranscriptionError):
                generator.generate(str(audio_path))
    
    def test_generate_caches_result(self, generator_with_cache, temp_dir):
        """测试生成结果被缓存"""
        audio_path = temp_dir / "test_audio.mp3"
        audio_path.touch()
        
        with patch.object(generator_with_cache, '_transcribe_with_whisper') as mock_whisper:
            mock_whisper.return_value = "测试转录文本"
            
            # 第一次生成
            result1 = generator_with_cache.generate(str(audio_path))
            assert mock_whisper.call_count == 1
            
            # 第二次生成应该从缓存返回
            result2 = generator_with_cache.generate(str(audio_path))
            
            # Whisper 不应该被调用第二次
            assert mock_whisper.call_count == 1
            assert result1 == result2
    
    def test_is_cached_returns_true_for_cached_transcript(self, generator_with_cache, temp_dir):
        """测试 is_cached 对已缓存的转录返回 True"""
        audio_path = temp_dir / "test_audio.mp3"
        audio_path.touch()
        
        with patch.object(generator_with_cache, '_transcribe_with_whisper') as mock_whisper:
            mock_whisper.return_value = "测试转录文本"
            generator_with_cache.generate(str(audio_path))
            
            assert generator_with_cache.is_cached(str(audio_path))
    
    def test_is_cached_returns_false_for_uncached_transcript(self, generator_with_cache):
        """测试 is_cached 对未缓存的转录返回 False"""
        assert not generator_with_cache.is_cached("/nonexistent/audio.mp3")
    
    def test_is_cached_returns_false_without_cache(self, generator):
        """测试没有缓存时 is_cached 返回 False"""
        assert not generator.is_cached("/any/audio.mp3")
    
    def test_get_cached_transcript_returns_cached_text(self, generator_with_cache, temp_dir):
        """测试 get_cached_transcript 返回缓存的文本"""
        audio_path = temp_dir / "test_audio.mp3"
        audio_path.touch()
        
        with patch.object(generator_with_cache, '_transcribe_with_whisper') as mock_whisper:
            mock_whisper.return_value = "测试转录文本"
            result = generator_with_cache.generate(str(audio_path))
            cached = generator_with_cache.get_cached_transcript(str(audio_path))
            
            assert cached == result
    
    def test_get_cached_transcript_returns_none_for_uncached(self, generator_with_cache):
        """测试 get_cached_transcript 对未缓存的返回 None"""
        result = generator_with_cache.get_cached_transcript("/nonexistent/audio.mp3")
        assert result is None
    
    def test_get_cached_transcript_returns_none_without_cache(self, generator):
        """测试没有缓存时 get_cached_transcript 返回 None"""
        result = generator.get_cached_transcript("/any/audio.mp3")
        assert result is None
    
    def test_delete_cached_transcript(self, generator_with_cache, temp_dir):
        """测试删除缓存的转录"""
        audio_path = temp_dir / "test_audio.mp3"
        audio_path.touch()
        
        with patch.object(generator_with_cache, '_transcribe_with_whisper') as mock_whisper:
            mock_whisper.return_value = "测试转录文本"
            generator_with_cache.generate(str(audio_path))
            assert generator_with_cache.is_cached(str(audio_path))
            
            generator_with_cache.delete_cached_transcript(str(audio_path))
            assert not generator_with_cache.is_cached(str(audio_path))
    
    def test_delete_cached_transcript_without_cache(self, generator):
        """测试没有缓存时删除不会出错"""
        # 应该不抛出异常
        generator.delete_cached_transcript("/any/audio.mp3")
    
    def test_generate_with_different_languages(self, temp_dir):
        """测试不同的语言"""
        for language in ["zh", "en", "auto"]:
            generator = TranscriptGenerator()
            audio_path = temp_dir / f"test_audio_{language}.mp3"
            audio_path.touch()
            
            with patch.object(generator, '_transcribe_with_whisper') as mock_whisper:
                mock_whisper.return_value = f"转录文本 ({language})"
                result = generator.generate(str(audio_path), language=language)
                assert result == f"转录文本 ({language})"
    
    def test_generate_multiple_audios_independently(self, generator_with_cache, temp_dir):
        """测试独立生成多个音频的转录"""
        audios = []
        for i in range(3):
            audio_path = temp_dir / f"test_audio_{i}.mp3"
            audio_path.touch()
            audios.append(audio_path)
        
        with patch.object(generator_with_cache, '_transcribe_with_whisper') as mock_whisper:
            mock_whisper.side_effect = [f"转录 {i}" for i in range(3)]
            
            results = []
            for audio_path in audios:
                result = generator_with_cache.generate(str(audio_path))
                results.append(result)
            
            # 所有结果应该不同
            assert len(set(results)) == len(results)
            
            # 所有结果都应该被缓存
            for audio_path in audios:
                assert generator_with_cache.is_cached(str(audio_path))
    
    def test_transcribe_with_whisper_api_key_missing(self, generator, temp_dir):
        """测试 Whisper API 密钥缺失"""
        audio_path = temp_dir / "test_audio.mp3"
        audio_path.touch()
        
        generator.api_key = None
        
        with pytest.raises(TranscriptionError, match="未设置 OPENAI_API_KEY"):
            generator._transcribe_with_whisper(str(audio_path))
    
    def test_transcribe_with_whisper_file_not_found(self, generator):
        """测试 Whisper 文件不存在"""
        generator.api_key = "test_key"
        
        with pytest.raises(TranscriptionError, match="音频文件不存在"):
            generator._transcribe_with_whisper("/nonexistent/audio.mp3")
