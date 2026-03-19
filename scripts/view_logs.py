#!/usr/bin/env python3
"""
日志查看工具

功能：
1. 查看最新日志
2. 过滤错误日志
3. 查看审计日志
4. 查看 Event 事件
5. 统计分析
"""
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import argparse


class LogViewer:
    """日志查看器"""
    
    def __init__(self, log_dir: str = 'logs'):
        self.log_dir = Path(log_dir)
    
    def show_latest_logs(self, lines: int = 20, level: str = 'INFO'):
        """显示最新日志"""
        date_str = datetime.now().strftime('%Y%m%d')
        log_file = self.log_dir / f'query_{date_str}.log'
        
        if not log_file.exists():
            print(f"❌ 日志文件不存在：{log_file}")
            return
        
        print("=" * 80)
        print(f"最新日志 ({log_file.name})")
        print("=" * 80)
        
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        
        # 过滤级别
        filtered_lines = [l for l in all_lines if f'| {level} |' in l or level == 'ALL']
        
        # 显示最新 N 行
        for line in filtered_lines[-lines:]:
            print(line.strip())
    
    def show_errors(self, lines: int = 20):
        """显示错误日志"""
        date_str = datetime.now().strftime('%Y%m%d')
        error_file = self.log_dir / f'error_{date_str}.log'
        
        if not error_file.exists():
            print("✅ 今日无错误日志")
            return
        
        print("=" * 80)
        print(f"错误日志 ({error_file.name})")
        print("=" * 80)
        
        with open(error_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        
        for line in all_lines[-lines:]:
            print(line.strip())
    
    def show_audit_logs(self, lines: int = 20):
        """显示审计日志"""
        date_str = datetime.now().strftime('%Y%m%d')
        audit_file = self.log_dir / f'audit_{date_str}.jsonl'
        
        if not audit_file.exists():
            print("❌ 审计日志文件不存在")
            return
        
        print("=" * 80)
        print(f"审计日志 ({audit_file.name})")
        print("=" * 80)
        
        with open(audit_file, 'r', encoding='utf-8') as f:
            lines_data = f.readlines()
        
        for line in lines_data[-lines:]:
            data = json.loads(line.strip())
            print(f"\n📋 {data.get('timestamp', '')}")
            for key, value in data.items():
                if key not in ['timestamp', 'level']:
                    print(f"   {key}: {value}")
    
    def show_events(self, lines: int = 20, event_type: str = None):
        """显示 Event 事件"""
        date_str = datetime.now().strftime('%Y%m%d')
        event_file = self.log_dir / f'events_{date_str}.jsonl'
        
        if not event_file.exists():
            print("❌ Event 文件不存在")
            return
        
        print("=" * 80)
        if event_type:
            print(f"Event 事件 - {event_type} ({event_file.name})")
        else:
            print(f"Event 事件 ({event_file.name})")
        print("=" * 80)
        
        with open(event_file, 'r', encoding='utf-8') as f:
            lines_data = f.readlines()
        
        count = 0
        for line in lines_data:
            data = json.loads(line.strip())
            
            # 过滤类型
            if event_type and data.get('event_type') != event_type:
                continue
            
            print(f"\n📊 {data.get('timestamp', '')} | {data.get('event_type')}")
            
            # 显示关键信息
            event_data = data.get('data', {})
            for key, value in event_data.items():
                if isinstance(value, dict):
                    print(f"   {key}:")
                    for k, v in value.items():
                        print(f"      {k}: {v}")
                else:
                    # 截断长文本
                    str_value = str(value)
                    if len(str_value) > 100:
                        str_value = str_value[:100] + '...'
                    print(f"   {key}: {str_value}")
            
            count += 1
            if count >= lines:
                break
    
    def show_stats(self):
        """显示统计信息"""
        date_str = datetime.now().strftime('%Y%m%d')
        event_file = self.log_dir / f'events_{date_str}.jsonl'
        
        if not event_file.exists():
            print("❌ 无 Event 数据")
            return
        
        print("=" * 80)
        print(f"统计信息 ({date_str})")
        print("=" * 80)
        
        # 统计事件类型
        type_counts = {}
        hour_counts = {}
        
        with open(event_file, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line.strip())
                
                # 类型统计
                event_type = data.get('event_type')
                type_counts[event_type] = type_counts.get(event_type, 0) + 1
                
                # 小时统计
                timestamp = data.get('timestamp', '')
                if len(timestamp) >= 13:  # YYYY-MM-DDTHH
                    hour = timestamp[11:13]
                    hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        print("\n📊 事件类型统计:")
        for event_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {event_type:20s}: {count:5d}")
        
        print("\n📈 小时分布:")
        for hour in sorted(hour_counts.keys()):
            count = hour_counts[hour]
            bar = '█' * (count // 10)
            print(f"  {hour}:00 | {bar} {count}")
        
        total = sum(type_counts.values())
        print(f"\n总计：{total} 个事件")


def main():
    parser = argparse.ArgumentParser(description='日志查看工具')
    
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # 最新日志
    parser_latest = subparsers.add_parser('latest', help='查看最新日志')
    parser_latest.add_argument('-n', '--lines', type=int, default=20)
    parser_latest.add_argument('-l', '--level', type=str, default='INFO',
                              choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'ALL'])
    
    # 错误日志
    parser_error = subparsers.add_parser('error', help='查看错误日志')
    parser_error.add_argument('-n', '--lines', type=int, default=20)
    
    # 审计日志
    parser_audit = subparsers.add_parser('audit', help='查看审计日志')
    parser_audit.add_argument('-n', '--lines', type=int, default=20)
    
    # Event 事件
    parser_event = subparsers.add_parser('event', help='查看 Event 事件')
    parser_event.add_argument('-n', '--lines', type=int, default=20)
    parser_event.add_argument('-t', '--type', type=str, 
                             choices=['tool_call', 'data_load', 'user_query', 'backtest', 'error'])
    
    # 统计信息
    parser_stats = subparsers.add_parser('stats', help='显示统计信息')
    
    args = parser.parse_args()
    
    viewer = LogViewer()
    
    if args.command == 'latest':
        viewer.show_latest_logs(args.lines, args.level)
    elif args.command == 'error':
        viewer.show_errors(args.lines)
    elif args.command == 'audit':
        viewer.show_audit_logs(args.lines)
    elif args.command == 'event':
        viewer.show_events(args.lines, args.type)
    elif args.command == 'stats':
        viewer.show_stats()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
