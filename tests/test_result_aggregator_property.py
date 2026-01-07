"""
结果聚合器属性测试
"""
import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from hypothesis import given, strategies as st
from video_processor.result_aggregator import ResultAggregator
from video_processor.models import ProcessingResult, VideoMetadata


# 定义生成策略
def video_metadata_strategy():
    """生成视频元数据的策略"""
    return st.builds(
        VideoMetadata,
        url=st.just("https://youtube.com/watch?v=test"),
        title=st.text(min_size=1, max_size=100),
        duration=st.integers(min_value=1, max_value=3600),
        platform=st.sampled_from(["youtube", "bilibili"]),
        upload_date=st.just("2024-01-01"),
        channel=st.text(min_size=1, max_size=50)
    )


def processing_result_strategy():
    """生成处理结果的策略"""
    return st.builds(
        ProcessingResult,
        task_id=st.text(min_size=1, max_size=20, alphabet=st.characters(blacklist_characters="/")),
        video_metadata=video_metadata_strategy(),
        video_path=st.just("/path/to/video.mp4"),
        audio_path=st.just("/path/to/audio.mp3"),
        transcript=st.text(min_size=1, max_size=1000),
        summary=st.text(min_size=1, max_size=500),
        processing_time=st.floats(min_value=0.1, max_value=100.0),
        created_at=st.just(datetime.now())
    )


class TestResultAggregatorProperty:
    """结果聚合器属性测试"""
    
    @pytest.fixture
    def temp_storage_dir(self):
        """创建临时存储目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def aggregator(self, temp_storage_dir):
        """创建结果聚合器实例"""
        return ResultAggregator(storage_dir=temp_storage_dir)
    
    @given(processing_result_strategy())
    def test_result_completeness_after_aggregation(self, result):
        """
        属性 5：结果完整性
        验证需求：10.1, 10.2
        
        对于任何完成的处理任务，聚合结果应包含所有必需的字段：
        视频元数据、转录文本和总结。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            aggregator = ResultAggregator(storage_dir=Path(tmpdir))
            
            # 聚合结果
            aggregated = aggregator.aggregate(
                task_id=result.task_id,
                video_metadata=result.video_metadata,
                video_path=result.video_path,
                audio_path=result.audio_path,
                transcript=result.transcript,
                summary=result.summary,
                processing_time=result.processing_time
            )
            
            # 验证所有必需字段都存在
            assert aggregated.task_id is not None
            assert aggregated.video_metadata is not None
            assert aggregated.video_metadata.url is not None
            assert aggregated.video_path is not None
            assert aggregated.audio_path is not None
            assert aggregated.transcript is not None
            assert aggregated.summary is not None
            assert aggregated.processing_time is not None
            assert aggregated.created_at is not None
    
    @given(processing_result_strategy())
    def test_result_persistence_round_trip(self, result):
        """
        属性 5：结果完整性（持久化往返）
        验证需求：10.2, 10.4
        
        对于任何保存的结果，保存后检索应返回相同的数据。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            aggregator = ResultAggregator(storage_dir=Path(tmpdir))
            
            # 保存结果
            aggregator.save(result)
            
            # 清空缓存以强制从文件读取
            aggregator._results_cache.clear()
            
            # 检索结果
            retrieved = aggregator.retrieve(result.task_id)
            
            # 验证检索的结果与原始结果相同
            assert retrieved is not None
            assert retrieved.task_id == result.task_id
            assert retrieved.video_metadata.url == result.video_metadata.url
            assert retrieved.transcript == result.transcript
            assert retrieved.summary == result.summary
            assert retrieved.processing_time == result.processing_time
    
    @given(st.lists(processing_result_strategy(), min_size=1, max_size=10))
    def test_result_query_returns_complete_data(self, results):
        """
        属性 5：结果完整性（查询）
        验证需求：10.3
        
        对于任何查询的结果，返回的字典应包含所有必需的字段。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            aggregator = ResultAggregator(storage_dir=Path(tmpdir))
            
            # 保存所有结果
            for result in results:
                aggregator.save(result)
            
            # 查询每个结果
            for result in results:
                query_result = aggregator.query(result.task_id)
                
                # 验证查询结果包含所有必需字段
                assert query_result is not None
                assert "task_id" in query_result
                assert "video_metadata" in query_result
                assert "video_path" in query_result
                assert "audio_path" in query_result
                assert "transcript" in query_result
                assert "summary" in query_result
                assert "processing_time" in query_result
                assert "created_at" in query_result
                
                # 验证字段值正确
                assert query_result["task_id"] == result.task_id
                assert query_result["transcript"] == result.transcript
                assert query_result["summary"] == result.summary
    
    @given(st.lists(processing_result_strategy(), min_size=1, max_size=10))
    def test_result_list_all_completeness(self, results):
        """
        属性 5：结果完整性（列表）
        验证需求：10.1
        
        对于任何保存的结果集合，列出所有结果应返回完整的结果对象。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            aggregator = ResultAggregator(storage_dir=Path(tmpdir))
            
            # 保存所有结果
            for result in results:
                aggregator.save(result)
            
            # 列出所有结果
            all_results = aggregator.list_all()
            
            # 验证返回的结果数量正确
            assert len(all_results) == len(results)
            
            # 验证每个结果都是完整的
            for result in all_results:
                assert result.task_id is not None
                assert result.video_metadata is not None
                assert result.video_path is not None
                assert result.audio_path is not None
                assert result.transcript is not None
                assert result.summary is not None
                assert result.processing_time is not None
                assert result.created_at is not None
    
    @given(st.lists(processing_result_strategy(), min_size=1, max_size=10))
    def test_result_to_dict_completeness(self, results):
        """
        属性 5：结果完整性（字典转换）
        验证需求：10.2
        
        对于任何处理结果，转换为字典应包含所有必需的字段。
        """
        for result in results:
            result_dict = result.to_dict()
            
            # 验证字典包含所有必需字段
            assert "task_id" in result_dict
            assert "video_metadata" in result_dict
            assert "video_path" in result_dict
            assert "audio_path" in result_dict
            assert "transcript" in result_dict
            assert "summary" in result_dict
            assert "processing_time" in result_dict
            assert "created_at" in result_dict
            
            # 验证嵌套的视频元数据字段
            assert "url" in result_dict["video_metadata"]
            assert "title" in result_dict["video_metadata"]
            assert "duration" in result_dict["video_metadata"]
            assert "platform" in result_dict["video_metadata"]
            assert "upload_date" in result_dict["video_metadata"]
            assert "channel" in result_dict["video_metadata"]
    
    @given(st.lists(processing_result_strategy(), min_size=2, max_size=10))
    def test_result_filtering_preserves_completeness(self, results):
        """
        属性 5：结果完整性（过滤）
        验证需求：10.5
        
        对于任何过滤的结果，返回的结果应保持完整性。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            aggregator = ResultAggregator(storage_dir=Path(tmpdir))
            
            # 保存所有结果
            for result in results:
                aggregator.save(result)
            
            # 按平台过滤
            if results:
                platform = results[0].video_metadata.platform
                filtered = aggregator.filter_by_source(platform)
                
                # 验证过滤结果的完整性
                for result in filtered:
                    assert result.task_id is not None
                    assert result.video_metadata is not None
                    assert result.video_path is not None
                    assert result.audio_path is not None
                    assert result.transcript is not None
                    assert result.summary is not None
                    assert result.processing_time is not None
                    assert result.created_at is not None
