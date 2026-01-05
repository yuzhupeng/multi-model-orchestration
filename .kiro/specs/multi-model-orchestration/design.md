# 设计文档：多模型视频处理编排系统

## 概述

本系统是一个高效的视频处理编排平台，采用模块化架构设计。系统通过以下核心机制实现高效的工程化编排与多模型动态调用：

1. **管道编排引擎**：支持顺序执行、并行执行和条件分支
2. **动态模型调用**：根据输入和中间结果动态选择和调用不同的处理模型
3. **缓存层**：使用 LRU 缓存减少重复处理
4. **消息队列**：实现任务的异步解耦处理
5. **线程池**：支持并发处理多个视频
6. **错误恢复**：完善的错误处理和重试机制

## 架构设计

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    API 入口层                                │
│              (接收视频链接和处理请求)                        │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                  编排器 (Orchestrator)                       │
│         (协调管道执行、错误处理、结果聚合)                   │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┬──────────────┐
        │            │            │              │
┌───────▼──┐  ┌──────▼──┐  ┌─────▼──┐  ┌──────▼──┐
│ 下载器   │  │ 提取器  │  │ 转录器 │  │ 总结器  │
│ (DL)    │  │ (AE)   │  │ (TG)  │  │ (SG)   │
└───────┬──┘  └──────┬──┘  └─────┬──┘  └──────┬──┘
        │            │            │            │
        └────────────┼────────────┼────────────┘
                     │
        ┌────────────▼────────────┐
        │   缓存层 (Cache)        │
        │  (LRU 缓存策略)         │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────┐
        │  消息队列 (MQ)          │
        │  (任务队列、重试机制)   │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────┐
        │  线程池 (Thread Pool)   │
        │  (并发执行、资源管理)   │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────┐
        │  结果聚合器 (Aggregator)│
        │  (JSON 格式化、持久化)  │
        └────────────────────────┘
```

## 核心组件设计

### 1. 编排器 (Orchestrator)

**职责**：
- 协调管道各阶段的执行
- 管理任务流转和状态转换
- 处理错误和重试逻辑
- 聚合最终结果

**接口**：
```python
class Orchestrator:
    def process_video(self, video_url: str) -> Dict[str, Any]
        """处理单个视频，返回完整的处理结果"""
    
    def process_batch(self, video_urls: List[str]) -> List[Dict[str, Any]]
        """批量处理多个视频"""
    
    def get_status(self, task_id: str) -> Dict[str, Any]
        """获取任务处理状态"""
```

**执行流程**：
```
输入视频链接
    ↓
检查缓存 (是否已处理过)
    ↓ (缓存未命中)
入队下载任务到消息队列
    ↓
工作线程执行下载
    ↓
入队音频提取任务
    ↓
工作线程执行提取
    ↓
入队转录任务
    ↓
工作线程执行转录
    ↓
入队总结任务
    ↓
工作线程执行总结
    ↓
聚合结果并缓存
    ↓
返回完整结果
```

### 2. 视频下载器 (Video Downloader)

**职责**：
- 支持 YouTube 和 Bilibili 平台
- 处理下载失败和重试
- 管理本地存储

**实现方案**：
- 使用 `yt-dlp` 库支持多平台下载
- 实现平台检测逻辑
- 支持并发下载（线程池）

**接口**：
```python
class VideoDownloader:
    def download(self, url: str) -> str
        """下载视频，返回本地文件路径"""
    
    def is_cached(self, url: str) -> bool
        """检查视频是否已缓存"""
```

### 3. 音频提取器 (Audio Extractor)

**职责**：
- 从视频中提取音频
- 支持多种音频格式
- 处理提取失败

**实现方案**：
- 使用 `ffmpeg` 进行音频提取
- 支持并发提取（线程池）
- 实现音频格式转换

**接口**：
```python
class AudioExtractor:
    def extract(self, video_path: str) -> str
        """提取音频，返回音频文件路径"""
```

### 4. 转录生成器 (Transcript Generator)

**职责**：
- 将音频转换为文本
- 支持多种语言
- 处理转录失败

**实现方案**：
- 使用 OpenAI Whisper API 或本地模型
- 支持并发转录（线程池）
- 实现语言自动检测

**接口**：
```python
class TranscriptGenerator:
    def generate(self, audio_path: str) -> str
        """生成转录文本"""
```

### 5. 总结生成器 (Summary Generator)

**职责**：
- 调用大语言模型生成总结
- 支持多种 LLM 模型
- 处理生成失败

**实现方案**：
- 支持 OpenAI GPT、Claude、本地 LLM 等
- 实现模型动态选择逻辑
- 支持并发生成（线程池）

**接口**：
```python
class SummaryGenerator:
    def generate(self, transcript: str, model: str = "gpt-3.5-turbo") -> str
        """生成总结"""
    
    def select_model(self, transcript_length: int) -> str
        """根据转录长度动态选择模型"""
