"""
消息队列属性测试

Feature: multi-model-orchestration, Property 7: 消息队列任务分配
Validates: Requirements 7.1, 7.2
"""
import pytest
from hypothesis import given, strategies as st
from video_processor.queue import MessageQueue
from video_processor.models import TaskType, TaskStatus


class TestMessageQueueProperty:
    """消息队列属性测试"""
    
    @given(
        num_tasks=st.integers(min_value=1, max_value=100),
        task_types=st.lists(
            st.sampled_from([TaskType.DOWNLOAD, TaskType.EXTRACT, TaskType.TRANSCRIBE, TaskType.SUMMARIZE]),
            min_size=1,
            max_size=100
        )
    )
    def test_queue_task_assignment_property(self, num_tasks, task_types):
        """
        属性 7：消息队列任务分配
        
        对于任何入队的任务，消息队列应最终将其分配给可用的工作线程执行。
        
        验证：
        1. 任务成功入队
        2. 任务可以出队
        3. 任务状态正确转换
        """
        queue = MessageQueue(max_size=1000)
        
        # 入队任务
        task_ids = []
        for i in range(min(num_tasks, len(task_types))):
            task_type = task_types[i]
            input_data = {"index": i}
            task_id = queue.enqueue(task_type, input_data)
            task_ids.append(task_id)
        
        # 验证队列长度
        assert queue.get_queue_length() == len(task_ids)
        
        # 出队并处理任务
        dequeued_tasks = []
        for _ in range(len(task_ids)):
            task = queue.dequeue(timeout=1)
            if task:
                dequeued_tasks.append(task)
                # 验证任务状态为 RUNNING
                assert task.status == TaskStatus.RUNNING
                # 标记为完成
                queue.mark_completed(task.task_id)
        
        # 验证所有任务都被出队
        assert len(dequeued_tasks) == len(task_ids)
        
        # 验证所有任务都完成
        stats = queue.get_stats()
        assert stats["completed_tasks"] == len(task_ids)
    
    @given(
        num_tasks=st.integers(min_value=1, max_value=50),
    )
    def test_queue_fifo_order_property(self, num_tasks):
        """
        属性：FIFO 顺序
        
        对于任何任务序列，出队的顺序应该与入队的顺序相同。
        """
        queue = MessageQueue(max_size=1000)
        
        # 入队任务
        task_ids = []
        for i in range(num_tasks):
            task_id = queue.enqueue(TaskType.DOWNLOAD, {"index": i})
            task_ids.append(task_id)
        
        # 出队任务
        dequeued_ids = []
        for _ in range(num_tasks):
            task = queue.dequeue(timeout=1)
            if task:
                dequeued_ids.append(task.task_id)
        
        # 验证 FIFO 顺序
        assert dequeued_ids == task_ids
    
    @given(
        num_tasks=st.integers(min_value=1, max_value=50),
    )
    def test_queue_retry_mechanism_property(self, num_tasks):
        """
        属性 4：错误恢复
        
        当任何任务失败时，消息队列应重试最多 3 次，然后将其标记为失败。
        """
        queue = MessageQueue(max_size=1000)
        
        # 入队任务
        task_ids = []
        for i in range(num_tasks):
            task_id = queue.enqueue(TaskType.DOWNLOAD, {"index": i})
            task_ids.append(task_id)
        
        # 模拟任务失败和重试
        for task_id in task_ids:
            # 出队任务
            task = queue.dequeue(timeout=1)
            if task:
                # 标记为失败
                queue.mark_failed(task.task_id, "模拟错误")
                
                # 检查任务状态
                status = queue.get_status(task.task_id)
                if status["retry_count"] < 3:
                    # 应该重新入队
                    assert status["status"] == TaskStatus.PENDING.value
                else:
                    # 应该标记为失败
                    assert status["status"] == TaskStatus.FAILED.value
    
    @given(
        num_tasks=st.integers(min_value=1, max_value=100),
    )
    def test_queue_size_invariant(self, num_tasks):
        """
        不变量：队列大小不超过 max_size
        
        对于任何操作序列，队列大小应该始终不超过 max_size。
        """
        max_size = 50
        queue = MessageQueue(max_size=max_size)
        
        # 尝试入队任务
        for i in range(num_tasks):
            try:
                queue.enqueue(TaskType.DOWNLOAD, {"index": i})
                # 验证不变量
                assert queue.get_queue_length() <= max_size
            except Exception:
                # 队列满时会抛出异常
                assert queue.get_queue_length() == max_size
                break
    
    def test_queue_task_status_transitions(self):
        """
        属性：任务状态转换
        
        任务应该按照正确的状态转换：PENDING → RUNNING → COMPLETED/FAILED
        """
        queue = MessageQueue(max_size=100)
        
        # 入队任务
        task_id = queue.enqueue(TaskType.DOWNLOAD, {"url": "test"})
        
        # 验证初始状态
        status = queue.get_status(task_id)
        assert status["status"] == TaskStatus.PENDING.value
        
        # 出队任务
        task = queue.dequeue(timeout=1)
        assert task is not None
        
        # 验证运行状态
        status = queue.get_status(task_id)
        assert status["status"] == TaskStatus.RUNNING.value
        
        # 标记为完成
        queue.mark_completed(task_id)
        
        # 验证完成状态
        status = queue.get_status(task_id)
        assert status["status"] == TaskStatus.COMPLETED.value
