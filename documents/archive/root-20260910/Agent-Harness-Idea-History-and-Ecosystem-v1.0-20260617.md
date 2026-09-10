# Agent Harness：理念、发展史与生态

> 分析日期：2026-06-17
> 核心数据源：LangChain Blog (Harrison Chase 2025.10)、Hanchung's Blog 技术债系列、arXiv Harness 综述

---

## 1. 什么是 Agent Harness

**定义**：Agent 模型中模型（Model）与运行环境（Environment）之间的编排层（Orchestration Layer）。

```
Model (LLM)  ←→  Harness  ←→  Environment (Tools / Files / APIs)
```

**核心类比**：

| 传统系统 | Agent 系统 |
|:---|:---|
| CPU | Foundation Model (LLM) |
| **操作系统** | **Agent Harness**（管理中断、内存、I/O、进程） |
| 应用程序 | Agent 执行的 Task |

**一句话**：Harness 是"让 LLM 能做事"的那层基础设施——它决定模型能看到什么工具、如何管理上下文、什么时候停止、失败了怎么办。

---

## 2. 核心理念与哲学

### 2.1 Harness = 结构，但结构终将被模型吃掉

Rich Sutton 的 Bitter Lesson（苦涩教训）应用于 Agent Harness：

> "Add structure for the level of compute you have, then remove it, because the structure becomes the bottleneck for the next level of compute."
> — Hyung Won Chung (Meta)

这意味着：
- 2024 年需要手写的编排逻辑（workflow builder、tool wrapper、context manager）
- 2025-2026 年正在被模型自身的能力"吃掉"——模型越来越能直接处理原始信息
- **Harness 设计原则**："Build the durable substrate like you mean to keep it. Build each production harness like you mean to replace it."

### 2.2 两个 Harness 类型的对立

| 类型 | 谁构建 | 用途 | 演进节奏 |
|:---|:---|:---|:---:|
| **Inner Harness** | 模型创建者（Anthropic / OpenAI） | 模型后训练 + 推理时的默认行为 | 大版本迭代 |
| **Outer Harness** | 用户/集成方 | 自定义工具、企业规则、安全策略 | 持续迭代 |

**关键不对称**：
- Training Harness（训练）：最大化动作空间，鼓励尝试，欢迎失败（信号给优化器）
- Production Harness（生产）：最小化权限，禁止失败，fail closed
- 两者不能简单复用

**桥梁**：Evaluation Harness——紧密镜像生产环境，由对齐团队拥有，捕获研究和产品之间的行为回归。

---

## 3. 发展史（术语演变）

### 3.1 萌芽期（2022-2023）：没有 Harness，只有 Prompt

最早用 LLM 构建 Agent 的方式极其原始——手写 prompt + 手动解析输出。没有标准化的工具抽象，没有上下文管理。

### 3.2 框架期（2023-2024）：Agent Framework 统治

LangChain、AutoGPT、BabyAGI 等框架出现，提供了"Chain"和"Tool"抽象。此时没有人区分 Framework / Runtime / Harness——所有东西都叫"Agent 框架"。

### 3.3 "Harness 转向"（2024-2025）：概念分化

2024 年末到 2025 年，行业认识到 Agent 系统的复杂度远超框架能覆盖的范围。Harness 概念从学术界进入工程实践。

**关键节点**：

| 时间 | 事件 | 意义 |
|:---|:---|:---|
| 2024 Q3 | Anthropic 发布 Claude Agent SDK | 第一个明确以"Agent Harness"定位的产品 |
| 2024 Q4 | OpenAI Codex CLI 发布 | 编码 Agent 的 Harness 模式 |
| 2025 Q1 | Cursor Auto 模式 | 代码编辑器内置 Harness |
| 2025 Q2 | LangChain Deep Agents 发布 | "Batteries-included agent harness" |
| 2025.10 | Harrison Chase 博客 | 正式定义 Framework / Runtime / Harness 三层 |
| 2026 | arXiv Harness 综述论文 | Harness 成为独立研究方向 |

### 3.4 术语三角：Framework vs Runtime vs Harness

Harrison Chase（LangChain CEO）在 2025.10 的博客中做了最权威的区分：

| 层 | 提供什么 | 使用场景 | 代表项目 |
|:---|:---|:---|:---|
| **Agent Framework** | 抽象和心智模型（Abstractions） | 快速原型、标准化构建模式 | LangChain, Vercel AI SDK, CrewAI |
| **Agent Runtime** | 持久化执行、流式、人机协同（Infrastructure） | 生产部署、长时运行 | LangGraph, Temporal, Inngest |
| **Agent Harness** | 开箱即用的完整 Agent 能力（Batteries-included） | 端到端 Agent，无需自己编排 | Deep Agents, Claude Agent SDK |

