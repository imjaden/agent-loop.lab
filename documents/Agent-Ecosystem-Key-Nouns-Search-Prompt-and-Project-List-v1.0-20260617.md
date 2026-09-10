# Agent 生态高频关键名词 · 检索 Prompt · 开源项目清单

> 分析日期：2026-06-17
> 来源：documents/ 目录下 4 份分析报告 + GitHub 搜索

---

## 1. 高频关键名词清单

### 1.1 核心概念（Tier 1 — 最高频）

| 名词 | 出现频次 | 所属战场 | 说明 |
|:---|:---:|:---|:---|
| Agent | 112 | A | Agent 循环核心概念，覆盖 Framework / Harness / SDK |
| Harness | 73 | A | 2024-2025 年新兴概念，Agent 编排层 |
| SDK | 51 | A / B | OpenAI SDK / Vercel AI SDK / Agents SDK |
| Framework | 40 | A | LangChain / CrewAI / Mastra 等框架抽象 |
| LLM | 37 | B / G | 大语言模型，AI Agent 的推理引擎 |
| CLI | 26 | C | 命令行工具，开发者交互入口 |
| TUI | 25 | D | 终端用户界面，Ink / Textual 竞争 |
| Runtime | 20 | A / G | LangGraph 持久化执行引擎 |
| ReAct | 19 | A | 推理+行动循环范式（Think→Act 的来源） |
| Toolchain | 11 | B / F | LLM 工具链 vs 传统构建工具链 |
| MCP | 10 | A / B / C | Model Context Protocol，工具标准化协议 |

### 1.2 项目级名词（Tier 2）

| 名词 | 频次 | 生态 | 类型 |
|:---|:---:|:---:|:---|
| LangChain | 29 | Python+TS | Framework / Harness |
| Vercel AI SDK | 26 | TS | SDK / Framework |
| OpenAI | 22 | Python+TS | SDK |
| Pydantic | 20 | Python | 结构化输出 |
| Zod | 20 | TS | 结构化输出 |
| Mastra | 17 | TS | Framework / Harness |
| Ink | 17 | TS | TUI Framework |
| vLLM | 15 | Python | 推理引擎 |
| Textual | 15 | Python | TUI Framework |
| esbuild | 14 | TS | 构建工具 |
| TGI | 12 | Python | 推理引擎 |
| PyTorch | 12 | Python | ML 框架 |
| Instructor | 11 | Python+TS | 结构化输出 |
| Ollama | 11 | Go | 本地推理 |
| Prettier | 10 | TS | CLI 工具 |
| Biome | 10 | Rust+TS | CLI 工具 |
| CrewAI | 10 | Python | Framework |
| Deep Agents | 9 | Python | Harness |
| LangGraph | 8 | Python | Runtime |

### 1.3 中文高频短语（Tier 3）

| 短语 | 频次 | 含义 |
|:---|:---:|:---|
| 推理部署 | 17 | Inference deployment |
| 开发者工具 | 14 | Developer tools (CLI) |
| 工具链 | 14 | Toolchain |
| 数据科学 | 13 | Data Science / ML |
| 终端界面 | 13 | Terminal UI |
| 基础设施 | 10 | Infrastructure |
| 发展史 | 9 | History / evolution |
| 特性对比 | 9 | Feature comparison |
| 侵蚀案例 | 9 | Erosion cases |
| 趋势研判 | 9 | Trend analysis |
| 结构化输出 | 7 | Structured output |
| 类型安全 | 7 | Type safety |
| 持久化执行 | 4 | Durable execution |
| 第一方/第三方 | 4 | First-party / Third-party Harness |

---

## 2. 检索 Prompt

### 2.1 用途

自用 Prompt，可嵌入 Hermes Agent 或手动执行，用于发现和汇总 GitHub 上与 Agent 生态相关的高质量开源项目集合。

### 2.2 Prompt 模板

