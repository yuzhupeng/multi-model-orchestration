"""
消息队列单元测试
"""
import pytest
import time
from video_processor.queue import MessageQueue
from video_processor.models import TaskType, TaskStatus
from video_processor.exceptions import QueueError


class TestMessageQueueUnit:
    """消息队列单元测试"""
    
    def test_queue_initialization(self):
        """测试队列初始化"""
        queue = MessageQueue(max_size=100)
        assert queue.max_size == 100
        assert queue.get_queue_length() == 0
    
    def test_queue_enqueue(self):
        """测试任务入队"""
        queue = MessageQueue(max_size=100)
        task_id = queue.enqueue(TaskType.DOWNLOAD, {"url": "test"})
        
        assert task_id is not None
        assert queue.get_queue_length() == 1
    
    def test_queue_dequeue(self):
        """测试任务出队"""
        queue = MessageQueue(max_size=100)
        task_id = queue.enqueue(TaskType.DOWNLOAD, {"url": "test"})
        
        task = queue.dequeue(timeout=1)
        assert task is not None
        assert task.task_id == task_id
        assert task.status == TaskStatus.RUNNING
    
    def test_queue_empty_dequeue(self):
        """测试空队列出队"""
        queue = MessageQueue(max_size=100)
        task = queue.dequeue(timeout=0.1)
        assert task is None
    
    def test_queue_mark_completed(self):
        """测试标记任务完成"""
        queue = MessageQueue(max_size=100)
        task_id = queue.enqueue(TaskType.DOWNLOAD, {"url": "test"})
        
        task = queue.dequeue(timeout=1)
        queue.mark_completed(task_id)
        
        status = queue.get_status(task_id)
        assert status["status"] == TaskStatus.COMPLETED.value
    
    def test_queue_mark_failed(self):
        """测试标记任务失败"""
        queue = MessageQueue(max_size=100)
        task_id = queue.enqueue(TaskType.DOWNLOAD, {"url": "test"})
        
        task = queue.dequeue(timeout=1)
        queue.mark_failed(task_id, "测试错误")
        
        status = queue.get_status(task_id)
        assert status["status"] == TaskStatus.PENDING.value  # 应该重试
        assert status["retry_count"] == 1
    
    def test_queue_max_retries(self):
        """测试最大重试次数"""
        queue = MessageQueue(max_size=100)
        task_id = queue.enqueue(TaskType.DOWNLOAD, {"url": "test"})
        
        # 失败 3 次（重试 3 次）
        for i in range(3):
            task = queue.dequeue(timeout=1)
            assert task is not None
            queue.mark_failed(task_id, f"错误 {i+1}")
        
        # 第 4 次出队应该返回任务（最后一次重试）
        task = queue.dequeue(timeout=1)
        assert task is not None
        
        # 再次失败，这次应该标记为失败
        queue.mark_failed(task_id, "最终错误")
        
        status = queue.get_status(task_id)
        assert status["status"] == TaskStatus.FAILED.value
        assert status["retry_count"] == 4  # 初始 + 3 次重试 + 1 次最终失败
    
    def test_queue_get_status(self):
        """测试获取任务状态"""
        queue = MessageQueue(max_size=100)
        task_id = queue.enqueue(TaskType.DOWNLOAD, {"url": "test"})
        
        status = queue.get_status(task_id)
        assert status is not None
        assert status["task_id"] == task_id
        assert status["status"] == TaskStatus.PENDING.value
    
    def test_queue_get_nonexistent_status(self):
        """测试获取不存在的任务状态"""
        queue = MessageQueue(max_size=100)
        status = queue.get_status("nonexistent")
        assert status is None
    
    def test_queue_stats(self):
        """测试队列统计"""
        queue = MessageQueue(max_size=100)
        
        # 入队 3 个任务
        task_ids = []
        for i in range(3):
            task_id = queue.enqueue(TaskType.DOWNLOAD, {"index": i})
            task_ids.append(task_id)
        
        # 出队 1 个任务
        task = queue.dequeue(timeout=1)
        
        # 完成 1 个任务
        queue.mark_completed(task.task_id)
        
        stats = queue.get_stats()
        assert stats["total_tasks"] == 3
        assert stats["pending_tasks"] == 2
        assert stats["running_tasks"] == 0
        assert stats["completed_tasks"] == 1
    
    def test_queue_clear(self):
        """测试清空队列"""
        queue = MessageQueue(max_size=100)
        
        # 入队任务
        for i in range(5):
            queue.enqueue(TaskType.DOWNLOAD, {"index": i})
        
        # 清空队列
        queue.clear()
        
        assert queue.get_queue_length() == 0
        assert len(queue.tasks) == 0
    
    def test_queue_invalid_max_size(self):
        """测试无效的最大大小"""
        with pytest.raises(QueueError):
            MessageQueue(max_size=0)
        
        with pytest.raises(QueueError):
            MessageQueue(max_size=-1)
    
    def test_queue_fifo_order(self):
        """测试 FIFO 顺序"""
        queue = MessageQueue(max_size=100)
        
        # 入队任务
        task_ids = []
        for i in range(5):
            task_id = queue.enqueue(TaskType.DOWNLOAD, {"index": i})
            task_ids.append(task_id)
        
        # 出队任务
        dequeued_ids = []
        for _ in range(5):
            task = queue.dequeue(timeout=1)
            if task:
                dequeued_ids.append(task.task_id)
        
        # 验证顺序
        assert dequeued_ids == task_ids
    
    def test_queue_multiple_task_types(self):
        """测试多种任务类型"""
        queue = MessageQueue(max_size=100)
        
        # 入队不同类型的任务
        task_types = [TaskType.DOWNLOAD, TaskType.EXTRACT, TaskType.TRANSCRIBE, TaskType.SUMMARIZE]
        task_ids = []
        
        for task_type in task_types:
            task_id = queue.enqueue(task_type, {"type": task_type.value})
            task_ids.append(task_id)
        
        # 验证队列长度
        assert queue.get_queue_length() == 4
        
        # 出队并验证任务类型
        for i, expected_type in enumerate(task_types):
            task = queue.dequeue(timeout=1)
            assert task is not None
            assert task.task_type == expected_type
    
    def test_queue_pending_count(self):
        """测试待处理任务数"""
        queue = MessageQueue(max_size=100)
        
        # 入队 3 个任务
        for i in range(3):
            queue.enqueue(TaskType.DOWNLOAD, {"index": i})
        
        assert queue.get_pending_count() == 3
        
        # 出队 1 个任务
        queue.dequeue(timeout=1)
        
        assert queue.get_pending_count() == 2
