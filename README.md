# Agent Loop Engineering

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek%20v4%20Flash-purple)](https://deepseek.com)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

最小化 AI Agent 循环框架。**Think → Act → Observe → Verify** 闭环执行，Tool 即插即用。

## 设计理念

```
┌─ Theory: Agent Loop ──────────────────┐  ┌─ Practice: llm-radar ─────────────────┐
│                                       │  │                                      │
│  [Think]  LLM reasoning & decision    │  │  _think():872 — check interval >=6h  │
│     │     Decide tool or output       │  │  source degradation >=3 auto-skip    │
│     ▼                                │  │                                      │
│  [Act]   Execute tool (web/file/code) │  │  fetch_all():412 — Selenium 6 sources│
│     │                                 │  │  extract_entities():454 — DeepSeek   │
│     ▼                                │  │  ~45 entities / run                  │
│  [Observe] Inject result into context │  │  _observe():935 — metrics.json       │
│     │                                 │  │  snapshot.json persistence           │
│     └──→ Back to [Think]              │  │  merge_entities():647 — dedup/merge  │
│                                       │  │                                      │
│  [Verify]  Output quality check       │  │  _verify():906 — freshness < 7d     │
│     │      Fail → retry               │  │  hotspots >= 3, else skip auto-push │
│     │                                 │  │                                      │
│     └──→ Back to [Think]              │  │  Crontab: 09:00 / 21:00 daily       │
│                                       │  │                                      │
│  Loop until verified final answer     │  │  Test suite: 19 pytest cases        │
└───────────────────────────────────────┘  └──────────────────────────────────────┘
```

## 在线演示

> 数据流可视化页面，点击节点查看对应源码片段。

[agent-loop.lab.jaden.tech](https://agent-loop.lab.jaden.tech) 

## 快速开始

```bash
pip install openai

# 复制配置模板
cp config.json.example config.json
# 编辑配置（填入 API Key）
vim config.json

# 执行任务
python3 agent-loop.py "搜索长亭科技的最新动态 $(date +%Y%m%d)，整理为 markdown 文档"

# 或从 stdin 读入
cat task.txt | python3 agent-loop.py

# 查看帮助
python3 agent-loop.py --help
```

执行示例：

```
$ python3 agent-loop.py "搜索..."
[Agent Loop v1.2] deepseek-v4-flash | Budget: 10 iters / 600s
--------------------------------------------------
✅ 报告已完成，保存至 reports/长亭科技最新动态-v1.0-20260616.md
```

## 配置文件

`config.json` 包含所有配置项：

```json
{
  "model": "deepseek-v4-flash",
  "api_key": "your-api-key",
  "base_url": "https://api.deepseek.com/v1",
  "tavily_api_key": "your-tavily-key",
  "prompt": "prompts/default.md",
  "workdir": ".",
  "checkpoint": "",
  "max_iter": 10,
  "max_duration": 600,
  "verbose": true
}
```

| 配置项 | 说明 |
|:-------|:------|
| `model` | LLM 模型名称 |
| `api_key` | DeepSeek API Key |
| `base_url` | API 基础 URL |
| `tavily_api_key` | Tavily 搜索 API Key |
| `prompt` | System Prompt 文件路径 |
| `workdir` | 工作目录（read_file/write_file 相对路径） |
| `checkpoint` | 检查点文件路径（为空不保存） |
| `max_iter` | 最大迭代次数 |
| `max_duration` | 最大运行时长（秒） |
| `verbose` | 是否显示详细输出 |

## 内置工具

| 工具 | 功能 |
|:-----|:------|
| `web_search` | 搜索互联网（Tavily API） |
| `web_extract` | 提取网页内容 |
| `read_file` | 读取本地文件 |
| `write_file` | 写入本地文件 |
| `run_python` | 执行 Python 代码 |

## 自定义工具

```python
from agent_loop import ToolBase, Agent, LLM, LLMConfig

def my_tool(param1: str, param2: int = 10) -> str:
    """工具功能描述（自动生成 schema）"""
    return f"Result: {param1} x {param2}"

tools = [ToolBase("my_tool", "Description", my_tool)]
agent = Agent(LLM(LLMConfig()), tools)
print(agent.run("Use my_tool to ..."))
```

## 特性

- **Think → Act → Observe → Verify** 闭环执行
- **预算控制**：迭代次数、运行时长、重试次数三重上限
- **自动验证**：输出质量检查，不合格自动重试
- **状态持久化**：支持检查点保存/恢复（断点续跑）
- **工具即插即用**：通过 `ToolBase` 快速注册，自动生成 OpenAI function calling schema

## 验证场景

| 理论场景 | llm-radar 实践项目 | 代码位置 |
|:---|:---|:---|
| 多源 web research → 文档合成 | 7 新闻源 Selenium 抓取 → DeepSeek 提取 → merge | `fetch_all()`, `_selenium_extract()`, `merge_entities()` |
| 代码/HTML 生成 | — | 通用，llm-radar 不涉及 |
| 结构化知识梳理 | 5 维度实体（厂商/人物/工具/大模型/热点） | `extract_entities()`, `_parse_json_output()` |
| 数据抓取与分析 | 每日 9:00/21:00 自动采集 → 质量门禁 → auto-push | `run()`, `_verify()`, `_auto_push()` |
| 工具即插即用 | MCP Server 工具注册 | `mcp-server.py` TOOL_REGISTRY |
| 状态持久化 | snapshot.json + metrics.json + archive | `_save_snapshot()`, `_observe()` |
| 错误恢复 | Selenium 重试 + 源降级 + JSON fallback | `_selenium_extract()` 2 次重试, `_try_fix_truncated_json()` |

---

## 路线图

> ✅ = 已实现  ·  [ ] = 规划中

### Phase 1：MCP 工具协议接入

- [ ] **MCP Client**：通过 stdio 协议发现和调用外部 MCP Server 提供的工具
- [ ] **config.json 支持 mcp_servers 配置**：filesystem、github 等标准 MCP server
- [ ] **MCP 工具自动注册**：tools/list → ToolBase 自动转换 → LLM 可见
- [ ] **mcp_client.py**：实现 tools/list、tools/call、错误处理

### Phase 2：CLI 重构

- [ ] **子命令体系**：`run` / `serve` / `interactive` / `tools` / `trace`
- [ ] **交互式 REPL 模式**：多轮对话持久化，上下文保持
- [ ] **HTTP API 服务**：`agent-loop serve` 启动 FastAPI 端点
- [ ] **Rich 输出**：进度条、彩色日志、Step 回溯

### Phase 3：实时追踪 Dashboard

- [ ] **SSE/WebSocket 推送**：每轮 Step 实时推送到前端
- [ ] **index.html 动态更新**：节点实时高亮、Tool 返回值流式展示
- [ ] **serve.py**：轻量 HTTP 服务 + 事件总线

### Phase 4：多 Provider 策略

- [ ] **LLM Provider 抽象层**：DeepSeek / OpenAI / Anthropic 统一接口
- [ ] **Multi-LLM 路由**：Think 用强模型、Verify 用不同视角模型
- [ ] **模型可配置策略**：reasoning / verification / cheap 三级模型配置

### 其他规划

- [ ] **Streaming 输出**：LLM 响应流式返回，实时显示
- [ ] **Memory 层**：Vector store / SQLite 持久化对话历史
- [ ] **OpenTelemetry Trace**：每步链路追踪，可观测性
- [ ] **Multi-Agent 协作**：Orchestrator + Worker 多 agent 编排
- [ ] **LLM-as-Judge 验证器**：用 LLM 评估输出质量，替代硬编码规则
