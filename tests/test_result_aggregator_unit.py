"""
结果聚合器单元测试
"""
import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from video_processor.result_aggregator import ResultAggregator
from video_processor.models import ProcessingResult, VideoMetadata


class TestResultAggregatorUnit:
    """结果聚合器单元测试"""
    
    @pytest.fixture
    def temp_storage_dir(self):
        """创建临时存储目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def aggregator(self, temp_storage_dir):
        """创建结果聚合器实例"""
        return ResultAggregator(storage_dir=temp_storage_dir)
    
    @pytest.fixture
    def sample_metadata(self):
        """创建示例视频元数据"""
        return VideoMetadata(
            url="https://youtube.com/watch?v=test123",
            title="Test Video",
            duration=600,
            platform="youtube",
            upload_date="2024-01-01",
            channel="Test Channel"
        )
    
    def test_aggregator_initialization(self, temp_storage_dir):
        """测试聚合器初始化"""
        aggregator = ResultAggregator(storage_dir=temp_storage_dir)
        assert aggregator.storage_dir == temp_storage_dir
        assert temp_storage_dir.exists()
    
    def test_aggregate_result(self, aggregator, sample_metadata):
        """测试聚合结果"""
        result = aggregator.aggregate(
            task_id="task_001",
            video_metadata=sample_metadata,
            video_path="/path/to/video.mp4",
            audio_path="/path/to/audio.mp3",
            transcript="This is a test transcript",
            summary="This is a test summary",
            processing_time=10.5
        )
        
        assert result.task_id == "task_001"
        assert result.video_metadata.url == sample_metadata.url
        assert result.transcript == "This is a test transcript"
        assert result.summary == "This is a test summary"
        assert result.processing_time == 10.5
    
    def test_save_result(self, aggregator, sample_metadata):
        """测试保存结果"""
        result = aggregator.aggregate(
            task_id="task_001",
            video_metadata=sample_metadata,
            video_path="/path/to/video.mp4",
            audio_path="/path/to/audio.mp3",
            transcript="Test transcript",
            summary="Test summary",
            processing_time=5.0
        )
        
        filepath = aggregator.save(result)
        
        # 验证文件存在
        assert Path(filepath).exists()
        
        # 验证文件内容
        with open(filepath, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        assert saved_data["task_id"] == "task_001"
        assert saved_data["transcript"] == "Test transcript"
        assert saved_data["summary"] == "Test summary"
    
    def test_retrieve_result(self, aggregator, sample_metadata):
        """测试检索结果"""
        # 创建并保存结果
        result = aggregator.aggregate(
            task_id="task_001",
            video_metadata=sample_metadata,
            video_path="/path/to/video.mp4",
            audio_path="/path/to/audio.mp3",
            transcript="Test transcript",
            summary="Test summary",
            processing_time=5.0
        )
        aggregator.save(result)
        
        # 清空缓存以测试从文件读取
        aggregator._results_cache.clear()
        
        # 检索结果
        retrieved = aggregator.retrieve("task_001")
        
        assert retrieved is not None
        assert retrieved.task_id == "task_001"
        assert retrieved.transcript == "Test transcript"
        assert retrieved.summary == "Test summary"
    
    def test_retrieve_nonexistent_result(self, aggregator):
        """测试检索不存在的结果"""
        result = aggregator.retrieve("nonexistent_task")
        assert result is None
    
    def test_query_result(self, aggregator, sample_metadata):
        """测试查询结果"""
        result = aggregator.aggregate(
            task_id="task_001",
            video_metadata=sample_metadata,
            video_path="/path/to/video.mp4",
            audio_path="/path/to/audio.mp3",
            transcript="Test transcript",
            summary="Test summary",
            processing_time=5.0
        )
        aggregator.save(result)
        
        # 查询结果
        query_result = aggregator.query("task_001")
        
        assert query_result is not None
        assert query_result["task_id"] == "task_001"
        assert query_result["transcript"] == "Test transcript"
        assert "created_at" in query_result
    
    def test_filter_by_date(self, aggregator, sample_metadata):
        """测试按日期过滤"""
        # 创建多个结果
        for i in range(3):
            result = aggregator.aggregate(
                task_id=f"task_{i:03d}",
                video_metadata=sample_metadata,
                video_path=f"/path/to/video{i}.mp4",
                audio_path=f"/path/to/audio{i}.mp3",
                transcript=f"Transcript {i}",
                summary=f"Summary {i}",
                processing_time=5.0
            )
            aggregator.save(result)
        
        # 按日期过滤
        now = datetime.now()
        start_date = now - timedelta(days=1)
        end_date = now + timedelta(days=1)
        
        filtered = aggregator.filter_by_date(start_date, end_date)
        
        assert len(filtered) == 3
    
    def test_filter_by_source(self, aggregator):
        """测试按来源过滤"""
        # 创建不同平台的结果
        youtube_metadata = VideoMetadata(
            url="https://youtube.com/watch?v=test",
            platform="youtube"
        )
        bilibili_metadata = VideoMetadata(
            url="https://bilibili.com/video/test",
            platform="bilibili"
        )
        
        result1 = aggregator.aggregate(
            task_id="task_001",
            video_metadata=youtube_metadata,
            video_path="/path/to/video1.mp4",
            audio_path="/path/to/audio1.mp3",
            transcript="YouTube transcript",
            summary="YouTube summary",
            processing_time=5.0
        )
        aggregator.save(result1)
        
        result2 = aggregator.aggregate(
            task_id="task_002",
            video_metadata=bilibili_metadata,
            video_path="/path/to/video2.mp4",
            audio_path="/path/to/audio2.mp3",
            transcript="Bilibili transcript",
            summary="Bilibili summary",
            processing_time=5.0
        )
        aggregator.save(result2)
        
        # 按来源过滤
        youtube_results = aggregator.filter_by_source("youtube")
        bilibili_results = aggregator.filter_by_source("bilibili")
        
        assert len(youtube_results) == 1
        assert len(bilibili_results) == 1
        assert youtube_results[0].video_metadata.platform == "youtube"
        assert bilibili_results[0].video_metadata.platform == "bilibili"
    
    def test_filter_by_status(self, aggregator, sample_metadata):
        """测试按状态过滤"""
        # 创建结果并手动添加状态字段
        result = aggregator.aggregate(
            task_id="task_001",
            video_metadata=sample_metadata,
            video_path="/path/to/video.mp4",
            audio_path="/path/to/audio.mp3",
            transcript="Test transcript",
            summary="Test summary",
            processing_time=5.0
        )
        
        # 保存结果并添加状态字段
        filepath = aggregator.storage_dir / "task_001.json"
        result_dict = result.to_dict()
        result_dict["status"] = "completed"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, ensure_ascii=False, indent=2)
        
        # 按状态过滤
        filtered = aggregator.filter_by_status("completed")
        
        assert len(filtered) == 1
        assert filtered[0].task_id == "task_001"
    
    def test_list_all(self, aggregator, sample_metadata):
        """测试列出所有结果"""
        # 创建多个结果
        for i in range(3):
            result = aggregator.aggregate(
                task_id=f"task_{i:03d}",
                video_metadata=sample_metadata,
                video_path=f"/path/to/video{i}.mp4",
                audio_path=f"/path/to/audio{i}.mp3",
                transcript=f"Transcript {i}",
                summary=f"Summary {i}",
                processing_time=5.0
            )
            aggregator.save(result)
        
        # 列出所有结果
        all_results = aggregator.list_all()
        
        assert len(all_results) == 3
    
    def test_delete_result(self, aggregator, sample_metadata):
        """测试删除结果"""
        result = aggregator.aggregate(
            task_id="task_001",
            video_metadata=sample_metadata,
            video_path="/path/to/video.mp4",
            audio_path="/path/to/audio.mp3",
            transcript="Test transcript",
            summary="Test summary",
            processing_time=5.0
        )
        aggregator.save(result)
        
        # 验证结果存在
        assert aggregator.retrieve("task_001") is not None
        
        # 删除结果
        success = aggregator.delete("task_001")
        
        assert success is True
        assert aggregator.retrieve("task_001") is None
    
    def test_delete_nonexistent_result(self, aggregator):
        """测试删除不存在的结果"""
        success = aggregator.delete("nonexistent_task")
        assert success is False
    
    def test_clear_all(self, aggregator, sample_metadata):
        """测试清空所有结果"""
        # 创建多个结果
        for i in range(3):
            result = aggregator.aggregate(
                task_id=f"task_{i:03d}",
                video_metadata=sample_metadata,
                video_path=f"/path/to/video{i}.mp4",
                audio_path=f"/path/to/audio{i}.mp3",
                transcript=f"Transcript {i}",
                summary=f"Summary {i}",
                processing_time=5.0
            )
            aggregator.save(result)
        
        # 验证结果存在
        assert len(aggregator.list_all()) == 3
        
        # 清空所有结果
        success = aggregator.clear_all()
        
        assert success is True
        assert len(aggregator.list_all()) == 0
    
    def test_get_stats(self, aggregator, sample_metadata):
        """测试获取统计信息"""
        # 创建多个结果
        for i in range(3):
            result = aggregator.aggregate(
                task_id=f"task_{i:03d}",
                video_metadata=sample_metadata,
                video_path=f"/path/to/video{i}.mp4",
                audio_path=f"/path/to/audio{i}.mp3",
                transcript=f"Transcript {i}",
                summary=f"Summary {i}",
                processing_time=5.0
            )
            aggregator.save(result)
        
        # 获取统计信息
        stats = aggregator.get_stats()
        
        assert stats["total_results"] == 3
        assert "youtube" in stats["results_by_platform"]
        assert stats["results_by_platform"]["youtube"] == 3
        assert stats["total_processing_time"] == 15.0
    
    def test_cache_retrieval(self, aggregator, sample_metadata):
        """测试缓存检索"""
        result = aggregator.aggregate(
            task_id="task_001",
            video_metadata=sample_metadata,
            video_path="/path/to/video.mp4",
            audio_path="/path/to/audio.mp3",
            transcript="Test transcript",
            summary="Test summary",
            processing_time=5.0
        )
        
        # 从缓存检索
        cached_result = aggregator.retrieve("task_001")
        
        assert cached_result is not None
        assert cached_result.task_id == "task_001"
        assert "task_001" in aggregator._results_cache
    
    def test_result_to_dict(self, aggregator, sample_metadata):
        """测试结果转换为字典"""
        result = aggregator.aggregate(
            task_id="task_001",
            video_metadata=sample_metadata,
            video_path="/path/to/video.mp4",
            audio_path="/path/to/audio.mp3",
            transcript="Test transcript",
            summary="Test summary",
            processing_time=5.0
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["task_id"] == "task_001"
        assert result_dict["video_metadata"]["url"] == sample_metadata.url
        assert result_dict["transcript"] == "Test transcript"
        assert result_dict["summary"] == "Test summary"
        assert "created_at" in result_dict
