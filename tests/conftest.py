"""
pytest 配置和 fixtures
"""
import pytest
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def temp_data_dir(tmp_path):
    """创建临时数据目录"""
    videos_dir = tmp_path / "videos"
    audio_dir = tmp_path / "audio"
    results_dir = tmp_path / "results"
    
    videos_dir.mkdir()
    audio_dir.mkdir()
    results_dir.mkdir()
    
    return {
        "root": tmp_path,
        "videos": videos_dir,
        "audio": audio_dir,
        "results": results_dir,
    }


@pytest.fixture
def sample_video_url():
    """示例视频 URL"""
    return "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


@pytest.fixture
def sample_transcript():
    """示例转录文本"""
    return """
    这是一个示例转录文本。
    它包含多行内容。
    用于测试总结生成器。
    """


@pytest.fixture
def sample_summary():
    """示例总结"""
    return "这是一个示例总结。"
