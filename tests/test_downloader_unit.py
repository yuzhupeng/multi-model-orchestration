"""
视频下载器单元测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile

from video_processor.downloader import VideoDownloader
from video_processor.exceptions import DownloadError


class TestVideoDownloaderUnit:
    """视频下载器单元测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def downloader(self, temp_dir):
        """创建下载器实例"""
        return VideoDownloader(output_dir=temp_dir)
    
    def test_downloader_initialization(self, temp_dir):
        """测试下载器初始化"""
        downloader = VideoDownloader(output_dir=temp_dir)
        assert downloader.output_dir == temp_dir
    
    def test_detect_platform_youtube(self, downloader):
        """测试检测 YouTube 平台"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        platform = downloader._detect_platform(url)
        assert platform == "youtube"
    
    def test_detect_platform_youtube_short(self, downloader):
        """测试检测 YouTube 短链接"""
        url = "https://youtu.be/dQw4w9WgXcQ"
        platform = downloader._detect_platform(url)
        assert platform == "youtube"
    
    def test_detect_platform_bilibili(self, downloader):
        """测试检测 Bilibili 平台"""
        url = "https://www.bilibili.com/video/BV1xx411c7mD"
        platform = downloader._detect_platform(url)
        assert platform == "bilibili"
    
    def test_detect_platform_bilibili_short(self, downloader):
        """测试检测 Bilibili 短链接"""
        url = "https://b23.tv/BV1xx411c7mD"
        platform = downloader._detect_platform(url)
        assert platform == "bilibili"
    
    def test_detect_platform_unsupported(self, downloader):
        """测试检测不支持的平台"""
        url = "https://www.example.com/video"
        with pytest.raises(DownloadError):
            downloader._detect_platform(url)
    
    def test_is_cached_not_exists(self, downloader):
        """测试检查不存在的缓存"""
        url = "https://www.youtube.com/watch?v=test"
        assert not downloader.is_cached(url)
    
    def test_is_cached_exists(self, downloader, temp_dir):
        """测试检查存在的缓存"""
        url = "https://www.youtube.com/watch?v=test"
        
        # 创建缓存文件
        import hashlib
        filename = hashlib.md5(url.encode()).hexdigest()
        cache_file = temp_dir / f"{filename}.mp4"
        cache_file.touch()
        
        assert downloader.is_cached(url)
    
    def test_get_cached_file_not_exists(self, downloader):
        """测试获取不存在的缓存文件"""
        url = "https://www.youtube.com/watch?v=test"
        result = downloader.get_cached_file(url)
        assert result is None
    
    def test_get_cached_file_exists(self, downloader, temp_dir):
        """测试获取存在的缓存文件"""
        url = "https://www.youtube.com/watch?v=test"
        
        # 创建缓存文件
        import hashlib
        filename = hashlib.md5(url.encode()).hexdigest()
        cache_file = temp_dir / f"{filename}.mp4"
        cache_file.touch()
        
        result = downloader.get_cached_file(url)
        assert result is not None
        assert str(cache_file) == result
    
    def test_delete_cached_file_not_exists(self, downloader):
        """测试删除不存在的缓存文件"""
        url = "https://www.youtube.com/watch?v=test"
        result = downloader.delete_cached_file(url)
        assert not result
    
    def test_delete_cached_file_exists(self, downloader, temp_dir):
        """测试删除存在的缓存文件"""
        url = "https://www.youtube.com/watch?v=test"
        
        # 创建缓存文件
        import hashlib
        filename = hashlib.md5(url.encode()).hexdigest()
        cache_file = temp_dir / f"{filename}.mp4"
        cache_file.touch()
        
        assert cache_file.exists()
        result = downloader.delete_cached_file(url)
        assert result
        assert not cache_file.exists()
    
    @patch('video_processor.downloader.yt_dlp.YoutubeDL')
    def test_download_youtube(self, mock_ydl_class, downloader):
        """测试下载 YouTube 视频（模拟）"""
        # 设置模拟
        mock_ydl = MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.return_value = {
            "title": "Test Video",
            "ext": "mp4",
        }
        mock_ydl.prepare_filename.return_value = "/path/to/video.mp4"
        
        url = "https://www.youtube.com/watch?v=test"
        result = downloader.download(url)
        
        assert result == "/path/to/video.mp4"
        mock_ydl.extract_info.assert_called_once()
    
    @patch('video_processor.downloader.yt_dlp.YoutubeDL')
    def test_download_bilibili(self, mock_ydl_class, downloader):
        """测试下载 Bilibili 视频（模拟）"""
        # 设置模拟
        mock_ydl = MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.return_value = {
            "title": "Test Video",
            "ext": "mp4",
        }
        mock_ydl.prepare_filename.return_value = "/path/to/video.mp4"
        
        url = "https://www.bilibili.com/video/BV1xx411c7mD"
        result = downloader.download(url)
        
        assert result == "/path/to/video.mp4"
        mock_ydl.extract_info.assert_called_once()
    
    @patch('video_processor.downloader.yt_dlp.YoutubeDL')
    def test_download_with_custom_filename(self, mock_ydl_class, downloader):
        """测试使用自定义文件名下载"""
        # 设置模拟
        mock_ydl = MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.return_value = {
            "title": "Test Video",
            "ext": "mp4",
        }
        mock_ydl.prepare_filename.return_value = "/path/to/custom_video.mp4"
        
        url = "https://www.youtube.com/watch?v=test"
        result = downloader.download(url, filename="custom_video")
        
        assert result == "/path/to/custom_video.mp4"
    
    @patch('video_processor.downloader.yt_dlp.YoutubeDL')
    def test_download_failure(self, mock_ydl_class, downloader):
        """测试下载失败"""
        # 设置模拟抛出异常
        mock_ydl_class.return_value.__enter__.side_effect = Exception("Download failed")
        
        url = "https://www.youtube.com/watch?v=test"
        with pytest.raises(DownloadError):
            downloader.download(url)
    
    @patch('video_processor.downloader.yt_dlp.YoutubeDL')
    def test_get_video_info(self, mock_ydl_class, downloader):
        """测试获取视频信息"""
        # 设置模拟
        mock_ydl = MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.return_value = {
            "title": "Test Video",
            "duration": 300,
            "uploader": "Test Channel",
            "upload_date": "20240101",
            "description": "Test description",
            "thumbnail": "https://example.com/thumb.jpg",
        }
        
        url = "https://www.youtube.com/watch?v=test"
        info = downloader.get_video_info(url)
        
        assert info is not None
        assert info["title"] == "Test Video"
        assert info["duration"] == 300
        assert info["uploader"] == "Test Channel"
    
    @patch('video_processor.downloader.yt_dlp.YoutubeDL')
    def test_get_video_info_failure(self, mock_ydl_class, downloader):
        """测试获取视频信息失败"""
        # 设置模拟抛出异常
        mock_ydl_class.return_value.__enter__.side_effect = Exception("Info extraction failed")
        
        url = "https://www.youtube.com/watch?v=test"
        info = downloader.get_video_info(url)
        
        assert info is None
