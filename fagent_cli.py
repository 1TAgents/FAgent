#!/usr/bin/env python3
"""
FAgent CLI 启动脚本

使用方式:
    python fagent_cli.py --help
    python fagent_cli.py --version
    python fagent_cli.py hello
"""

import sys
import os

# 添加 src 目录到 Python 路径
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

from cli.main import main

if __name__ == '__main__':
    main()
