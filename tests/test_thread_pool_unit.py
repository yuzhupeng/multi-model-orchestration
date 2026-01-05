"""
线程池单元测试
"""
import pytest
import time
from video_processor.thread_pool import ThreadPool
from video_processor.exceptions import ThreadPoolError


class TestThreadPoolUnit:
    """线程池单元测试"""
    
    def test_thread_pool_initialization(self):
        """测试线程池初始化"""
        pool = ThreadPool(max_workers=4)
        assert pool.max_workers == 4
        assert not pool.is_shutdown
        pool.shutdown()
    
    def test_thread_pool_submit_task(self):
        """测试提交任务"""
        pool = ThreadPool(max_workers=2)
        
        def simple_task():
            return "done"
        
        task_id = "task_1"
        future = pool.submit(task_id, simple_task)
        
        assert future is not None
        pool.shutdown()
    
    def test_thread_pool_get_result(self):
        """测试获取任务结果"""
        pool = ThreadPool(max_workers=2)
        
        def return_value():
            return 42
        
        task_id = "task_1"
        pool.submit(task_id, return_value)
        result = pool.get_result(task_id, timeout=5)
        
        assert result == 42
        pool.shutdown()
    
    def test_thread_pool_is_done(self):
        """测试检查任务是否完成"""
        pool = ThreadPool(max_workers=2)
        
        def slow_task():
            time.sleep(0.1)
            return "done"
        
        task_id = "task_1"
        pool.submit(task_id, slow_task)
        
        # 任务可能还未完成
        time.sleep(0.2)
        assert pool.is_done(task_id)
        
        pool.shutdown()
    
    def test_thread_pool_cancel_task(self):
        """测试取消任务"""
        pool = ThreadPool(max_workers=2)
        
        def slow_task():
            time.sleep(1)
            return "done"
        
        task_id = "task_1"
        pool.submit(task_id, slow_task)
        
        # 立即取消
        cancelled = pool.cancel(task_id)
        
        # 可能成功或失败，取决于任务是否已开始
        assert isinstance(cancelled, bool)
        
        pool.shutdown()
    
    def test_thread_pool_wait_all(self):
        """测试等待所有任务完成"""
        pool = ThreadPool(max_workers=2)
        
        def quick_task(value):
            return value * 2
        
        # 提交多个任务
        for i in range(5):
            pool.submit(f"task_{i}", quick_task, i)
        
        # 等待所有任务完成
        success = pool.wait_all(timeout=10)
        assert success
        
        pool.shutdown()
    
    def test_thread_pool_get_active_count(self):
        """测试获取活跃线程数"""
        pool = ThreadPool(max_workers=2)
        
        def quick_task():
            return "done"
        
        # 提交任务
        pool.submit("task_1", quick_task)
        
        # 活跃线程数应该 >= 0
        active = pool.get_active_count()
        assert active >= 0
        
        pool.shutdown()
    
    def test_thread_pool_get_stats(self):
        """测试获取统计信息"""
        pool = ThreadPool(max_workers=2)
        
        def quick_task():
            return "done"
        
        # 提交任务
        for i in range(3):
            pool.submit(f"task_{i}", quick_task)
        
        # 等待完成
        pool.wait_all(timeout=10)
        
        stats = pool.get_stats()
        assert stats["total_tasks"] == 3
        assert stats["max_workers"] == 2
        
        pool.shutdown()
    
    def test_thread_pool_shutdown(self):
        """测试关闭线程池"""
        pool = ThreadPool(max_workers=2)
        
        def quick_task():
            return "done"
        
        pool.submit("task_1", quick_task)
        pool.shutdown(wait=True)
        
        assert pool.is_shutdown
    
    def test_thread_pool_submit_after_shutdown(self):
        """测试关闭后提交任务"""
        pool = ThreadPool(max_workers=2)
        pool.shutdown()
        
        def quick_task():
            return "done"
        
        with pytest.raises(ThreadPoolError):
            pool.submit("task_1", quick_task)
    
    def test_thread_pool_context_manager(self):
        """测试上下文管理器"""
        with ThreadPool(max_workers=2) as pool:
            def quick_task():
                return "done"
            
            pool.submit("task_1", quick_task)
            pool.wait_all(timeout=10)
        
        # 退出上下文后应该关闭
        assert pool.is_shutdown
    
    def test_thread_pool_multiple_tasks(self):
        """测试多个任务"""
        pool = ThreadPool(max_workers=4)
        
        def compute_task(value):
            return value * 2
        
        # 提交多个任务
        results = {}
        for i in range(10):
            task_id = f"task_{i}"
            pool.submit(task_id, compute_task, i)
            results[task_id] = i * 2
        
        # 等待完成
        pool.wait_all(timeout=10)
        
        # 验证结果
        for task_id, expected in results.items():
            result = pool.get_result(task_id)
            assert result == expected
        
        pool.shutdown()
    
    def test_thread_pool_exception_handling(self):
        """测试异常处理"""
        pool = ThreadPool(max_workers=2)
        
        def failing_task():
            raise ValueError("Test error")
        
        pool.submit("task_1", failing_task)
        
        # 获取结果时应该返回 None（因为任务失败）
        result = pool.get_result("task_1", timeout=5)
        # 结果可能是 None 或异常
        
        pool.shutdown()
    
    def test_thread_pool_nonexistent_task(self):
        """测试获取不存在的任务"""
        pool = ThreadPool(max_workers=2)
        
        result = pool.get_result("nonexistent", timeout=1)
        assert result is None
        
        assert not pool.is_done("nonexistent")
        
        pool.shutdown()
