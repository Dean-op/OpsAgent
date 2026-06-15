# SuperBizAgent

企业级智能对话与智能运维助手。当前版本支持 RAG 知识库问答、AIOps 自动诊断、Prometheus 监控查询、MCP 工具调用，并默认通过 OpenAI 兼容协议接入硅基流动模型。

## 核心能力

- 智能对话：支持普通问答和 SSE 流式对话。
- RAG 知识库：上传 Markdown 文档后自动切分、向量化并写入 Milvus。
- AIOps 诊断：基于 Plan-Execute-Replan 执行告警排查，并流式生成诊断报告。
- Prometheus 监控：内置 Prometheus + node-exporter Docker 编排和演示告警规则。
- MCP 工具：通过本地 MCP Server 提供日志查询、指标查询等工具。

## 技术栈

| 模块 | 技术 |
| --- | --- |
| Web/API | FastAPI |
| Agent | LangChain, LangGraph |
| 模型接口 | OpenAI-compatible API |
| 默认模型 | SiliconFlow: `deepseek-ai/DeepSeek-V4-Flash` |
| Embedding | SiliconFlow: `Qwen/Qwen3-Embedding-0.6B` |
| 向量库 | Milvus |
| 监控 | Prometheus, node-exporter |
| 工具协议 | MCP |

## 快速启动

### 环境要求

- Python 3.11+，推荐项目当前的 Python 3.13 配置
- Docker Desktop
- 硅基流动 API Key

### Windows 推荐方式

```powershell
.\start-windows.bat
```

脚本会自动处理：

- 创建或同步 `.venv`
- 启动 Milvus
- 启动 Prometheus 和 node-exporter
- 启动 CLS MCP Server
- 启动 Monitor MCP Server
- 启动 FastAPI 主服务
- 上传 `aiops-docs/*.md` 到知识库

停止服务：

```powershell
.\stop-windows.bat
```

### 手动启动

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .

docker compose -f vector-database.yml up -d
docker compose -f prometheus-docker.yml up -d

python mcp_servers/cls_server.py
python mcp_servers/monitor_server.py
python -m uvicorn app.main:app --host 0.0.0.0 --port 9900
```

## 访问地址

| 服务 | 地址 |
| --- | --- |
| Web 页面 | http://localhost:9900 |
| API 文档 | http://localhost:9900/docs |
| Prometheus | http://localhost:9090 |
| node-exporter | http://localhost:9100 |
| CLS MCP | http://127.0.0.1:8003/mcp |
| Monitor MCP | http://127.0.0.1:8004/mcp |

## 配置

项目通过 `.env` 读取配置。`.env` 不应提交到 Git。

```env
LLM_API_KEY=your-siliconflow-api-key
LLM_BASE_URL=https://api.siliconflow.cn/v1
LLM_MODEL=deepseek-ai/DeepSeek-V4-Flash
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-0.6B
EMBEDDING_DIMENSIONS=1024

PROMETHEUS_BASE_URL=http://127.0.0.1:9090
PROMETHEUS_REQUEST_TIMEOUT=10.0

MILVUS_HOST=localhost
MILVUS_PORT=19530

RAG_TOP_K=3
CHUNK_MAX_SIZE=800
CHUNK_OVERLAP=100
```

## 主要接口

| 功能 | 方法 | 路径 |
| --- | --- | --- |
| 健康检查 | GET | `/health` |
| 普通对话 | POST | `/api/chat` |
| 流式对话 | POST | `/api/chat_stream` |
| 文件上传 | POST | `/api/upload` |
| AIOps 诊断 | POST | `/api/aiops` |

示例：

```bash
curl -X POST "http://localhost:9900/api/aiops" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"demo"}' \
  --no-buffer
```

## AIOps 演示流程

1. 打开 http://localhost:9900。
2. 点击右上角 `AI Ops`。
3. 系统生成 4-6 步诊断计划。
4. Executor 逐步调用 Prometheus、MCP 日志工具和指标工具。
5. 最终诊断报告通过 SSE `content` 事件真流式输出。

诊断链路：

```text
Planner -> Executor -> Replanner -> Streaming Report
```

## 项目结构

```text
app/
  api/          FastAPI 路由
  agent/        AIOps Agent、MCP Client
  core/         LLM 工厂、Milvus Client
  services/     RAG、AIOps、向量检索服务
  tools/        本地 Agent 工具
mcp_servers/    本地 MCP Server
prometheus/     Prometheus 配置和演示告警规则
aiops-docs/     运维知识库文档
static/         前端页面
tests/          测试用例
```

## 常用验证命令

```powershell
# 服务健康
Invoke-WebRequest -Uri "http://127.0.0.1:9900/health" -UseBasicParsing

# Prometheus 告警
Invoke-WebRequest -Uri "http://127.0.0.1:9090/api/v1/alerts" -UseBasicParsing

# 前端语法
node --check static\app.js

# 关键测试
.\.venv\Scripts\python.exe -m pytest tests -q
```

## 常见问题

### `.env` 已经被提交过怎么办？

当前 `.gitignore` 已忽略 `.env`。如果历史提交中泄露过真实 API Key，请到硅基流动后台作废旧 Key 并重新生成。

### AIOps 看起来不是全程逐字输出？

计划生成和工具查询必须等节点完成后才能返回；最终诊断报告阶段已经支持 token/片段级真流式输出。

### MCP Server 启动失败？

检查端口是否被占用：

```powershell
netstat -ano | findstr :8003
netstat -ano | findstr :8004
```

也可以直接执行：

```powershell
.\stop-windows.bat
.\start-windows.bat
```

### Prometheus 没有数据？

确认容器和端口：

```powershell
docker ps
Invoke-WebRequest -Uri "http://127.0.0.1:9090/-/healthy" -UseBasicParsing
```

## 许可证

MIT License
