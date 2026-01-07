"""
结果聚合器 - 收集、格式化和持久化处理结果
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from video_processor.models import ProcessingResult, VideoMetadata
from video_processor.config import RESULTS_DIR
from video_processor.logger import get_logger

logger = get_logger(__name__)


class ResultAggregator:
    """结果聚合器 - 收集所有处理结果，格式化为 JSON，并持久化"""
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """
        初始化结果聚合器
        
        Args:
            storage_dir: 结果存储目录，默认为 RESULTS_DIR
        """
        self.storage_dir = storage_dir or RESULTS_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._results_cache: Dict[str, ProcessingResult] = {}
        logger.info(f"Result aggregator initialized with storage dir: {self.storage_dir}")
    
    def aggregate(self, task_id: str, video_metadata: VideoMetadata, 
                  video_path: str, audio_path: str, 
                  transcript: str, summary: str, 
                  processing_time: float) -> ProcessingResult:
        """
        聚合处理结果
        
        Args:
            task_id: 任务 ID
            video_metadata: 视频元数据
            video_path: 视频文件路径
            audio_path: 音频文件路径
            transcript: 转录文本
            summary: 总结文本
            processing_time: 处理时间（秒）
        
        Returns:
            ProcessingResult: 聚合后的处理结果
        """
        result = ProcessingResult(
            task_id=task_id,
            video_metadata=video_metadata,
            video_path=video_path,
            audio_path=audio_path,
            transcript=transcript,
            summary=summary,
            processing_time=processing_time,
            created_at=datetime.now()
        )
        
        # 缓存结果
        self._results_cache[task_id] = result
        logger.info(f"Result aggregated for task {task_id}")
        
        return result
    
    def save(self, result: ProcessingResult) -> str:
        """
        保存结果到文件系统
        
        Args:
            result: 处理结果
        
        Returns:
            str: 保存的文件路径
        """
        try:
            # 生成文件名
            filename = f"{result.task_id}.json"
            filepath = self.storage_dir / filename
            
            # 转换为字典并序列化
            result_dict = result.to_dict()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result_dict, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Result saved to {filepath}")
            return str(filepath)
        
        except Exception as e:
            logger.error(f"Failed to save result for task {result.task_id}: {str(e)}")
            raise
    
    def retrieve(self, task_id: str) -> Optional[ProcessingResult]:
        """
        检索结果
        
        Args:
            task_id: 任务 ID
        
        Returns:
            ProcessingResult: 处理结果，如果不存在则返回 None
        """
        # 先检查缓存
        if task_id in self._results_cache:
            logger.debug(f"Result retrieved from cache for task {task_id}")
            return self._results_cache[task_id]
        
        # 从文件系统读取
        try:
            filename = f"{task_id}.json"
            filepath = self.storage_dir / filename
            
            if not filepath.exists():
                logger.warning(f"Result file not found for task {task_id}")
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                result_dict = json.load(f)
            
            # 重构 ProcessingResult 对象
            result = self._dict_to_result(result_dict)
            
            # 更新缓存
            self._results_cache[task_id] = result
            logger.info(f"Result retrieved from file for task {task_id}")
            
            return result
        
        except Exception as e:
            logger.error(f"Failed to retrieve result for task {task_id}: {str(e)}")
            return None
    
    def query(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        查询结果（返回字典格式）
        
        Args:
            task_id: 任务 ID
        
        Returns:
            Dict: 结果字典，包含完整输出及时间戳
        """
        result = self.retrieve(task_id)
        if result is None:
            return None
        
        return result.to_dict()
    
    def filter_by_date(self, start_date: datetime, end_date: datetime) -> List[ProcessingResult]:
        """
        按日期过滤结果
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            List[ProcessingResult]: 符合条件的结果列表
        """
        results = []
        
        try:
            # 遍历结果目录中的所有文件
            for filepath in self.storage_dir.glob("*.json"):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        result_dict = json.load(f)
                    
                    result = self._dict_to_result(result_dict)
                    
                    # 检查日期范围
                    if start_date <= result.created_at <= end_date:
                        results.append(result)
                
                except Exception as e:
                    logger.warning(f"Failed to process result file {filepath}: {str(e)}")
                    continue
            
            logger.info(f"Found {len(results)} results between {start_date} and {end_date}")
            return results
        
        except Exception as e:
            logger.error(f"Failed to filter results by date: {str(e)}")
            return []
    
    def filter_by_source(self, platform: str) -> List[ProcessingResult]:
        """
        按来源（平台）过滤结果
        
        Args:
            platform: 平台名称（"youtube" 或 "bilibili"）
        
        Returns:
            List[ProcessingResult]: 符合条件的结果列表
        """
        results = []
        
        try:
            # 遍历结果目录中的所有文件
            for filepath in self.storage_dir.glob("*.json"):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        result_dict = json.load(f)
                    
                    result = self._dict_to_result(result_dict)
                    
                    # 检查平台
                    if result.video_metadata.platform == platform:
                        results.append(result)
                
                except Exception as e:
                    logger.warning(f"Failed to process result file {filepath}: {str(e)}")
                    continue
            
            logger.info(f"Found {len(results)} results from platform {platform}")
            return results
        
        except Exception as e:
            logger.error(f"Failed to filter results by source: {str(e)}")
            return []
    
    def filter_by_status(self, status: str) -> List[ProcessingResult]:
        """
        按状态过滤结果
        
        Args:
            status: 状态（"completed", "failed" 等）
        
        Returns:
            List[ProcessingResult]: 符合条件的结果列表
        """
        results = []
        
        try:
            # 遍历结果目录中的所有文件
            for filepath in self.storage_dir.glob("*.json"):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        result_dict = json.load(f)
                    
                    # 检查状态字段（如果存在）
                    if result_dict.get("status") == status:
                        result = self._dict_to_result(result_dict)
                        results.append(result)
                
                except Exception as e:
                    logger.warning(f"Failed to process result file {filepath}: {str(e)}")
                    continue
            
            logger.info(f"Found {len(results)} results with status {status}")
            return results
        
        except Exception as e:
            logger.error(f"Failed to filter results by status: {str(e)}")
            return []
    
    def list_all(self) -> List[ProcessingResult]:
        """
        列出所有结果
        
        Returns:
            List[ProcessingResult]: 所有结果列表
        """
        results = []
        
        try:
            # 遍历结果目录中的所有文件
            for filepath in self.storage_dir.glob("*.json"):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        result_dict = json.load(f)
                    
                    result = self._dict_to_result(result_dict)
                    results.append(result)
                
                except Exception as e:
                    logger.warning(f"Failed to process result file {filepath}: {str(e)}")
                    continue
            
            logger.info(f"Listed {len(results)} total results")
            return results
        
        except Exception as e:
            logger.error(f"Failed to list all results: {str(e)}")
            return []
    
    def delete(self, task_id: str) -> bool:
        """
        删除结果
        
        Args:
            task_id: 任务 ID
        
        Returns:
            bool: 是否成功删除
        """
        try:
            # 从缓存中删除
            if task_id in self._results_cache:
                del self._results_cache[task_id]
            
            # 从文件系统中删除
            filename = f"{task_id}.json"
            filepath = self.storage_dir / filename
            
            if filepath.exists():
                os.remove(filepath)
                logger.info(f"Result deleted for task {task_id}")
                return True
            
            logger.warning(f"Result file not found for task {task_id}")
            return False
        
        except Exception as e:
            logger.error(f"Failed to delete result for task {task_id}: {str(e)}")
            return False
    
    def clear_all(self) -> bool:
        """
        清空所有结果
        
        Returns:
            bool: 是否成功清空
        """
        try:
            # 清空缓存
            self._results_cache.clear()
            
            # 删除所有结果文件
            for filepath in self.storage_dir.glob("*.json"):
                try:
                    os.remove(filepath)
                except Exception as e:
                    logger.warning(f"Failed to delete file {filepath}: {str(e)}")
            
            logger.info("All results cleared")
            return True
        
        except Exception as e:
            logger.error(f"Failed to clear all results: {str(e)}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取结果统计信息
        
        Returns:
            Dict: 统计信息
        """
        try:
            all_results = self.list_all()
            
            stats = {
                "total_results": len(all_results),
                "cache_size": len(self._results_cache),
                "storage_dir": str(self.storage_dir),
                "results_by_platform": {},
                "total_processing_time": 0.0,
            }
            
            # 统计各平台的结果数
            for result in all_results:
                platform = result.video_metadata.platform or "unknown"
                stats["results_by_platform"][platform] = stats["results_by_platform"].get(platform, 0) + 1
                stats["total_processing_time"] += result.processing_time
            
            logger.info(f"Stats: {stats}")
            return stats
        
        except Exception as e:
            logger.error(f"Failed to get stats: {str(e)}")
            return {}
    
    @staticmethod
    def _dict_to_result(result_dict: Dict[str, Any]) -> ProcessingResult:
        """
        将字典转换为 ProcessingResult 对象
        
        Args:
            result_dict: 结果字典
        
        Returns:
            ProcessingResult: 处理结果对象
        """
        video_metadata = VideoMetadata(
            url=result_dict["video_metadata"]["url"],
            title=result_dict["video_metadata"].get("title"),
            duration=result_dict["video_metadata"].get("duration"),
            platform=result_dict["video_metadata"].get("platform"),
            upload_date=result_dict["video_metadata"].get("upload_date"),
            channel=result_dict["video_metadata"].get("channel"),
        )
        
        created_at = datetime.fromisoformat(result_dict["created_at"])
        
        return ProcessingResult(
            task_id=result_dict["task_id"],
            video_metadata=video_metadata,
            video_path=result_dict["video_path"],
            audio_path=result_dict["audio_path"],
            transcript=result_dict["transcript"],
            summary=result_dict["summary"],
            processing_time=result_dict["processing_time"],
            created_at=created_at,
        )
