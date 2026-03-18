"""
Main Router - 主路由器

根据模式（stock/future）路由到对应模块
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class MainRouter:
    """
    主路由器
    
    职责：
    1. 根据 mode 参数路由到对应模块
    2. 处理模式模糊时的确认
    3. 统一管理模块实例
    """
    
    def __init__(self):
        """初始化路由器"""
        self._stock_module = None
        self._future_module = None
        logger.info("主路由器初始化完成")
    
    @property
    def stock_module(self):
        """股票模块（懒加载）"""
        if self._stock_module is None:
            from modules.stock.api import StockModule
            self._stock_module = StockModule()
        return self._stock_module
    
    @property
    def future_module(self):
        """期货模块（懒加载）"""
        if self._future_module is None:
            from modules.future.api import FutureModule
            self._future_module = FutureModule()
        return self._future_module
    
    def process(
        self,
        message: str,
        mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        处理用户请求
        
        Args:
            message: 用户消息
            mode: 模式（stock/future/None=自动识别）
        
        Returns:
            {
                "reply": str,
                "data": dict (optional),
                "suggestions": list,
                "mode": str,  # 实际使用的模式
            }
        """
        try:
            # 1. 确定模式
            if mode is None:
                # 自动识别
                mode = self._auto_detect_mode(message)
                logger.info(f"自动识别模式 | mode={mode}")
            
            # 2. 路由到对应模块
            if mode == "stock":
                result = self.stock_module.process_chat(message)
                logger.info(f"路由到股票模块 | message={message[:50]}")
            elif mode == "future":
                result = self.future_module.process_chat(message)
                logger.info(f"路由到期货模块 | message={message[:50]}")
            else:
                # 未知模式
                return {
                    "reply": "抱歉，我不理解您的问题。请问您问的是股票还是期货？",
                    "suggestions": [
                        "帮我看看茅台行情",
                        "沪深 300 股指期货走势",
                    ],
                    "mode": "unknown",
                }
            
            # 3. 添加模式信息
            result["mode"] = mode
            return result
            
        except Exception as e:
            logger.error(f"路由处理失败 | error={e}")
            return {
                "reply": f"处理失败：{e}",
                "suggestions": [],
                "mode": "error",
            }
    
    def _auto_detect_mode(self, message: str) -> str:
        """
        自动识别模式
        
        基于关键词匹配
        
        Args:
            message: 用户消息
        
        Returns:
            "stock" | "future"
        """
        message_upper = message.upper()
        
        # 期货关键词
        future_keywords = [
            '期货', '主力合约', '做空', '开仓', '平仓',
            '股指', '商品', '原油', '黄金', '螺纹钢', '豆粕',
            'IF', 'IC', 'IH', 'IM',  # 股指期货
            'CU', 'AL', 'ZN', 'AU', 'AG',  # 金属
            'RB', 'HC',  # 螺纹/热卷
            'SC', 'LU', 'FU',  # 能源
            'M', 'Y', 'P', 'C',  # 农产品
            'SR', 'CF', 'MA', 'FG', 'SA',  # 化工
        ]
        
        # 检查是否包含期货关键词
        for keyword in future_keywords:
            if keyword in message_upper:
                return "future"
        
        # 默认返回股票
        return "stock"
    
    def get_module_info(self) -> Dict[str, Any]:
        """获取模块信息（用于前端显示）"""
        return {
            "stock": self.stock_module.get_module_info(),
            "future": self.future_module.get_module_info(),
        }


# 全局实例
main_router = MainRouter()


def get_router() -> MainRouter:
    """获取路由器实例"""
    return main_router