**注意**：边界模糊——LangGraph 既是 Runtime 也是 Framework；Vercel AI SDK 的 Agent 功能越来越像 Harness。

---

## 4. Harness 的核心组件

一个完整的 Agent Harness 通常包含：

| 组件 | 说明 | 演变趋势 |
|:---|:---|:---:|
| **System Prompt & Persona** | 模型行为的常设指令 | 2025: 手动写 → 2026: 根据任务自动生成 |
| **Tool Surface** | 可调用的函数集合 + Schema | 2024: 手写 wrapper → 2026: 自动从 OpenAPI/MCP 发现 |
| **Rollout Protocol** | ReAct / Plan-and-Execute / Multi-Agent Loop | 2024: 硬编码 → 2026: 模型自主选择策略 |
| **Context Manager** | 跨轮次携带/压缩/丢弃的上下文 | 2025: 截断 → 2026: 智能压缩 + 分层记忆 |
| **Memory** | 短期 / 中期 / 长期存储 | 2025: 手写 → 2026: Mem0 / Letta 等专业服务 |
| **Sub-agent Topology** | Orchestrator / Worker / Judge / Hand-off | 2024: 单一 Agent → 2026: 自适应拓扑 |
| **Guardrails & Gates** | 输入/输出过滤、权限审批 | 2024: 简单的 Allowlist → 2026: RBAC + MCP 策略 |
| **Verifiers & Judges** | 步骤成功判定、继续/停止决策 | 2024: 规则检查 → 2026: LLM-as-Judge |
| **Observability** | 追踪、回放、评估钩子 | 2025: LangSmith / LangFuse 等专业平台 |

---

## 5. 代表型项目（Python 生态）

| 项目 | 类型 | Stars | 语言 | Harness 定位 |
|:---|:---|:---:|:---:|:---|
| **LangChain Deep Agents** | Harness | ~6K | Python | "通用版 Claude Code"，内置规划、文件系统、工具调用 |
| **LangGraph** | Runtime + Framework | ~12K | Python | 持久化执行引擎，支持人机协同与复杂状态机 |
| **LangChain** | Framework | 134K | Python | 最早的 Agent 抽象层，Chain + Tool 模式 |
| **CrewAI** | Framework | 49K | Python | 角色化多 Agent 编排（倾向 Framework，接近 Harness）|
| **PydanticAI** | Framework | 15K | Python | 类型安全的 Agent 框架，结构化输出原生 |
| **OpenAI Agents SDK** | Framework + Harness | ~8K | Python | 最小抽象层 + 管理式 Agent 运行时 |
| **Smolagents**（HuggingFace） | Framework | ~10K | Python | 轻量级 Agent，支持代码 Agent 模式 |
| **BeeAI**（IBM） | Framework | ~5K | Python | IBM 的 Agent 框架，企业导向 |

### Python 生态格局

```
                 Framework                    Runtime                   Harness
   简单原型 ────────────────────────────────────────────────────── 生产就绪

   LangChain ─────────────────────────────────────────────────────────
   CrewAI ─────────────────────
   PydanticAI ─────────────
   OpenAI SDK ────────────────────────
   Smolagents ────────────
   
                              LangGraph ──────────────────────────
                              Deep Agents ────────────────────────────
```

---

## 6. 代表型项目（TypeScript 生态）

| 项目 | 类型 | Stars | 语言 | Harness 定位 |
|:---|:---|:---:|:---:|:---|
| **Vercel AI SDK** | Framework → Harness | 20K | TS | 从 Streaming-first SDK 进化为完整 Agent 框架，2.8M/wk |
| **Mastra** | Framework + Harness | 19K | TS | TS-native Agent 框架，内置 Memory / MCP / Studio |
| **LangChain.js** | Framework | 16.6K | TS | LangChain 的 JS 移植 |
| **OpenAI Agents SDK (TS)** | Framework + Harness | ~2K | TS | OpenAI 官方 TS 版，128K/wk |
| **Claude Agent SDK**（Anthropic） | Harness | — | TS | 管理式 Agent，第一方 Harness |
| **Genkit**（Google） | Framework | ~6K | TS | Google 的 AI 应用框架，GCP 集成 |
| **CopilotKit** | Framework | ~9K | TS | React 组件级 AI 集成 |

### TypeScript 生态格局

```
                 Framework                    Runtime                   Harness
   简单原型 ────────────────────────────────────────────────────── 生产就绪

   Vercel AI SDK ──────────────────────────────────
   Mastra ─────────────────────────────────────────────
   LangChain.js ────────────────────
   CopilotKit ────────────
   Genkit ──────────────────
   
                              (TS 原生 Runtime 层几乎空白)
                              Mastra 正在填补这个位置
                              
                              Claude Agent SDK ─────────────────
                              OpenAI TS SDK ──────────────────────
```

