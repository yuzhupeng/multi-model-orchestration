# 多模型视频处理编排系统

一个高效的视频处理编排平台，支持从多个平台下载视频、提取音频、生成转录文本和总结。

## 功能特性

- 🎥 **多平台支持**：支持 YouTube 和 Bilibili 视频下载
- 🔄 **智能编排**：支持顺序执行、并行执行和条件分支
- 🧠 **动态模型调用**：根据内容动态选择最合适的 LLM 模型
- ⚡ **高性能**：LRU 缓存、消息队列、多线程并发处理
- 🛡️ **可靠性**：完善的错误处理和重试机制
- 📊 **可观测性**：详细的日志和监控

## 系统架构

```
API 入口层
    ↓
编排器 (Orchestrator)
    ↓
下载器 → 提取器 → 转录器 → 总结器
    ↓
缓存层 (LRU Cache)
    ↓
消息队列 (Message Queue)
    ↓
线程池 (Thread Pool)
    ↓
结果聚合器 (Result Aggregator)
```

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境

1. 复制 `.env.example` 为 `.env`
2. 填入你的 OpenAI API 密钥

```bash
cp .env.example .env
# 编辑 .env 文件，填入 OPENAI_API_KEY
```

### 使用示例

```python
from video_processor import Orchestrator

# 创建编排器
orchestrator = Orchestrator()

# 处理单个视频
result = orchestrator.process_video("https://www.youtube.com/watch?v=...")

# 批量处理视频
results = orchestrator.process_batch([
    "https://www.youtube.com/watch?v=...",
    "https://www.bilibili.com/video/...",
])

# 获取任务状态
status = orchestrator.get_status(task_id)
```

## 项目结构

```
video_processor/
├── __init__.py              # 包初始化
├── models.py                # 数据模型
├── exceptions.py            # 异常定义
├── logger.py                # 日志系统
├── config.py                # 配置文件
├── cache.py                 # 缓存系统
├── queue.py                 # 消息队列
├── thread_pool.py           # 线程池
├── downloader.py            # 视频下载器
├── extractor.py             # 音频提取器
├── transcriber.py           # 转录生成器
├── summarizer.py            # 总结生成器
├── orchestrator.py          # 编排器
└── aggregator.py            # 结果聚合器

tests/
├── test_cache.py            # 缓存测试
├── test_queue.py            # 队列测试
├── test_downloader.py       # 下载器测试
├── test_orchestrator.py     # 编排器测试
└── ...

data/
├── videos/                  # 下载的视频
├── audio/                   # 提取的音频
└── results/                 # 处理结果
```

## 核心组件

### 1. 编排器 (Orchestrator)
协调管道各阶段的执行，管理任务流转和状态转换。

### 2. 缓存系统 (Cache)
使用 LRU 策略缓存中间结果，减少重复处理。

### 3. 消息队列 (Message Queue)
实现任务的异步解耦处理，支持重试机制。

### 4. 线程池 (Thread Pool)
支持并发处理多个视频，提高系统吞吐量。

### 5. 处理器
- **下载器**：支持 YouTube 和 Bilibili
- **提取器**：使用 ffmpeg 提取音频
- **转录器**：使用 OpenAI Whisper 生成转录
- **总结器**：使用 GPT 模型生成总结

## 配置选项

### 缓存配置
- `CACHE_MAX_SIZE`: 最大缓存项数（默认 1000）
- `CACHE_TTL`: 缓存过期时间（默认 3600 秒）

### 线程池配置
- `THREAD_POOL_SIZE`: 线程数（默认 CPU 核心数）
- `THREAD_POOL_TIMEOUT`: 线程超时时间（默认 300 秒）

### 消息队列配置
- `QUEUE_MAX_SIZE`: 最大队列大小（默认 10000）
- `TASK_MAX_RETRIES`: 任务最大重试次数（默认 3）
- `TASK_RETRY_BACKOFF`: 重试退避因子（默认 2.0）

## 测试

运行所有测试：

```bash
pytest
```

运行特定测试：

```bash
pytest tests/test_cache.py -v
```

运行属性测试：

```bash
pytest tests/test_cache.py::test_lru_cache_property -v
```

## 性能指标

- 缓存命中时间：< 10ms
- 并发处理能力：支持 N 个视频同时处理（N = CPU 核心数）
- 内存使用：< 1GB（取决于缓存大小和视频数量）

## 错误处理

系统实现了完善的错误处理机制：

- **网络错误**：自动重试（最多 3 次）
- **超时错误**：自动重试（最多 3 次）
- **格式错误**：记录并跳过
- **认证错误**：记录并停止
- **系统错误**：记录并恢复

## 日志

系统使用 Python 标准 logging 模块，支持多个日志级别：

- `DEBUG`: 调试信息
- `INFO`: 一般信息
- `WARNING`: 警告信息
- `ERROR`: 错误信息
- `CRITICAL`: 严重错误

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

如有问题，请提交 Issue 或联系开发者。
