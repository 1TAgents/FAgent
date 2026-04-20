# 数据同步服务

这是一个可选的独立服务，用来慢速预热本地历史数据缓存。它不是 Web 聊天主链路的必需组件，适合本地实验或离线数据准备。

## 作用

- 同步股票列表
- 同步单只股票 K 线
- 后台批量补全历史数据
- 查看同步状态和缓存统计

## 启动

在项目根目录执行：

```bash
uvicorn agents.data_sync.service:app --reload --host 0.0.0.0 --port 8003
```

如果你的环境对 `PYTHONPATH` 有要求，也可以显式指定：

```bash
PYTHONPATH=. uvicorn agents.data_sync.service:app --reload --host 0.0.0.0 --port 8003
```

## 常用接口

- `GET /health`：健康检查
- `GET /status`：查看同步状态
- `POST /sync/stocks`：同步股票列表
- `POST /sync/klines`：同步单只股票或一组股票 K 线
- `POST /sync/historical`：后台启动历史数据补全
- `GET /stats`：查看数据统计

## 示例

```bash
curl http://localhost:8003/health
curl http://localhost:8003/status

curl -X POST http://localhost:8003/sync/stocks
curl -X POST http://localhost:8003/sync/klines \
  -H "Content-Type: application/json" \
  -d '{"symbol":"600519","limit":100}'
```

## 说明

- 该服务更偏“离线数据准备”，不建议和面向用户的聊天请求放在同一进程里。
- 启动前请确保行情数据相关依赖已经安装，并按需配置 `.env`。
- 如果你只想验证主服务链路，通常不需要先启动这个服务。
