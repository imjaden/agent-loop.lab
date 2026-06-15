# Agent Loop Engineering

最小化 AI Agent 循环框架。Think → Act → Observe 闭环，Tool 即插即用。

## 设计理念

```
用户任务
   │
   ▼
┌─────────────────────────────────────┐
│  Agent Loop                         │
│                                     │
│  [Think]  LLM 分析当前上下文         │
│     │  决定：输出答案 or 调用工具     │
│     ▼                               │
│  [Act]   执行工具（web/file/code）   │
│     │                               │
│     ▼                               │
│  [Observe] 结果注入上下文            │
│     │                               │
│     └──→ 回到 [Think]               │
│                                     │
│  直到 LLM 直接输出最终答案            │
└─────────────────────────────────────┘
```

## 快速开始

```bash
pip install openai

# 设置环境变量（必需）
export DEEPSEEK_API_KEY='your-deepseek-api-key'  # https://platform.deepseek.com
export TAVILY_API_KEY='your-tavily-api-key'       # https://tavily.com（免费版每月1000次）

# 命令行传入任务
python3 agent-loop.py "搜索长亭科技的最新动态，当前日期$(date '+%Y-%m-%d')，整理为 markdown 文档"

# 从 stdin 读入（适合复杂任务）
cat task.txt | python3 agent-loop.py

# 指定模型
python3 agent-loop.py --model claude-sonnet-4 "分析 ..."

# 查看帮助
python3 agent-loop.py --help
```

## 内置工具

| 工具 | 功能 |
|:-----|:------|
| `web_search` | 搜索互联网 |
| `web_extract` | 提取网页内容为 markdown |
| `read_file` | 读取本地文件 |
| `write_file` | 写入本地文件 |
| `run_python` | 执行 Python 代码 |

## 自定义工具

```python
from agent-loop import ToolBase, Agent, LLM, LLMConfig

def my_tool(param1: str, param2: int = 10) -> str:
    """工具功能描述（自动生成 schema）"""
    return f"Result: {param1} x {param2}"

tools = [ToolBase("my_tool", "Description", my_tool)]
agent = Agent(LLM(LLMConfig()), tools)
print(agent.run("Use my_tool to ..."))
```

## 环境变量

- `DEEPSEEK_API_KEY` — DeepSeek API Key（https://platform.deepseek.com）
- `TAVILY_API_KEY` — Tavily 搜索 API Key（https://tavily.com，免费版每月1000次）
- `DEEPSEEK_BASE_URL` — API Base URL（可选，默认 https://api.deepseek.com/v1）

## 本 session 验证场景

- 多源 web research → 文档合成（长亭产品分析）
- 代码/HTML 生成（架构图、矩阵）
- 结构化知识梳理（OSI×IPDRR）
- SLA 监控数据抓取与分析
