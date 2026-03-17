"""
Trading Cost Calculator - 交易费用计算器

基于 A 股行业标准：
- 印花税：0.1%（卖出收取）
- 佣金：万分之 3（买卖双向，最低 5 元）
- 过户费：万分之 0.2（买卖双向）
"""

class TradingCostCalculator:
    """交易费用计算器"""
    
    def __init__(
        self,
        stamp_duty: float = 0.001,      # 印花税 0.1%（卖出）
        commission: float = 0.0003,      # 佣金 万分之 3
        min_commission: float = 5.0,     # 最低佣金 5 元
        transfer_fee: float = 0.00002    # 过户费 万分之 0.2
    ):
        self.stamp_duty = stamp_duty
        self.commission = commission
        self.min_commission = min_commission
        self.transfer_fee = transfer_fee
    
    def calculate_cost(self, price: float, quantity: int, side: str) -> float:
        """
        计算单笔交易费用
        
        Args:
            price: 成交价格
            quantity: 数量（股）
            side: buy/sell
            
        Returns:
            总费用
        """
        # 成交金额
        amount = price * quantity
        
        # 佣金（买卖双向，最低 5 元）
        commission = max(amount * self.commission, self.min_commission)
        
        # 过户费（买卖双向）
        transfer = amount * self.transfer_fee
        
        # 印花税（仅卖出）
        stamp = amount * self.stamp_duty if side == 'sell' else 0
        
        total_cost = commission + transfer + stamp
        
        return total_cost
    
    def calculate_round_trip_cost(self, buy_price: float, sell_price: float, quantity: int) -> float:
        """
        计算往返交易总费用
        
        Args:
            buy_price: 买入价
            sell_price: 卖出价
            quantity: 数量
            
        Returns:
            总费用
        """
        buy_cost = self.calculate_cost(buy_price, quantity, 'buy')
        sell_cost = self.calculate_cost(sell_price, quantity, 'sell')
        
        return buy_cost + sell_cost