---

## 7. 第一方 vs 第三方 Harness（Benchmark 对比）

**关键问题**：模型在自己的 Harness 中表现最好（第一方优势）？

Empirical data（Post-train benchmark）：

| 模型 | 第一方 Harness | 第三方 Harness | 差异 |
|:---|:---:|:---:|:---:|
| GPT-5.1 Codex Max | **20.2%** | 7.7% | 大幅领先 |
| Gemini 3 Pro | **18.3%** | 14.9% | 显著领先 |
| Claude Opus 4.5 | **17.3%** | 17.1% | 几乎持平 |

**例外**：Letta Code（第三方）在 Claude Opus 4.5 上以 **59.1% vs 41.6%** 击败了 Claude Code（第一方）——因为 Letta 在持久记忆（Durable Memory）上投入了更多。

**结论**：
- 模型在训练时的 Harness 中表现最好（惯性与对齐优势）
- 但第三方 Harness 如果在一个特定维度（如 Memory）上深度投入，可以反超
- "Harness is load-bearing"——Harness 的选择直接影响模型表现

---

## 8. 趋势与前瞻

### 8.1 Harness 组件正在被模型"吃掉"

| 2024 年的结构 | 2025-2026 状态 |
|:---|:---|
| 无代码工作流构建器 | 正在被单一长 Horizon Agent 取代 |
| 手写 Tool Wrapper | 模型直接读 OpenAPI Spec / MCP |
| Context 截断 | 模型自主管理上下文（如 Gemini 的 10M context）|
| 硬编码 ReAct | 模型自主选择策略（Plan / Act / Reflect）|

### 8.2 三层架构将收敛为两层？

- Harrison Chase 预测：Framework 和 Harness 可能合并
- Runtime（持久化执行）作为独立基础设施层保留
- 最终格局：**Agent Runtime（底层） + Agent Framework/Harness（上层）**

### 8.3 Python vs TypeScript 在 Harness 层的竞争

| 维度 | Python | TypeScript |
|:---|:---|:---|
| Harness 数量 | 多且成熟（Deep Agents, LangGraph, OpenAI SDK） | 增长最快（Mastra, Vercel AI SDK） |
| 第一方 Harness | 少（OpenAI SDK） | 有明显优势（Claude Agent SDK, Codex CLI） |
| 第三方 Harness 质量 | 高（企业级特性） | 正在追赶（Mastra 势头猛） |
| 分发体验 | pip install | npx / npm（零安装优势） |
| 底层绑定 | Python→CUDA C++ 优势 | 无 |

### 8.4 对选型者的启示

| 你的场景 | 推荐 Harness | 理由 |
|:---|:---|:---|
| 快速原型验证 | LangChain / Vercel AI SDK | 抽象层丰富，上手快 |
| 生产级 Agent 服务 | LangGraph + Deep Agents | 持久化执行 + 开箱即用 |
| TypeScript 全栈团队 | Mastra / Vercel AI SDK | 不换语言，统一技术栈 |
| 编码 Agent | Claude Code / Deep Agents / Codex CLI | 第一方 Harness 有优势 |
| 安全 / 合规场景 | 自建 Outer Harness（Guardrails + MCP） | 企业级控制需求 |

---

## 9. 参考资料

- [Agent Frameworks, Runtimes, and Harnesses – oh my!](https://www.langchain.com/blog/agent-frameworks-runtimes-and-harnesses-oh-my) — Harrison Chase, LangChain CEO, 2025.10
- [Hidden Technical Debt of AI Systems: Agent Harness](https://leehanchung.github.io/blogs/2026/05/08/hidden-technical-debt-agent-harness/) — Hanchung's Blog, 2026.05
- [Agent Harness Engineering — The Rise of the AI Control Plane](https://medium.com/@adnanmasood/agent-harness-engineering-the-rise-of-the-ai-control-plane-938ead884b1d) — Adnan Masood
- [Agent Systems with Harness Engineering (Survey)](https://github.com/RUCAIBox/awesome-agent-harness) — arXiv, 2026
- [Natural-Language Agent Harnesses](https://arxiv.org/html/2603.25723v1) — arXiv, 2026
- [Choosing Your Agent Harness](https://pub.towardsai.net/choosing-your-agent-harness-an-architectural-comparison-of-claude-managed-agents-langchain-deep-a0762804ec07) — Towards AI
- [Deep Agents Overview](https://docs.langchain.com/oss/python/deepagents/overview) — LangChain Docs

---

## 📋 元信息

| 项目 | 内容 |
|:---|:---|
| 助手名称 | IRIS (byHermes) |
| 创建时间 | 2026-06-17 |
| 信息来源 | LangChain Blog, Hanchung Tech Blog, arXiv, GitHub |
