"""
系统配置
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 数据目录
DATA_DIR = PROJECT_ROOT / "data"
VIDEOS_DIR = DATA_DIR / "videos"
AUDIO_DIR = DATA_DIR / "audio"
RESULTS_DIR = DATA_DIR / "results"

# 创建必要的目录
for directory in [DATA_DIR, VIDEOS_DIR, AUDIO_DIR, RESULTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# 缓存配置
CACHE_MAX_SIZE = 1000  # 最大缓存项数
CACHE_TTL = 3600  # 缓存过期时间（秒）

# 线程池配置
THREAD_POOL_SIZE = os.cpu_count() or 4  # 默认 CPU 核心数
THREAD_POOL_TIMEOUT = 300  # 线程超时时间（秒）

# 消息队列配置
QUEUE_MAX_SIZE = 10000  # 最大队列大小
TASK_MAX_RETRIES = 3  # 任务最大重试次数
TASK_RETRY_BACKOFF = 2.0  # 重试退避因子

# API 配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL_DEFAULT = "gpt-3.5-turbo"
OPENAI_MODEL_STANDARD = "gpt-4"
OPENAI_MODEL_ADVANCED = "gpt-4-turbo"

# 下载配置
DOWNLOAD_TIMEOUT = 300  # 下载超时时间（秒）
DOWNLOAD_RETRIES = 3  # 下载重试次数

# 日志配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# 性能配置
CACHE_HIT_THRESHOLD = 10  # 毫秒
PROCESSING_TIMEOUT = 3600  # 处理超时时间（秒）