```

### 6. 缓存系统 (Cache System)

**职责**：
- 存储中间结果
- 实现 LRU 驱逐策略
- 支持快速查询

**实现方案**：
- 使用 Python `functools.lru_cache` 或自定义 LRU 缓存
- 支持内存缓存和持久化缓存
- 实现缓存键生成策略

**缓存键设计**：
```
video_download: hash(url)
audio_extract: hash(video_path)
transcript: hash(audio_path)
summary: hash(transcript + model)
```

**接口**：
```python
class Cache:
    def get(self, key: str) -> Optional[Any]
        """获取缓存值"""
    
    def set(self, key: str, value: Any, ttl: int = None) -> None
        """设置缓存值"""
    
    def clear(self) -> None
        """清空缓存"""
```

### 7. 消息队列 (Message Queue)

**职责**：
- 管理任务队列
- 实现任务分配
- 处理重试逻辑

**实现方案**：
- 使用 `queue.Queue` 或 `celery` 等消息队列库
- 实现任务优先级
- 支持任务重试（最多 3 次）

**任务类型**：
```python
class Task:
    task_id: str
    task_type: str  # "download", "extract", "transcribe", "summarize"
    input_data: Dict[str, Any]
    retry_count: int = 0
    max_retries: int = 3
    status: str = "pending"  # "pending", "running", "completed", "failed"
```

**接口**：
```python
class MessageQueue:
    def enqueue(self, task: Task) -> str
        """入队任务，返回任务 ID"""
    
    def dequeue(self) -> Optional[Task]
        """出队任务"""
    
    def get_status(self, task_id: str) -> str
        """获取任务状态"""
```

### 8. 线程池 (Thread Pool)

**职责**：
- 管理工作线程
- 分配任务给工作线程
- 监控线程状态

**实现方案**：
- 使用 `concurrent.futures.ThreadPoolExecutor`
- 配置线程数（默认 CPU 核心数）
- 实现线程监控和日志

**接口**：
```python
class ThreadPool:
    def submit(self, task: Task) -> Future
        """提交任务到线程池"""
    
    def get_active_count(self) -> int
        """获取活跃线程数"""
    
    def shutdown(self, wait: bool = True) -> None
        """关闭线程池"""
```

### 9. 结果聚合器 (Result Aggregator)

**职责**：
- 收集所有处理结果
- 格式化为 JSON
- 持久化结果

**实现方案**：
- 实现结果数据模型
- 支持 JSON 序列化
- 支持数据库或文件系统存储

**结果数据模型**：
```python
class ProcessingResult:
    task_id: str
    video_url: str
    video_path: str
    audio_path: str
    transcript: str
    summary: str
    metadata: Dict[str, Any]
    timestamps: Dict[str, datetime]
    status: str
```

**接口**：
```python
class ResultAggregator:
    def aggregate(self, task_id: str) -> ProcessingResult
        """聚合结果"""
    
    def save(self, result: ProcessingResult) -> None
        """保存结果"""
    
    def retrieve(self, task_id: str) -> ProcessingResult
        """检索结果"""
```

### 10. 错误处理和日志 (Error Handling & Logging)

**职责**：
- 记录系统日志
- 处理异常
- 实现错误恢复

**实现方案**：
- 使用 Python `logging` 模块
- 实现自定义异常类
- 支持日志级别过滤

**异常类**：
```python
class VideoProcessingError(Exception):
    """基础异常"""

class DownloadError(VideoProcessingError):
    """下载失败"""

class ExtractionError(VideoProcessingError):
    """提取失败"""

class TranscriptionError(VideoProcessingError):
    """转录失败"""

class SummarizationError(VideoProcessingError):
    """总结失败"""
```

## 数据模型

### 视频元数据
```python
class VideoMetadata:
    url: str
    title: str
    duration: int  # 秒
    platform: str  # "youtube" 或 "bilibili"
    upload_date: str
    channel: str
```

### 处理任务
```python
class ProcessingTask:
    task_id: str
    video_url: str
    status: str  # "pending", "downloading", "extracting", "transcribing", "summarizing", "completed", "failed"
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str]
```

### 处理结果
```python
class ProcessingResult:
    task_id: str
    video_metadata: VideoMetadata
    video_path: str
    audio_path: str
    transcript: str
    summary: str
    processing_time: float  # 秒
    created_at: datetime
