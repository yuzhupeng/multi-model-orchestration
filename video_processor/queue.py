"""
消息队列系统 - 任务队列实现
"""
from queue import Queue, Empty
from typing import Optional, Dict, Any
from threading import Lock
import uuid
from datetime import datetime

from .models import Task, TaskStatus, TaskType
from .logger import get_logger
from .exceptions import QueueError

logger = get_logger(__name__)


class MessageQueue:
    """
    消息队列 - FIFO 任务队列
    
    特性：
    - FIFO 队列
    - 任务状态跟踪
    - 重试机制
    - 线程安全
    """
    
    def __init__(self, max_size: int = 10000):
        """
        初始化消息队列
        
        Args:
            max_size: 最大队列大小
        """
        if max_size <= 0:
            raise QueueError("max_size 必须大于 0")
        
        self.max_size = max_size
        self.queue: Queue[Task] = Queue(maxsize=max_size)
        self.tasks: Dict[str, Task] = {}  # 任务 ID 到任务的映射
        self.lock = Lock()
        self.completed_count = 0
        self.failed_count = 0
    
    def enqueue(self, task_type: TaskType, input_data: Dict[str, Any]) -> str:
        """
        入队任务
        
        Args:
            task_type: 任务类型
            input_data: 输入数据
        
        Returns:
            任务 ID
        
        Raises:
            QueueError: 如果队列已满
        """
        try:
            task_id = str(uuid.uuid4())
            task = Task(
                task_id=task_id,
                task_type=task_type,
                input_data=input_data,
                status=TaskStatus.PENDING,
            )
            
            # 尝试入队
            try:
                self.queue.put(task, block=False)
            except Exception as e:
                raise QueueError(f"队列已满: {str(e)}")
            
            # 记录任务
            with self.lock:
                self.tasks[task_id] = task
            
            logger.info(f"任务入队: {task_id} (类型: {task_type})")
            return task_id
        except QueueError:
            raise
        except Exception as e:
            raise QueueError(f"入队失败: {str(e)}")
    
    def dequeue(self, timeout: Optional[float] = None) -> Optional[Task]:
        """
        出队任务
        
        Args:
            timeout: 超时时间（秒）
        
        Returns:
            任务，如果队列为空则返回 None
        """
        try:
            task = self.queue.get(timeout=timeout)
            
            # 更新任务状态
            with self.lock:
                task.status = TaskStatus.RUNNING
                task.updated_at = datetime.now()
                self.tasks[task.task_id] = task
            
            logger.info(f"任务出队: {task.task_id}")
            return task
        except Empty:
            return None
        except Exception as e:
            logger.error(f"出队失败: {str(e)}")
            return None
    
    def mark_completed(self, task_id: str) -> bool:
        """
        标记任务为完成
        
        Args:
            task_id: 任务 ID
        
        Returns:
            是否成功
        """
        with self.lock:
            if task_id not in self.tasks:
                logger.warning(f"任务不存在: {task_id}")
                return False
            
            task = self.tasks[task_id]
            task.status = TaskStatus.COMPLETED
            task.updated_at = datetime.now()
            self.tasks[task_id] = task
            self.completed_count += 1
            
            logger.info(f"任务完成: {task_id}")
            return True
    
    def mark_failed(self, task_id: str, error_message: str = "") -> bool:
        """
        标记任务为失败
        
        Args:
            task_id: 任务 ID
            error_message: 错误消息
        
        Returns:
            是否成功
        """
        with self.lock:
            if task_id not in self.tasks:
                logger.warning(f"任务不存在: {task_id}")
                return False
            
            task = self.tasks[task_id]
            task.error_message = error_message
            task.updated_at = datetime.now()
            
            # 增加重试计数
            task.retry_count += 1
            
            # 检查是否应该重试
            if task.retry_count <= task.max_retries:
                task.status = TaskStatus.PENDING
                logger.info(f"任务重试: {task_id} (重试 {task.retry_count}/{task.max_retries})")
                
                # 重新入队
                try:
                    self.queue.put(task, block=False)
                except Exception as e:
                    logger.error(f"重新入队失败: {str(e)}")
                    task.status = TaskStatus.FAILED
                    self.failed_count += 1
            else:
                task.status = TaskStatus.FAILED
                self.failed_count += 1
                logger.error(f"任务失败（已达最大重试次数）: {task_id}")
            
            self.tasks[task_id] = task
            return True
    
    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态
        
        Args:
            task_id: 任务 ID
        
        Returns:
            任务状态信息
        """
        with self.lock:
            if task_id not in self.tasks:
                return None
            
            task = self.tasks[task_id]
            return {
                "task_id": task.task_id,
                "task_type": task.task_type.value,
                "status": task.status.value,
                "retry_count": task.retry_count,
                "max_retries": task.max_retries,
                "error_message": task.error_message,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
            }
    
    def get_queue_length(self) -> int:
        """获取队列长度"""
        return self.queue.qsize()
    
    def get_pending_count(self) -> int:
        """获取待处理任务数"""
        with self.lock:
            return sum(1 for task in self.tasks.values() if task.status == TaskStatus.PENDING)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取队列统计信息
        
        Returns:
            统计信息字典
        """
        with self.lock:
            total_tasks = len(self.tasks)
            pending_tasks = sum(1 for task in self.tasks.values() if task.status == TaskStatus.PENDING)
            running_tasks = sum(1 for task in self.tasks.values() if task.status == TaskStatus.RUNNING)
            completed_tasks = sum(1 for task in self.tasks.values() if task.status == TaskStatus.COMPLETED)
            failed_tasks = sum(1 for task in self.tasks.values() if task.status == TaskStatus.FAILED)
            
            return {
                "queue_length": self.queue.qsize(),
                "max_size": self.max_size,
                "total_tasks": total_tasks,
                "pending_tasks": pending_tasks,
                "running_tasks": running_tasks,
                "completed_tasks": completed_tasks,
                "failed_tasks": failed_tasks,
                "completed_count": self.completed_count,
                "failed_count": self.failed_count,
            }
    
    def clear(self) -> None:
        """清空队列"""
        with self.lock:
            # 清空队列
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                except Empty:
                    break
            
            # 清空任务映射
            self.tasks.clear()
            self.completed_count = 0
            self.failed_count = 0
            
            logger.info("队列已清空")
    
    def __len__(self) -> int:
        """获取队列长度"""
        return self.get_queue_length()