```
## 任务：检索 Agent 生态开源项目集合

### 目标
检索 GitHub 上与 AI Agent 生态相关的 awesome-*、oh-my-* 类项目集合，
按关键名词分类汇总，输出每个项目的名称、Star 数、描述。

### 关键名词列表（按优先级排序）

#### Tier 1 — 核心概念（必检）
agent, agents, llm, ai, mcp, harness, sdk, framework, runtime, tui, cli, toolchain, guardrails, rag, prompt

#### Tier 2 — 扩展名词（按需）
inference, embedding, vector-database, structured-output, function-calling, quantizaton, fine-tuning, ollama, vllm, react, autonomous, multi-agent, orchestration

#### Tier 3 — 编程语言（交叉检索）
typescript, python, rust, go, javascript, zig

### 检索逻辑

1. **精确匹配搜索**（优先）：
   - `awesome-{关键名词}` — 如 awesome-agent, awesome-llm, awesome-mcp
   - `awesome-{语言}-{关键名词}` — 如 awesome-python-llm, awesome-typescript-agent
   - `oh-my-{关键名词}` — 如 oh-my-agent, oh-my-llm

2. **模糊匹配搜索**（补充）：
   - `awesome {关键名词} {语言} list` — GitHub topic 搜索
   - `best-of {关键名词}` — 如 best-of-mcp, best-of-agent
   - `{关键名词} resources` — 资源集合类

3. **交叉检索**（扩展）：
   - `{语言} {关键名词} framework` — 特定语言的框架集合
   - `awesome {关键名词} {场景}` — 如 awesome-agent-eval, awesome-agent-security

4. **排行榜补充**：
   - `github {关键名词} stars` — 确认 Top 项目的 Star 排名
   - 参考 GitHub Topic 页面自带的仓库排序

### 输出格式

```markdown
## {关键名词分类}

### 项目集合类
| 仓库 | Stars | 描述 |
|:---|:---:|:---|
| user/repo | N | 一句话描述 |

### 代表型工具
| 仓库 | Stars | 类型 | 语言 |
|:---|:---:|:---:|:---:|
| user/repo | N | Framework/Harness/SDK | Python/TS |
```

### 验证规则

1. 排除已归档（archived）仓库
2. 排除 Star < 100 的仓库（除非是新兴热点）
3. 优先选择最近 6 个月有更新的仓库
4. 对同一个 awesome 系列的多个 fork，只保留主分支
5. 标注每个项目的语言生态（Python / TS / Rust / Go）
```

---

## 3. 整合的 GitHub 项目清单

### 3.1 Agent / Agents

| 仓库 | Stars | 语言 | 说明 |
|:---|:---:|:---:|:---|
| kyrolabs/awesome-agents | ~6K | — | Awesome list of AI Agents，最全的 Agent 集合 |
| caramaschiHG/awesome-ai-agents-2026 | ~2K | — | 300+ 资源，20+ 分类，按月更新 |
| ARUNAGIRINATHAN-K/awesome-ai-agents-2026 | ~1K | — | 300+ AI Agents, Frameworks & Coding |
| PunGrumpy/awesome-ai-agents | ~500 | — | AI Agents 框架与工具集合 |

**代表型工具**：

| 仓库 | Stars | 语言 | 类型 |
|:---|:---:|:---:|:---|
| langchain-ai/langchain | 134K | Python+TS | Agent Framework |
| langchain-ai/langgraph | ~12K | Python | Agent Runtime |
| langchain-ai/deepagents | ~6K | Python | Agent Harness |
| joaomdmoura/crewai | 49K | Python | Multi-Agent Framework |
| microsoft/autogen | 53K | Python | Multi-Agent Framework |
| openai/openai-agents-python | ~8K | Python | Agent SDK |
| mastra-ai/mastra | 19K | TS | Agent Framework+Harness |
| vercel/ai | 20K | TS | AI SDK / Agent Framework |
| run-llama/llama_index | 38K | Python | Agent+Document Workflow |

### 3.2 LLM

| 仓库 | Stars | 语言 | 说明 |
|:---|:---:|:---:|:---|
| hannibal046/awesome-llm | ~16K | — | LLM 论文、训练框架、部署工具集合 |
| Shubhamsaboo/awesome-llm-apps | 115K | Python | 100+ AI Agent & RAG 可运行应用 |
| hyp1231/awesome-llm-powered-agent | ~5K | — | LLM 驱动的 Agent 论文与仓库集合 |

### 3.3 MCP（Model Context Protocol）