```

## 动态模型调用机制

### 模型选择策略

系统根据以下因素动态选择模型：

1. **转录长度**：
   - 短转录 (< 1000 字)：使用轻量级模型 (gpt-3.5-turbo)
   - 中等转录 (1000-5000 字)：使用标准模型 (gpt-4)
   - 长转录 (> 5000 字)：使用专业模型 (gpt-4-turbo)

2. **内容类型**：
   - 技术内容：使用技术专家模型
   - 新闻内容：使用新闻总结模型
   - 娱乐内容：使用通用模型

3. **用户偏好**：
   - 支持用户指定模型
   - 支持模型优先级配置

### 实现方案

```python
class ModelSelector:
    def select_model(self, 
                    transcript: str, 
                    content_type: str = "general",
                    user_preference: str = None) -> str:
        """根据多个因素选择最合适的模型"""
        
        if user_preference:
            return user_preference
        
        transcript_length = len(transcript)
        
        if content_type == "technical":
            if transcript_length < 1000:
                return "gpt-3.5-turbo"
            elif transcript_length < 5000:
                return "gpt-4"
            else:
                return "gpt-4-turbo"
        
        # 其他内容类型的逻辑...
        return "gpt-3.5-turbo"
```

## 并发处理机制

### 多线程架构

```
主线程 (Main Thread)
    ↓
编排器 (Orchestrator)
    ↓
消息队列 (Message Queue)
    ↓
线程池 (Thread Pool)
    ├─ 工作线程 1 (Worker 1)
    ├─ 工作线程 2 (Worker 2)
    ├─ 工作线程 3 (Worker 3)
    └─ 工作线程 N (Worker N)
```

### 任务分配策略

1. **FIFO 队列**：按提交顺序处理任务
2. **优先级队列**：支持任务优先级
3. **负载均衡**：自动分配给最空闲的工作线程

## 缓存策略

### LRU 缓存实现

```python
class LRUCache:
    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.access_order = []
        self.max_size = max_size
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        return None
    
    def set(self, key: str, value: Any) -> None:
        if key in self.cache:
            self.access_order.remove(key)
        elif len(self.cache) >= self.max_size:
            # 驱逐最近最少使用的项
            lru_key = self.access_order.pop(0)
            del self.cache[lru_key]
        
        self.cache[key] = value
        self.access_order.append(key)
```

### 缓存命中率优化

- 使用内容哈希作为缓存键
- 支持缓存预热
- 实现缓存统计和监控

## 错误处理和恢复

### 重试策略

```python
class RetryStrategy:
    def __init__(self, max_retries: int = 3, backoff_factor: float = 2.0):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
    
    def execute_with_retry(self, func, *args, **kwargs):
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                wait_time = self.backoff_factor ** attempt
                time.sleep(wait_time)
```

### 错误分类和处理

| 错误类型 | 处理方式 | 重试 |
|---------|--------|------|
| 网络错误 | 重试 | 是 |
| 超时错误 | 重试 | 是 |
| 格式错误 | 记录并跳过 | 否 |
| 认证错误 | 记录并停止 | 否 |
| 系统错误 | 记录并恢复 | 是 |

## 正确性属性

一个属性是一个特征或行为，应该在系统的所有有效执行中保持真实——本质上是关于系统应该做什么的形式化陈述。属性充当人类可读规范和机器可验证正确性保证之间的桥梁。

### 属性 1：管道顺序执行
**验证需求**：需求 5.1

对于任何视频 URL，执行管道应按以下顺序进行：下载 → 提取音频 → 生成转录 → 生成总结。任何阶段的输出应该是下一阶段的输入。

### 属性 2：缓存一致性
**验证需求**：需求 6.1, 6.2

对于任何已缓存的结果，第二次查询应返回与第一次相同的结果，而不重新处理。

### 属性 3：并发处理隔离
**验证需求**：需求 8.1, 8.3

对于任何两个并发处理的视频，一个视频的处理不应影响另一个视频的结果。

### 属性 4：错误恢复
**验证需求**：需求 9.2

当任何管道阶段失败时，系统应记录错误并允许重试，最多 3 次。

### 属性 5：结果完整性
**验证需求**：需求 10.1, 10.2

对于任何完成的处理任务，聚合结果应包含所有必需的字段：视频元数据、转录文本和总结。

### 属性 6：缓存驱逐
**验证需求**：需求 6.3

当缓存满时，最近最少使用的项应被驱逐，新项应被添加。

### 属性 7：消息队列任务分配
**验证需求**：需求 7.1, 7.2

对于任何入队的任务，消息队列应最终将其分配给可用的工作线程执行。

### 属性 8：多线程线程安全
**验证需求**：需求 8.1, 8.2

对于任何共享资源（缓存、队列、结果存储），并发访问应不导致数据竞争或不一致。

## 测试策略

### 单元测试

- 测试每个组件的核心功能
- 测试边界情况和错误条件
- 测试组件间的接口

### 属性测试

- 使用 `hypothesis` 库进行属性测试
- 为每个正确性属性编写一个属性测试
- 最少 100 次迭代验证

### 集成测试

- 测试完整的管道流程
- 测试多个视频的并发处理
- 测试缓存和消息队列的交互

### 性能测试

- 测试缓存命中率
- 测试并发处理性能
- 测试内存使用情况
