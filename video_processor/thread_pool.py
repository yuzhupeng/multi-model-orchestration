"""
线程池管理系统
"""
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from typing import Callable, Any, Optional, Dict, List
from threading import Lock
import time

from .logger import get_logger
from .exceptions import ThreadPoolError
from .config import THREAD_POOL_SIZE, THREAD_POOL_TIMEOUT

logger = get_logger(__name__)


class ThreadPool:
    """
    线程池包装类
    
    特性：
    - 基于 ThreadPoolExecutor
    - 任务提交和监控
    - 优雅关闭
    - 线程安全
    """
    
    def __init__(self, max_workers: Optional[int] = None, timeout: int = THREAD_POOL_TIMEOUT):
        """
        初始化线程池
        
        Args:
            max_workers: 最大工作线程数，None 表示使用 CPU 核心数
            timeout: 线程超时时间（秒）
        """
        self.max_workers = max_workers or THREAD_POOL_SIZE
        self.timeout = timeout
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.futures: Dict[str, Future] = {}
        self.lock = Lock()
        self.submitted_count = 0
        self.completed_count = 0
        self.failed_count = 0
        self.is_shutdown = False
    
    def submit(self, task_id: str, func: Callable, *args, **kwargs) -> Optional[Future]:
        """
        提交任务到线程池
        
        Args:
            task_id: 任务 ID
            func: 可调用对象
            *args: 位置参数
            **kwargs: 关键字参数
        
        Returns:
            Future 对象，如果线程池已关闭则返回 None
        
        Raises:
            ThreadPoolError: 如果提交失败
        """
        if self.is_shutdown:
            raise ThreadPoolError("线程池已关闭")
        
        try:
            future = self.executor.submit(func, *args, **kwargs)
            
            with self.lock:
                self.futures[task_id] = future
                self.submitted_count += 1
            
            logger.info(f"任务提交到线程池: {task_id}")
            return future
        except Exception as e:
            raise ThreadPoolError(f"任务提交失败: {str(e)}")
    
    def get_result(self, task_id: str, timeout: Optional[float] = None) -> Optional[Any]:
        """
        获取任务结果
        
        Args:
            task_id: 任务 ID
            timeout: 超时时间（秒）
        
        Returns:
            任务结果，如果任务不存在或超时则返回 None
        """
        with self.lock:
            if task_id not in self.futures:
                logger.warning(f"任务不存在: {task_id}")
                return None
            
            future = self.futures[task_id]
        
        try:
            result = future.result(timeout=timeout or self.timeout)
            logger.info(f"任务完成: {task_id}")
            return result
        except Exception as e:
            logger.error(f"获取任务结果失败: {task_id}, 错误: {str(e)}")
            return None
    
    def is_done(self, task_id: str) -> bool:
        """
        检查任务是否完成
        
        Args:
            task_id: 任务 ID
        
        Returns:
            是否完成
        """
        with self.lock:
            if task_id not in self.futures:
                return False
            return self.futures[task_id].done()
    
    def cancel(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务 ID
        
        Returns:
            是否成功取消
        """
        with self.lock:
            if task_id not in self.futures:
                return False
            
            future = self.futures[task_id]
            cancelled = future.cancel()
            
            if cancelled:
                logger.info(f"任务已取消: {task_id}")
            
            return cancelled
    
    def wait_all(self, timeout: Optional[float] = None) -> bool:
        """
        等待所有任务完成
        
        Args:
            timeout: 超时时间（秒）
        
        Returns:
            是否所有任务都完成
        """
        with self.lock:
            futures = list(self.futures.values())
        
        try:
            for future in as_completed(futures, timeout=timeout):
                try:
                    future.result()
                    self.completed_count += 1
                except Exception as e:
                    logger.error(f"任务执行失败: {str(e)}")
                    self.failed_count += 1
            
            return True
        except Exception as e:
            logger.error(f"等待任务超时: {str(e)}")
            return False
    
    def get_active_count(self) -> int:
        """获取活跃线程数"""
        with self.lock:
            active = sum(1 for future in self.futures.values() if not future.done())
            return active
    
    def get_pending_count(self) -> int:
        """获取待处理任务数"""
        with self.lock:
            pending = sum(1 for future in self.futures.values() if not future.running() and not future.done())
            return pending
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取线程池统计信息
        
        Returns:
            统计信息字典
        """
        with self.lock:
            total_tasks = len(self.futures)
            active_tasks = sum(1 for future in self.futures.values() if future.running())
            pending_tasks = sum(1 for future in self.futures.values() if not future.running() and not future.done())
            completed_tasks = sum(1 for future in self.futures.values() if future.done() and not future.cancelled())
            cancelled_tasks = sum(1 for future in self.futures.values() if future.cancelled())
            
            return {
                "max_workers": self.max_workers,
                "total_tasks": total_tasks,
                "active_tasks": active_tasks,
                "pending_tasks": pending_tasks,
                "completed_tasks": completed_tasks,
                "cancelled_tasks": cancelled_tasks,
                "submitted_count": self.submitted_count,
                "completed_count": self.completed_count,
                "failed_count": self.failed_count,
                "is_shutdown": self.is_shutdown,
            }
    
    def shutdown(self, wait: bool = True) -> None:
        """
        关闭线程池
        
        Args:
            wait: 是否等待所有任务完成
        """
        if self.is_shutdown:
            logger.warning("线程池已关闭")
            return
        
        try:
            self.executor.shutdown(wait=wait)
            self.is_shutdown = True
            logger.info("线程池已关闭")
        except Exception as e:
            logger.error(f"关闭线程池失败: {str(e)}")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.shutdown(wait=True)