| 仓库 | Stars | 语言 | 说明 |
|:---|:---:|:---:|:---|
| punkpeye/awesome-mcp-servers | ~62K | — | MCP Servers 集合，400+ 条目 |
| tolkoneoiu/best-of-mcp-servers | ~1K | — | 400 awesome MCP servers，34 分类 |
| patriksimek/awesome-mcp-servers-2 | ~500 | — | 生产级 MCP Servers |
| modelcontextprotocol/servers | ~12K | Python+TS | MCP 官方 Server 实现 |

### 3.4 Prompt Engineering

| 仓库 | Stars | 说明 |
|:---|:---:|:---|
| dair-ai/Prompt-Engineering-Guide | 55K | Prompt Engineering 指南（最权威） |
| promptslab/Awesome-Prompt-Engineering | ~3K | Prompt Engineering 资源集合 |

### 3.5 Guardrails / AI Security

| 仓库 | Stars | 语言 | 说明 |
|:---|:---:|:---:|:---|
| guardrails-ai/guardrails | ~5K | Python | LLM Guardrails 框架 |
| enguard-ai/awesome-ai-guardrails | ~700 | — | AI Guardrails 资源集合 |
| ottosulin/awesome-ai-security | ~1K | — | AI 安全框架与工具 |
| ant-research/awesome-mllm-guardrails | ~500 | — | MLLM Guardrails 集合 |

### 3.6 CLI / TUI

| 仓库 | Stars | 说明 |
|:---|:---:|:---|
| toolleeo/awesome-cli-apps-in-a-csv | ~20K | 最大 CLI/TUI 工具集合 |
| rothgar/awesome-tuis | ~3K | TUI 应用列表 |
| shadawck/awesome-cli-frameworks | ~2K | 跨语言 CLI 框架集合 |
| ratatui/awesome-ratatui | ~2K | Rust TUI 框架 Ratatui 生态 |

### 3.7 Tool LLM

| 仓库 | Stars | 说明 |
|:---|:---:|:---|
| zorazrw/awesome-tool-llm | ~500 | LLM 工具增强（Function Calling）资源 |

### 3.8 推理部署

| 仓库 | Stars | 语言 | 说明 |
|:---|:---:|:---:|:---|
| vllm-project/vllm | 100K+ | Python | 高吞吐 LLM 推理（2025 Octoverse #1）|
| huggingface/text-generation-inference | ~8K | Python | TGI v3.0 推理服务 |
| ollama/ollama | 120K+ | Go | 本地模型运行 |
| bentoml/BentoML | ~7K | Python | 模型部署服务 |
| ggml-org/llama.cpp | 75K+ | C++ | 轻量本地推理 |

### 3.9 结构化输出 / Function Calling

| 仓库 | Stars | 语言 | 说明 |
|:---|:---:|:---:|:---|
| instructor-ai/instructor | ~11K | Python+TS | LLM 结构化输出（Pydantic/Zod 驱动）|
| pydantic/pydantic | 22K | Python | 类型校验→JSON Schema |
| colinhacks/zod | 35K | TS | TS 类型校验→JSON Schema |

### 3.10 Toolchain / 构建

| 仓库 | Stars | 语言 | 说明 |
|:---|:---:|:---:|:---|
| evanw/esbuild | 38K | Go+TS | JS/TS 构建，速度 100x |
| biomejs/biome | 15K | Rust+TS | Format+Lint 统一工具 |
| astral-sh/uv | ~30K | Rust+Python | Python 包管理（Rust pip）|

---

## 4. 开源项目检索的推荐工作流

```
1. 确定关键名词
   ↓
2. 优先搜索 awesome-{名词}（GitHub topic 搜索）
   ↓
3. 补充搜索 best-of-{名词}、oh-my-{名词}
   ↓
4. 按 Stars 排序，筛选 Top 10
   ↓
5. 确认最近更新日期（排除已归档）
   ↓
6. 按语言生态分类（Python / TS / Rust / Go）
   ↓
7. 输出结构化清单（表格 + Stars + 类型标注）
```

---

## 📋 元信息

| 项目 | 内容 |
|:---|:---|
| 助手名称 | IRIS (byHermes) |
| 创建时间 | 2026-06-17 |
| 信息来源 | documents/ 分析报告 + GitHub 搜索 |
