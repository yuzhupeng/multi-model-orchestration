"""
视频下载器 - 支持 YouTube 和 Bilibili
"""
import os
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import yt_dlp

from .logger import get_logger
from .exceptions import DownloadError
from .config import VIDEOS_DIR, DOWNLOAD_TIMEOUT, DOWNLOAD_RETRIES

logger = get_logger(__name__)


class VideoDownloader:
    """
    视频下载器
    
    特性：
    - 支持 YouTube 下载
    - 支持 Bilibili 下载
    - 错误处理和重试
    - 本地存储管理
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        初始化视频下载器
        
        Args:
            output_dir: 输出目录，默认为 VIDEOS_DIR
        """
        self.output_dir = output_dir or VIDEOS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _detect_platform(self, url: str) -> str:
        """
        检测视频平台
        
        Args:
            url: 视频 URL
        
        Returns:
            平台名称 ("youtube" 或 "bilibili")
        
        Raises:
            DownloadError: 如果平台不支持
        """
        if "youtube.com" in url or "youtu.be" in url:
            return "youtube"
        elif "bilibili.com" in url or "b23.tv" in url:
            return "bilibili"
        else:
            raise DownloadError(f"不支持的平台: {url}")
    
    def _get_ydl_opts(self, output_path: str) -> Dict[str, Any]:
        """
        获取 yt-dlp 选项
        
        Args:
            output_path: 输出路径
        
        Returns:
            yt-dlp 选项字典
        """
        return {
            "format": "best",
            "outtmpl": output_path,
            "quiet": False,
            "no_warnings": False,
            "socket_timeout": DOWNLOAD_TIMEOUT,
            "retries": DOWNLOAD_RETRIES,
            "fragment_retries": DOWNLOAD_RETRIES,
        }
    
    def download(self, url: str, filename: Optional[str] = None) -> str:
        """
        下载视频
        
        Args:
            url: 视频 URL
            filename: 自定义文件名（不包括扩展名）
        
        Returns:
            本地文件路径
        
        Raises:
            DownloadError: 如果下载失败
        """
        try:
            # 检测平台
            platform = self._detect_platform(url)
            logger.info(f"检测到平台: {platform}")
            
            # 生成输出文件名
            if filename is None:
                # 使用 URL 的哈希作为文件名
                import hashlib
                filename = hashlib.md5(url.encode()).hexdigest()
            
            output_path = str(self.output_dir / filename)
            
            # 下载视频
            logger.info(f"开始下载视频: {url}")
            ydl_opts = self._get_ydl_opts(output_path)
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                video_file = ydl.prepare_filename(info)
                
                logger.info(f"视频下载完成: {video_file}")
                return video_file
        
        except DownloadError:
            raise
        except Exception as e:
            error_msg = f"视频下载失败: {str(e)}"
            logger.error(error_msg)
            raise DownloadError(error_msg)
    
    def is_cached(self, url: str, filename: Optional[str] = None) -> bool:
        """
        检查视频是否已缓存
        
        Args:
            url: 视频 URL
            filename: 自定义文件名（不包括扩展名）
        
        Returns:
            是否已缓存
        """
        try:
            if filename is None:
                import hashlib
                filename = hashlib.md5(url.encode()).hexdigest()
            
            # 检查是否存在任何匹配的文件
            for file in self.output_dir.glob(f"{filename}*"):
                if file.is_file():
                    logger.debug(f"视频已缓存: {file}")
                    return True
            
            return False
        except Exception as e:
            logger.error(f"检查缓存失败: {str(e)}")
            return False
    
    def get_cached_file(self, url: str, filename: Optional[str] = None) -> Optional[str]:
        """
        获取缓存的视频文件
        
        Args:
            url: 视频 URL
            filename: 自定义文件名（不包括扩展名）
        
        Returns:
            缓存文件路径，如果不存在则返回 None
        """
        try:
            if filename is None:
                import hashlib
                filename = hashlib.md5(url.encode()).hexdigest()
            
            # 查找匹配的文件
            for file in self.output_dir.glob(f"{filename}*"):
                if file.is_file():
                    logger.debug(f"返回缓存文件: {file}")
                    return str(file)
            
            return None
        except Exception as e:
            logger.error(f"获取缓存文件失败: {str(e)}")
            return None
    
    def delete_cached_file(self, url: str, filename: Optional[str] = None) -> bool:
        """
        删除缓存的视频文件
        
        Args:
            url: 视频 URL
            filename: 自定义文件名（不包括扩展名）
        
        Returns:
            是否成功删除
        """
        try:
            if filename is None:
                import hashlib
                filename = hashlib.md5(url.encode()).hexdigest()
            
            deleted = False
            for file in self.output_dir.glob(f"{filename}*"):
                if file.is_file():
                    file.unlink()
                    logger.info(f"删除缓存文件: {file}")
                    deleted = True
            
            return deleted
        except Exception as e:
            logger.error(f"删除缓存文件失败: {str(e)}")
            return False
    
    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        获取视频信息
        
        Args:
            url: 视频 URL
        
        Returns:
            视频信息字典，如果获取失败则返回 None
        """
        try:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "socket_timeout": DOWNLOAD_TIMEOUT,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                return {
                    "title": info.get("title"),
                    "duration": info.get("duration"),
                    "uploader": info.get("uploader"),
                    "upload_date": info.get("upload_date"),
                    "description": info.get("description"),
                    "thumbnail": info.get("thumbnail"),
                }
        except Exception as e:
            logger.error(f"获取视频信息失败: {str(e)}")
            return None
