# FAgent Memory System
# FAgent 记忆系统

__version__ = "0.1.0"

# 延迟导入，避免循环依赖
def get_memory_manager():
    """获取 Memory Manager 实例"""
    from .manager import MemoryManager
    return MemoryManager()
