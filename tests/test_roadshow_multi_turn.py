#!/usr/bin/env python3
"""
路演多轮对话自动化测试框架

测试 Backend API 的多轮对话能力，筛选优质对话示例用于路演演示

功能:
1. 自动化执行多轮对话测试场景
2. 评估每轮对话质量（内容、时间、连贯性）
3. 生成测试报告
4. 自动将优质对话提升为路演演示示例

使用:
    python tests/test_roadshow_multi_turn.py --output reports/roadshow_test_2026-03-20.html
"""
import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== 数据模型 ====================

@dataclass
class TurnResult:
    """单轮对话测试结果"""
    turn_index: int
    user_input: str
    assistant_output: str
    response_time_ms: float
    success: bool
    error: Optional[str] = None
    content_score: float = 0.0  # 内容质量评分 (0-100)
    coherence_score: float = 0.0  # 上下文连贯性评分 (0-100)


@dataclass
class ScenarioResult:
    """测试场景结果"""
    scenario_id: str
    scenario_name: str
    turns: List[TurnResult]
    total_time_ms: float
    success_rate: float
    avg_content_score: float
    avg_coherence_score: float
    overall_score: float
    is_demo_ready: bool  # 是否达到路演标准
    issues: List[str]


@dataclass
class TestReport:
    """测试报告"""
    test_time: str
    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    demo_ready_count: int
    scenario_results: List[ScenarioResult]
    summary: Dict[str, Any]


# ==================== 测试场景定义 ====================

class RoadshowScenarios:
    """路演多轮对话测试场景"""
    
    @staticmethod
    def get_all_scenarios() -> List[Dict[str, Any]]:
        """获取所有测试场景"""
        return [
            # 场景 1: 股票查询 → 策略咨询 → 回测验证
            {
                "id": "RS001",
                "name": "股票投资咨询流程",
                "description": "从行情查询到策略回测的完整流程",
                "turns": [
                    {"user": "贵州茅台现在怎么样？"},
                    {"user": "有什么适合的趋势策略？"},
                    {"user": "用双均线策略回测一下茅台，参数 5 日和 20 日，过去一年"}
                ],
                "expected_outcomes": [
                    "返回茅台行情数据（价格、涨跌幅、技术指标）",
                    "推荐至少 1 个趋势策略（双均线）",
                    "返回回测结果（收益率、夏普比率等指标）"
                ],
                "priority": "high"
            },
            
            # 场景 2: 期货查询 → 策略对比 → 风险评估
            {
                "id": "RS002",
                "name": "期货投资咨询流程",
                "description": "期货市场查询到策略分析",
                "turns": [
                    {"user": "螺纹钢期货现在什么价格？"},
                    {"user": "期货和股票策略有什么区别？"},
                    {"user": "期货双均线策略怎么做空？"}
                ],
                "expected_outcomes": [
                    "返回螺纹钢期货价格（主力合约）",
                    "解释期货可以做空、有杠杆等特点",
                    "说明期货双均线的做空机制"
                ],
                "priority": "high"
            },
            
            # 场景 3: 策略库探索 → 参数咨询 → 适用场景
            {
                "id": "RS003",
                "name": "策略库探索流程",
                "description": "了解可用策略并选择合适参数",
                "turns": [
                    {"user": "你们有哪些策略可以用？"},
                    {"user": "双均线策略的参数怎么设置？"},
                    {"user": "RSI 策略适合什么行情？"}
                ],
                "expected_outcomes": [
                    "列出至少 2 个策略（双均线、RSI）",
                    "说明双均线参数（短期 5-10 日，长期 20-30 日）",
                    "说明 RSI 适合震荡市"
                ],
                "priority": "medium"
            },
            
            # 场景 4: 回测结果分析 → 策略优化 → 风险评估
            {
                "id": "RS004",
                "name": "回测深度分析流程",
                "description": "对回测结果进行深度分析和优化",
                "turns": [
                    {"user": "双均线策略回测茅台的收益怎么样？"},
                    {"user": "最大回撤是多少？"},
                    {"user": "怎么优化这个策略？"}
                ],
                "expected_outcomes": [
                    "返回收益率数据",
                    "返回最大回撤数据",
                    "提供优化建议（参数调整、止损等）"
                ],
                "priority": "high"
            },
            
            # 场景 5: 新手入门 → 基础教学 → 实战演练
            {
                "id": "RS005",
                "name": "新手入门流程",
                "description": "从零开始指导新手使用",
                "turns": [
                    {"user": "我是新手，怎么用 FAgent？"},
                    {"user": "第一个策略应该选什么？"},
                    {"user": "帮我回测一下这个策略"}
                ],
                "expected_outcomes": [
                    "简单介绍 FAgent 功能",
                    "推荐简单策略（如双均线）",
                    "执行回测并解释结果"
                ],
                "priority": "medium"
            },
            
            # 场景 6: 闲聊吐槽 → 情感共鸣 → 投资建议
            {
                "id": "RS006",
                "name": "情感交流流程",
                "description": "展示 AI 的情感理解和共情能力",
                "turns": [
                    {"user": "最近炒股亏了好多，好郁闷"},
                    {"user": "有什么办法可以避免情绪化交易吗？"},
                    {"user": "那你推荐什么策略比较稳健？"}
                ],
                "expected_outcomes": [
                    "表达理解和安慰，不冷漠",
                    "提供专业建议（止盈止损、策略回测）",
                    "推荐稳健策略（如低回撤策略）"
                ],
                "priority": "medium"
            },
            
            # 场景 7: 闲聊夸奖 → 谦虚回应 → 展示能力
            {
                "id": "RS007",
                "name": "夸奖回应流程",
                "description": "展示 AI 的谦虚和专业",
                "turns": [
                    {"user": "你比那些券商分析师厉害多了"},
                    {"user": "真的假的？有这么神吗？"},
                    {"user": "那你给我展示一下你的能力"}
                ],
                "expected_outcomes": [
                    "谦虚回应，不夸大",
                    "客观说明能力边界",
                    "展示核心功能（查询、策略、回测）"
                ],
                "priority": "low"
            },
            
            # 场景 8: 闲聊天气 → 生活话题 → 投资心情
            {
                "id": "RS008",
                "name": "生活话题流程",
                "description": "展示 AI 的生活化和人性化",
                "turns": [
                    {"user": "今天天气不错，适合出门"},
                    {"user": "你觉得天气和股市有关系吗？"},
                    {"user": "哈哈，开个玩笑，帮我看看螺纹钢吧"}
                ],
                "expected_outcomes": [
                    "友好回应天气话题",
                    "科学解释（天气与股市无直接关系）",
                    "理解幽默，切换到业务查询"
                ],
                "priority": "low"
            }
        ]


