"""
视频下载器属性测试

Feature: multi-model-orchestration, Property 2: 缓存一致性
Validates: Requirements 1.4
"""
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import hashlib

from video_processor.downloader import VideoDownloader


class TestVideoDownloaderProperty:
    """视频下载器属性测试"""
    
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        urls=st.lists(
            st.just("https://www.youtube.com/watch?v=test"),
            min_size=1,
            max_size=10,
            unique=True
        )
    )
    def test_cache_consistency_property(self, urls):
        """
        属性 2：缓存一致性
        
        对于任何已缓存的结果，第二次查询应返回与第一次相同的结果。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            downloader = VideoDownloader(output_dir=temp_dir)
            
            # 为每个 URL 创建缓存文件
            for url in urls:
                filename = hashlib.md5(url.encode()).hexdigest()
                cache_file = temp_dir / f"{filename}.mp4"
                cache_file.touch()
            
            # 验证缓存一致性
            for url in urls:
                # 第一次查询
                first_result = downloader.get_cached_file(url)
                
                # 第二次查询
                second_result = downloader.get_cached_file(url)
                
                # 两次结果应该相同
                assert first_result == second_result
                assert first_result is not None
    
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        num_urls=st.integers(min_value=1, max_value=20)
    )
    def test_cache_detection_property(self, num_urls):
        """
        属性：缓存检测
        
        对于任何缓存的文件，is_cached 应该返回 True。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            downloader = VideoDownloader(output_dir=temp_dir)
            
            # 创建缓存文件
            urls = []
            for i in range(num_urls):
                url = f"https://www.youtube.com/watch?v=test{i}"
                urls.append(url)
                
                filename = hashlib.md5(url.encode()).hexdigest()
                cache_file = temp_dir / f"{filename}.mp4"
                cache_file.touch()
            
            # 验证所有缓存都能被检测到
            for url in urls:
                assert downloader.is_cached(url)
    
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        num_urls=st.integers(min_value=1, max_value=20)
    )
    def test_cache_deletion_property(self, num_urls):
        """
        属性：缓存删除
        
        对于任何缓存的文件，删除后应该无法再检测到。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            downloader = VideoDownloader(output_dir=temp_dir)
            
            # 创建缓存文件
            urls = []
            for i in range(num_urls):
                url = f"https://www.youtube.com/watch?v=test{i}"
                urls.append(url)
                
                filename = hashlib.md5(url.encode()).hexdigest()
                cache_file = temp_dir / f"{filename}.mp4"
                cache_file.touch()
            
            # 删除所有缓存
            for url in urls:
                assert downloader.is_cached(url)
                downloader.delete_cached_file(url)
                assert not downloader.is_cached(url)
    
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        urls=st.lists(
            st.just("https://www.youtube.com/watch?v=test"),
            min_size=1,
            max_size=10
        )
    )
    def test_platform_detection_property(self, urls):
        """
        属性：平台检测
        
        对于任何有效的 URL，平台检测应该返回正确的平台。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            downloader = VideoDownloader(output_dir=temp_dir)
            
            # 测试 YouTube URL
            youtube_urls = [
                "https://www.youtube.com/watch?v=test1",
                "https://youtu.be/test2",
            ]
            
            for url in youtube_urls:
                platform = downloader._detect_platform(url)
                assert platform == "youtube"
            
            # 测试 Bilibili URL
            bilibili_urls = [
                "https://www.bilibili.com/video/BV1xx411c7mD",
                "https://b23.tv/BV1xx411c7mD",
            ]
            
            for url in bilibili_urls:
                platform = downloader._detect_platform(url)
                assert platform == "bilibili"
