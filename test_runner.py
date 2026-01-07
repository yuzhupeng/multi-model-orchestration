#!/usr/bin/env python
"""Simple test runner to verify result aggregator implementation"""
import sys
import tempfile
from pathlib import Path

# Add current directory to path
sys.path.insert(0, '.')

from video_processor.result_aggregator import ResultAggregator
from video_processor.models import VideoMetadata, ProcessingResult

def test_basic_functionality():
    """Test basic result aggregator functionality"""
    print("Testing Result Aggregator...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        aggregator = ResultAggregator(storage_dir=Path(tmpdir))
        
        # Create sample metadata
        metadata = VideoMetadata(
            url="https://youtube.com/watch?v=test",
            title="Test Video",
            duration=600,
            platform="youtube",
            upload_date="2024-01-01",
            channel="Test Channel"
        )
        
        # Test aggregation
        result = aggregator.aggregate(
            task_id="task_001",
            video_metadata=metadata,
            video_path="/path/to/video.mp4",
            audio_path="/path/to/audio.mp3",
            transcript="This is a test transcript",
            summary="This is a test summary",
            processing_time=10.5
        )
        
        print(f"✓ Aggregation successful: {result.task_id}")
        
        # Test saving
        filepath = aggregator.save(result)
        print(f"✓ Save successful: {filepath}")
        
        # Test retrieval
        aggregator._results_cache.clear()
        retrieved = aggregator.retrieve("task_001")
        assert retrieved is not None
        assert retrieved.task_id == "task_001"
        print(f"✓ Retrieval successful: {retrieved.task_id}")
        
        # Test query
        query_result = aggregator.query("task_001")
        assert query_result is not None
        assert "created_at" in query_result
        print(f"✓ Query successful")
        
        # Test filtering
        filtered = aggregator.filter_by_source("youtube")
        assert len(filtered) == 1
        print(f"✓ Filtering successful: {len(filtered)} results")
        
        # Test stats
        stats = aggregator.get_stats()
        assert stats["total_results"] == 1
        print(f"✓ Stats successful: {stats['total_results']} total results")
        
        print("\n✓ All basic tests passed!")

if __name__ == "__main__":
    try:
        test_basic_functionality()
        sys.exit(0)
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