# ==================== 测试执行器 ====================

class MultiTurnTester:
    """多轮对话测试执行器"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.cid = None
    
    def create_session(self) -> int:
        """创建新会话"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/chat/session/create",
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            self.cid = data.get("cid")
            logger.info(f"创建会话成功 | cid={self.cid}")
            return self.cid
        except Exception as e:
            logger.error(f"创建会话失败：{e}")
            raise
    
    def send_message(self, user_message: str) -> tuple:
        """
        发送消息并获取回复
        
        返回：(assistant_content, response_time_ms, success, error)
        """
        if self.cid is None:
            raise ValueError("请先创建会话")
        
        start_time = time.time()
        
        try:
            payload = {
                "cid": self.cid,
                "user_message": user_message,
                "temperature": 0.7
            }
            
            response = self.session.post(
                f"{self.base_url}/api/chat/send/stream",
                json=payload,
                stream=True,
                timeout=60
            )
            response.raise_for_status()
            
            full_content = ""
            for line in response.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    if decoded.startswith("data: "):
                        data_str = decoded[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            if "content" in data:
                                full_content += data["content"]
                        except json.JSONDecodeError:
                            continue
            
            response_time_ms = (time.time() - start_time) * 1000
            
            if not full_content.strip():
                return "", response_time_ms, False, "空响应"
            
            return full_content, response_time_ms, True, None
            
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            logger.error(f"发送消息失败：{error_msg}")
            return "", response_time_ms, False, error_msg
    
    def evaluate_content(self, content: str, expected_keywords: List[str] = None) -> float:
        """
        评估内容质量（0-100 分）
        
        评分标准:
        - 内容长度 (20 分): >100 字得满分
        - 结构清晰 (30 分): 有分段、列表等
        - 关键词匹配 (50 分): 包含预期关键词
        """
        score = 0.0
        
        # 内容长度 (20 分)
        length = len(content.strip())
        if length > 100:
            score += 20
        elif length > 50:
            score += 15
        elif length > 20:
            score += 10
        
        # 结构清晰 (30 分)
        has_structure = False
        if "\n" in content:  # 有分段
            has_structure = True
            score += 10
        if any(marker in content for marker in ["-", "•", "1.", "2."]):  # 有列表
            has_structure = True
            score += 10
        if any(marker in content for marker in ["**", "##", "###"]):  # 有强调
            score += 10
        
        # 关键词匹配 (50 分)
        if expected_keywords:
            matched = sum(1 for kw in expected_keywords if kw.lower() in content.lower())
            keyword_score = (matched / len(expected_keywords)) * 50
            score += keyword_score
        else:
            # 如果没有预期关键词，检查是否有实质内容
            if length > 50:
                score += 30
        
        return min(score, 100.0)
    
    def evaluate_coherence(self, current_output: str, previous_context: List[str]) -> float:
        """
        评估上下文连贯性（0-100 分）
        
        评分标准:
        - 引用了之前的内容 (40 分)
        - 逻辑连贯 (30 分)
        - 代词使用正确 (30 分)
        """
        if not previous_context:
            return 100.0  # 第一轮无需评估连贯性
        
        score = 0.0
        context_text = " ".join(previous_context[-2:])  # 最近两轮
        
        # 引用之前内容 (40 分)
        # 检查是否包含之前提到的关键词
        context_words = set(context_text.lower().split())
        current_words = set(current_output.lower().split())
        overlap = len(context_words & current_words)
        if overlap > 5:
            score += 40
        elif overlap > 2:
            score += 30
        elif overlap > 0:
            score += 20
        
        # 逻辑连贯 (30 分) - 检查是否有连贯词
        coherence_markers = ["因此", "所以", "基于", "根据", "如前", "继续", "另外", "同时"]
        if any(marker in current_output for marker in coherence_markers):
            score += 30
        
        # 代词使用 (30 分)
        pronouns = ["这个", "那个", "它", "他", "她", "这", "那"]
        if any(pronoun in current_output for pronoun in pronouns):
            score += 30
        
        return min(score, 100.0)
    
    def run_scenario(self, scenario: Dict[str, Any]) -> ScenarioResult:
        """执行单个测试场景"""
        logger.info(f"开始测试场景：{scenario['name']} ({scenario['id']})")
        
        # 创建新会话
        self.create_session()
        
        turns_result = []
        previous_outputs = []
        total_time = 0.0
        success_count = 0
        
        for i, turn in enumerate(scenario["turns"]):
            user_input = turn["user"]
            
            # 发送消息
            content, response_time, success, error = self.send_message(user_input)
            total_time += response_time
            
            if success:
                success_count += 1
                
                # 评估内容质量
                expected_keywords = scenario.get("expected_outcomes", [])
                content_score = self.evaluate_content(content, expected_keywords)
                
                # 评估连贯性
                coherence_score = self.evaluate_coherence(content, previous_outputs)
                
                turns_result.append(TurnResult(
                    turn_index=i,
                    user_input=user_input,
                    assistant_output=content,
                    response_time_ms=response_time,
                    success=success,
                    error=error,
                    content_score=content_score,
                    coherence_score=coherence_score
                ))
                
                previous_outputs.append(content)
            else:
                turns_result.append(TurnResult(
                    turn_index=i,
                    user_input=user_input,
                    assistant_output="",
                    response_time_ms=response_time,
                    success=False,
                    error=error
                ))
        
        # 计算总体评分
        success_rate = success_count / len(scenario["turns"])
        avg_content = sum(t.content_score for t in turns_result) / len(turns_result)
        avg_coherence = sum(t.coherence_score for t in turns_result) / len(turns_result)
        overall_score = (success_rate * 40 + avg_content * 0.3 + avg_coherence * 0.3)
        
        # 判断是否达到路演标准
        is_demo_ready = (
            success_rate >= 0.9 and
            avg_content >= 70 and
            avg_coherence >= 60 and
            overall_score >= 75
        )
        
        # 收集问题
        issues = []
        if success_rate < 1.0:
            issues.append(f"有{len(scenario['turns']) - success_count}轮对话失败")
        if avg_content < 70:
            issues.append(f"内容质量偏低 ({avg_content:.1f}分)")
        if avg_coherence < 60:
            issues.append(f"上下文连贯性不足 ({avg_coherence:.1f}分)")
        if total_time > 30000:
            issues.append(f"总响应时间过长 ({total_time/1000:.1f}秒)")
        
        return ScenarioResult(
            scenario_id=scenario["id"],
            scenario_name=scenario["name"],
            turns=turns_result,
            total_time_ms=total_time,
            success_rate=success_rate,
            avg_content_score=avg_content,
            avg_coherence_score=avg_coherence,
            overall_score=overall_score,
            is_demo_ready=is_demo_ready,
            issues=issues
        )


# ==================== 报告生成器 ====================

class ReportGenerator:
    """测试报告生成器"""
    
    @staticmethod
    def generate_html_report(report: TestReport, output_path: str):
        """生成 HTML 测试报告"""
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FAgent 路演多轮对话测试报告</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f5; padding: 40px; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        h1 {{ color: #1e3a5f; margin-bottom: 20px; }}
        h2 {{ color: #2563EB; margin: 30px 0 15px; }}
        .summary {{ background: white; padding: 30px; border-radius: 12px; margin-bottom: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-top: 20px; }}
        .stat-card {{ background: linear-gradient(135deg, #2563EB 0%, #7C3AED 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; }}
        .stat-value {{ font-size: 36px; font-weight: 700; }}
        .stat-label {{ font-size: 14px; opacity: 0.9; margin-top: 5px; }}
        .scenario {{ background: white; border-radius: 12px; padding: 25px; margin-bottom: 25px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .scenario-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }}
        .scenario-title {{ font-size: 20px; font-weight: 600; color: #1e3a5f; }}
        .scenario-badge {{ padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }}
        .badge-ready {{ background: #059669; color: white; }}
        .badge-not-ready {{ background: #dc2626; color: white; }}
        .turn {{ background: #f9fafb; border-left: 4px solid #2563EB; padding: 15px; margin: 15px 0; border-radius: 4px; }}
        .turn-user {{ font-weight: 600; color: #2563EB; margin-bottom: 10px; }}
        .turn-assistant {{ color: #374151; line-height: 1.6; white-space: pre-wrap; }}
        .turn-stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-top: 10px; padding-top: 10px; border-top: 1px solid #e5e7eb; }}
        .stat {{ font-size: 13px; color: #6b7280; }}
        .stat strong {{ color: #1e3a5f; }}
        .issues {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin-top: 15px; border-radius: 4px; }}
        .issues-title {{ font-weight: 600; color: #92400e; margin-bottom: 8px; }}
        .issues-list {{ color: #78350f; }}
        .demo-examples {{ background: #dbeafe; border-left: 4px solid #2563EB; padding: 20px; margin-top: 30px; border-radius: 4px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
        th {{ background: #f9fafb; font-weight: 600; color: #6b7280; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 FAgent 路演多轮对话测试报告</h1>
        <p style="color: #6b7280; margin-bottom: 30px;">测试时间：{report.test_time}</p>
        
        <div class="summary">
            <h2>📊 测试概览</h2>
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-value">{report.total_scenarios}</div>
                    <div class="stat-label">总场景数</div>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #059669 0%, #10b981 100%);">
                    <div class="stat-value">{report.passed_scenarios}</div>
                    <div class="stat-label">通过场景</div>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%);">
                    <div class="stat-value">{report.failed_scenarios}</div>
                    <div class="stat-label">失败场景</div>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #7C3AED 0%, #a855f7 100%);">
                    <div class="stat-value">{report.demo_ready_count}</div>
                    <div class="stat-label">可路演示例</div>
                </div>
            </div>
        </div>
        
        <h2>📋 测试场景详情</h2>
"""
        
        for result in report.scenario_results:
            badge_class = "badge-ready" if result.is_demo_ready else "badge-not-ready"
            badge_text = "✅ 可路演" if result.is_demo_ready else "❌ 需优化"
            
            html += f"""
        <div class="scenario">
            <div class="scenario-header">
                <div class="scenario-title">{result.scenario_name} ({result.scenario_id})</div>
                <span class="scenario-badge {badge_class}">{badge_text}</span>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px;">
                <div class="stat-card" style="background: #f0f9ff; color: #1e3a5f;">
                    <div class="stat-value" style="font-size: 24px;">{result.success_rate*100:.0f}%</div>
                    <div class="stat-label">成功率</div>
                </div>
                <div class="stat-card" style="background: #f0f9ff; color: #1e3a5f;">
                    <div class="stat-value" style="font-size: 24px;">{result.avg_content_score:.1f}</div>
                    <div class="stat-label">内容质量</div>
                </div>
                <div class="stat-card" style="background: #f0f9ff; color: #1e3a5f;">
                    <div class="stat-value" style="font-size: 24px;">{result.avg_coherence_score:.1f}</div>
                    <div class="stat-label">连贯性</div>
                </div>
                <div class="stat-card" style="background: #f0f9ff; color: #1e3a5f;">
                    <div class="stat-value" style="font-size: 24px;">{result.overall_score:.1f}</div>
                    <div class="stat-label">综合评分</div>
                </div>
            </div>
"""
            
            for turn in result.turns:
                status_icon = "✅" if turn.success else "❌"
                html += f"""
            <div class="turn">
                <div class="turn-user">{status_icon} Turn {turn.turn_index + 1}: {turn.user_input}</div>
                <div class="turn-assistant">{turn.assistant_output if turn.assistant_output else f"⚠️ 错误：{turn.error}"}</div>
                <div class="turn-stats">
                    <div class="stat"><strong>响应时间:</strong> {turn.response_time_ms/1000:.2f}s</div>
                    <div class="stat"><strong>内容评分:</strong> {turn.content_score:.1f}/100</div>
                    <div class="stat"><strong>连贯性:</strong> {turn.coherence_score:.1f}/100</div>
                </div>
            </div>
"""
            
            if result.issues:
                html += f"""
            <div class="issues">
                <div class="issues-title">⚠️ 需要优化:</div>
                <ul class="issues-list">
"""
                for issue in result.issues:
                    html += f"                    <li>{issue}</li>\n"
                html += """                </ul>
            </div>
"""
            
            html += "        </div>\n"
        
        # 可路演示例汇总
        demo_ready = [r for r in report.scenario_results if r.is_demo_ready]
        if demo_ready:
            html += """
        <div class="demo-examples">
            <h2>🎯 推荐路演示例</h2>
            <table>
                <tr>
                    <th>场景 ID</th>
                    <th>场景名称</th>
                    <th>综合评分</th>
                    <th>对话轮数</th>
                </tr>
"""
            for r in demo_ready:
                html += f"""
                <tr>
                    <td>{r.scenario_id}</td>
                    <td>{r.scenario_name}</td>
                    <td>{r.overall_score:.1f}</td>
                    <td>{len(r.turns)}</td>
                </tr>
"""
            html += """
            </table>
        </div>
"""
        
        html += """
    </div>
</body>
</html>
"""
        
        Path(output_path).write_text(html, encoding='utf-8')
        logger.info(f"HTML 报告已生成：{output_path}")


# ==================== 主函数 ====================

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="路演多轮对话自动化测试")
    parser.add_argument("--output", type=str, default="reports/roadshow_test_report.html",
                        help="测试报告输出路径")
    parser.add_argument("--base-url", type=str, default="http://localhost:8000",
                        help="Backend API 地址")
    args = parser.parse_args()
    
    # 创建报告目录
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    
    # 初始化测试器
    tester = MultiTurnTester(base_url=args.base_url)
    
    # 获取测试场景
    scenarios = RoadshowScenarios.get_all_scenarios()
    logger.info(f"加载了 {len(scenarios)} 个测试场景")
    
    # 执行测试
    results = []
    for scenario in scenarios:
        try:
            result = tester.run_scenario(scenario)
            results.append(result)
        except Exception as e:
            logger.error(f"场景 {scenario['name']} 测试失败：{e}")
    
    # 生成报告
    passed = sum(1 for r in results if r.success_rate >= 0.9)
    failed = len(results) - passed
    demo_ready = sum(1 for r in results if r.is_demo_ready)
    
    report = TestReport(
        test_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        total_scenarios=len(results),
        passed_scenarios=passed,
        failed_scenarios=failed,
        demo_ready_count=demo_ready,
        scenario_results=results,
        summary={
            "pass_rate": passed / len(results) if results else 0,
            "demo_ready_rate": demo_ready / len(results) if results else 0
        }
    )
    
    # 生成 HTML 报告
    ReportGenerator.generate_html_report(report, args.output)
    
    # 打印摘要
    print("\n" + "="*60)
    print("📊 测试完成摘要")
    print("="*60)
    print(f"测试时间：{report.test_time}")
    print(f"总场景数：{report.total_scenarios}")
    print(f"✅ 通过：{report.passed_scenarios}")
    print(f"❌ 失败：{report.failed_scenarios}")
    print(f"🎯 可路演示例：{report.demo_ready_count}")
    print(f"\n报告已生成：{args.output}")
    print("="*60)


if __name__ == "__main__":
    main()
