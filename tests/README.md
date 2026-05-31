# 测试说明

当前 `tests/` 目录同时包含三种测试形态：单元测试、脚本式联调测试、历史回归/路演脚本。不要把它理解成单一框架。

## 目录分层

### 1. 单元测试

- `tests/memory/`：Memory 的 ID、模型、数据库、API、layers
- `tests/cli/`：CLI 框架与各命令的基础可用性
- `tests/test_validators.py`：验证器相关测试

### 2. 联调 / 冒烟测试

- `tests/test_full_stack.py`：前端/Backend/Agents 的服务链路检查
- `tests/test_market.py`：行情服务和接口脚本测试
- `tests/test_multi_turn.py`：多轮对话测试

### 3. 场景与报告脚本

- `tests/test_runner.py` + `tests/test_cases.json`：JSON 驱动的场景执行器
- `tests/badcases.json` + `tests/test_badcases_log.py`：用户实测 badcase 数据集、回放元数据和字段校验
- `tests/run_automated_tests.py`
- `tests/run_enhanced_tests.py`
- `tests/test_roadshow_multi_turn.py`：生成路演/演示报告

## 安装

```bash
pip install -r tests/requirements.txt
```

如果你要跑 CLI 或 Memory 相关测试，还需要先安装项目本身依赖：

```bash
pip install -r requirements-cli.txt
pip install -r backend/requirements.txt
pip install -r agents/requirements.txt
```

## 常用命令

### 单元测试

```bash
pytest tests/memory tests/cli
pytest tests/test_validators.py
```

### 联调脚本

这些脚本通常要求本地服务已经启动：

```bash
python tests/test_full_stack.py
python tests/test_market.py
python tests/test_multi_turn.py
```

### JSON 场景执行

```bash
python tests/test_runner.py --list
python tests/test_runner.py --suite market_service
python tests/test_runner.py --tag smoke
```

### Badcase 回归数据

```bash
python -m pytest tests/test_badcases_log.py -q
python .cursor/skills/fagent-badcase-replay/scripts/run_badcase_eval.py --list
```

### 路演报告

```bash
python tests/test_roadshow_multi_turn.py \
  --output reports/roadshow_test_report.html
```

## 服务依赖

不同脚本依赖不同服务：

| 测试类型 | 需要 Backend | 需要 Agents | 需要 Frontend |
|----------|--------------|-------------|---------------|
| `tests/memory` | 否 | 否 | 否 |
| `tests/cli` | 否 | 否 | 否 |
| `test_full_stack.py` | 是 | 是 | 可选 |
| `test_market.py` | 视场景而定 | 通常需要 | 否 |
| `test_runner.py` | 视模块而定 | 视模块而定 | 否 |

## 说明

- 历史测试报告请看 `tests/TEST_REPORT.md`，它是归档快照，不代表当前实时质量
- 如果你只是想做一轮基础验证，优先跑 `pytest tests/memory tests/cli`
- 如果你要验证 Web 主链路，优先跑 `tests/test_full_stack.py`
