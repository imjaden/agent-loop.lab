"""
Agent Loop Engineering v2 — 最小化 Agent 循环框架

Version: 2.0(2026-06-16)
Description
- 基于 Loop Engineering 方法论的 AI Agent 循环框架
- Think → Act → Observe → Verify 闭环执行
- 支持多工具调用、状态持久化、预算控制

设计原则（源自 Loop Engineering 方法论）：
  1. 持续运行 — 后台自动推进，不占人注意力
  2. 状态感知 — 读取进度状态，断点续跑
  3. 自动验证 — 输出自检，不合格自动重试
  4. 预算控制 — Token/时间/失败 三重上限
  5. 停止条件 — 明确的终止信号，避免无效循环

Loop 范式：user_task → [think → act → observe → verify]ⁿ → done

LLM 默认：deepseek-v4-flash（OpenAI 兼容，轻量快速）

【指令清单】
| 指令 | 功能说明 |
|------|---------|
| python3 agent-loop.py <任务> | 直接执行任务 |
| --model <模型> | 指定 LLM 模型 |
| --api-key <key> | 指定 API Key |
| --system <文件> | 自定义系统提示词 |
| --checkpoint <路径> | 检查点文件路径 |
| --max-iter <N> | 最大迭代次数 |
| --max-duration <秒> | 最大运行时长 |
| --quiet | 静默模式 |
| --pretty/report/markdown | 输出格式 |

【辅助工具】
| 工具方法 | 功能说明 |
|---------|---------|
| _format_path() | 路径格式化，支持项目相对路径 |
| _print_with_emoji() | 智能打印，自动匹配 Emoji 前缀 |
| _load_secrets() | 从 secret-manager 加载敏感信息 |

Environments:
- Python 3.12+
- IDE: TRAE CN
- LLM: deepseek-v4-flash

Related Paths
- 项目路径: ~/CodeSpace/AgentLoop
- 缓存目录: /tmp/_agent_*

Dependency
- openai
- requests (用于 Tavily API)

敏感信息管理
- DEEPSEEK_API_KEY: DeepSeek API Key
- TAVILY_API_KEY: Tavily 搜索 API Key
- 推荐使用 secret-manager 统一管理
"""

import json, os, subprocess, sys, time, hashlib
from dataclasses import dataclass, field, asdict
from typing import Callable, Optional
from datetime import datetime, timezone
from pathlib import Path


# ──────────────────────────────────────────────
# 0. 辅助工具
# ──────────────────────────────────────────────

class AgentHelper:
    """Agent Loop 辅助工具类"""

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or os.path.dirname(os.path.abspath(__file__)))

    def _format_path(self, absolute_path: str) -> str:
        """【辅助工具】格式化路径：绝对路径若包含当前项目路径，则打印相对路径"""
        try:
            abs_p = Path(absolute_path).resolve()
            if str(abs_p).startswith(str(self.project_root)):
                return os.path.relpath(absolute_path, os.getcwd())
        except (ValueError, OSError):
            pass
        return absolute_path

    def _print_with_emoji(self, message: str, prefix_emoji: str = None):
        """【辅助工具】智能打印：根据内容自动添加 Emoji 前缀

        Args:
            message: 打印内容
            prefix_emoji: 强制指定 Emoji（可选），未指定时根据内容智能匹配
        """
        if prefix_emoji:
            print(f"{prefix_emoji} {message}")
            return

        msg_lower = message.lower()
        emoji_rules = [
            (['完成', '成功', 'done', '已生成', '已创建', '已更新', 'success', 'ok', 'written'],
             '✅'),
            (['错误', '失败', 'error', 'fail', '中止', '不存在', 'missing'], '❌'),
            (['警告', '注意', 'warning', 'warn', '已过期', '检测', '已有'], '⚠️'),
            (['帮助', 'help', '文档', '说明'], '📖'),
            (['创建', '笔记', '写入', 'create', 'write'], '📝'),
            (['缓存', '保存', 'cache', 'save', 'checkpoint'], '💾'),
            (['思考', 'thinking', '分析', 'analyzing'], '🤔'),
            (['执行', '运行', 'executing', 'running'], '⚙️'),
            (['验证', 'verify', '检查', 'check'], '🔍'),
            (['迭代', 'iter', 'iteration'], '🔄'),
        ]

        for keywords, emoji in emoji_rules:
            if any(k in msg_lower for k in keywords):
                print(f"{emoji} {message}")
                return

        print(f"ℹ️ {message}")

    def _load_secrets(self) -> dict:
        """【辅助工具】从 secret-manager 加载敏感信息"""
        try:
            secret_manager_path = Path.home() / 'CodeSpace' / 'script-miner' / 'efficiency' / 'secret_manager.py'
            if secret_manager_path.exists():
                sys.path.append(str(secret_manager_path.parent))
                from secret_manager import SecretManager
                sm = SecretManager()
                return sm._secrets
        except ImportError:
            pass
        return {}


# 全局辅助工具实例
helper = AgentHelper()


# ──────────────────────────────────────────────
# 1. LLM 接口（OpenAI 兼容，默认 deepseek-v4-flash）
# ──────────────────────────────────────────────

DEEPSEEK_BASE = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

@dataclass
class LLMConfig:
    api_key: str = DEEPSEEK_KEY or ""
    base_url: str = DEEPSEEK_BASE
    model: str = "deepseek-v4-flash"
    max_tokens: int = 16384

class LLM:
    """OpenAI 兼容 LLM 调用层，自动选择 base_url"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = None

    def _ensure(self):
        if self._client is None:
            if not self.config.api_key:
                raise ValueError(
                    "缺少 DEEPSEEK_API_KEY 环境变量。\n"
                    "请设置环境变量后重试：\n"
                    "  export DEEPSEEK_API_KEY='your-api-key-here'\n"
                    "或在命令行中指定：\n"
                    "  python agent-loop.py --api-key 'your-api-key-here' ..."
                )
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
            )

    def chat(self, messages: list, tools: list = None, temperature: float = 0.3) -> dict:
        self._ensure()
        kwargs = dict(
            model=self.config.model,
            messages=messages,
            temperature=temperature,
            max_tokens=self.config.max_tokens,
        )
        if tools:
            kwargs["tools"] = [t.openai_schema() for t in tools]
            kwargs["tool_choice"] = "auto"
        resp = self._client.chat.completions.create(**kwargs)
        return self._parse(resp)

    def _parse(self, resp) -> dict:
        msg = resp.choices[0].message
        result = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            # 保留原始的 OpenAI 格式，用于后续消息传递
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in msg.tool_calls
            ]
            # 同时保存解析后的格式，方便工具执行
            result["_parsed_tool_calls"] = [
                {"id": tc.id, "name": tc.function.name,
                 "args": json.loads(tc.function.arguments)}
                for tc in msg.tool_calls
            ]
        return result


# ──────────────────────────────────────────────
# 2. Tool 抽象
# ──────────────────────────────────────────────

@dataclass
class ToolBase:
    name: str
    description: str
    handler: Callable

    def openai_schema(self) -> dict:
        import inspect
        sig = inspect.signature(self.handler)
        props, required = {}, []
        for p_name, p_param in sig.parameters.items():
            if p_name == "self":
                continue
            props[p_name] = {"type": "string", "description": f"Parameter: {p_name}"}
            if p_param.default is inspect.Parameter.empty:
                required.append(p_name)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object", "properties": props, "required": required},
            }
        }

    def execute(self, **kwargs) -> str:
        try:
            result = self.handler(**kwargs)
            return str(result)[:8000]
        except Exception as e:
            return f"[Tool Error] {self.name}: {e}"


# ──────────────────────────────────────────────
# 3. Loop 工程 · 验证器
# ──────────────────────────────────────────────

class Verifier:
    """输出验证器：检查结果质量，支持自定义检查项"""

    DEFAULT_CHECKS = [
        ("最小长度",  lambda t: len(t) > 100,       "内容过短（<100 chars）"),
        ("有实质内容", lambda t: len(t.split()) > 20, "内容缺少实质性信息"),
    ]

    def __init__(self, checks: list = None):
        self.checks = checks or self.DEFAULT_CHECKS
        self.failures = []

    def verify(self, text: str) -> bool:
        self.failures = []
        for name, fn, msg in self.checks:
            if not fn(text):
                self.failures.append(f"  ❌ [{name}] {msg}")
        return len(self.failures) == 0

    def summary(self) -> str:
        if not self.failures:
            return "  ✅ All checks passed"
        return "\n".join(self.failures)


# ──────────────────────────────────────────────
# 4. Loop 工程 · 预算控制器
# ──────────────────────────────────────────────

@dataclass
class Budget:
    max_iterations: int = 25
    max_tokens: int = 16384      # 估算上限
    max_retries: int = 3          # 验证失败重试上限
    max_duration: int = 600       # 秒
    start_time: float = field(default_factory=time.time)

    @property
    def elapsed(self) -> float:
        return time.time() - self.start_time

    @property
    def expired(self) -> bool:
        if self.elapsed > self.max_duration:
            return True
        return False

    def remaining_str(self) -> str:
        return f"⏱ {self.elapsed:.0f}/{self.max_duration}s"


# ──────────────────────────────────────────────
# 5. Loop 工程 · 状态持久化
# ──────────────────────────────────────────────

@dataclass
class LoopState:
    """可持久化的循环状态，支持断点续跑"""
    task_id: str = ""
    iteration: int = 0
    status: str = "running"       # running | done | failed | budget_exceeded
    summary: str = ""
    checkpoint_path: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def save(self, path: str = ""):
        if path:
            self.checkpoint_path = path
        if self.checkpoint_path:
            os.makedirs(os.path.dirname(self.checkpoint_path) or ".", exist_ok=True)
            with open(self.checkpoint_path, "w") as f:
                json.dump(asdict(self), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str) -> Optional["LoopState"]:
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            return cls(**data)
        return None


# ──────────────────────────────────────────────
# 6. Agent 循环核心
# ──────────────────────────────────────────────

@dataclass
class Step:
    iteration: int
    role: str            # think | act | observe | verify
    content: str = ""
    tool_name: str = ""
    tool_args: dict = field(default_factory=dict)
    tool_result: str = ""

class Agent:
    """
    Loop 架构：
      user_task → [think → act → observe → verify]ⁿ → final_answer

    特性：
      - 自动验证：每轮输出通过 Verifier 检查，不合格重试
      - 预算控制：迭代/时间/重试 三重上限
      - 状态持久化：支持 save/load 断点续跑
      - 历史审计：每步的 think/act/observe/verify 可回溯
    """

    def __init__(self, llm: LLM, tools: list[ToolBase],
                 system_prompt: str = "",
                 verifier: Verifier = None,
                 budget: Budget = None):
        self.llm = llm
        self.tools = {t.name: t for t in tools}
        self.system_prompt = system_prompt
        self.verifier = verifier or Verifier()
        self.budget = budget or Budget()
        self.messages = []
        self.history: list[Step] = []
        self.state = LoopState()
        self._retry_count = 0

    def run(self, task: str, verbose: bool = True,
            checkpoint: str = "") -> str:
        """执行 Agent 循环"""
        self.messages = []
        self.history = []

        # 状态初始化
        self.state = LoopState(
            task_id=hashlib.md5(task.encode()).hexdigest()[:12],
            checkpoint_path=checkpoint or "",
        )

        if self.system_prompt:
            self.messages.append({"role": "system", "content": self.system_prompt})
        self.messages.append({"role": "user", "content": task})

        for i in range(1, self.budget.max_iterations + 1):
            self.state.iteration = i

            # ── 预算检查 ──
            if self.budget.expired:
                self.state.status = "budget_exceeded"
                self.state.summary = f"Budget exceeded ({self.budget.elapsed:.0f}s)"
                if verbose:
                    helper._print_with_emoji(f"Budget exceeded at iteration {i}", '⏰')
                break

            # ── Think ──
            if verbose:
                print(f"\n{'─'*50}\n[Iter {i}] 🤔 Thinking... [{self.budget.remaining_str()}]")

            resp = self.llm.chat(self.messages, tools=list(self.tools.values()))

            # 构建完整的 assistant 消息（包含 tool_calls）
            assistant_msg = {"role": resp["role"], "content": resp.get("content", "")}
            if resp.get("tool_calls"):
                assistant_msg["tool_calls"] = resp["tool_calls"]
            self.messages.append(assistant_msg)

            step = Step(iteration=i, role="think", content=resp.get("content", ""))
            self.history.append(step)

            # ── 直接输出答案 → 验证 → 结束 ──
            if not resp.get("tool_calls"):
                answer = resp.get("content", "")
                if self.verifier.verify(answer):
                    if verbose:
                        helper._print_with_emoji(f"Verified ({len(answer)} chars)", '✅')
                        print(self.verifier.summary())
                    self.state.status = "done"
                    self.state.summary = f"Completed in {i} iterations"
                    self.state.save()
                    return answer
                else:
                    # 验证失败 → 重试
                    self._retry_count += 1
                    if self._retry_count > self.budget.max_retries:
                        if verbose:
                            helper._print_with_emoji(f"Max retries ({self.budget.max_retries}) exceeded", '❌')
                        # 返回最后一次的结果，附带失败说明
                        self.state.status = "failed"
                        self.state.summary = f"Failed after {self._retry_count} retries"
                        self.state.save()
                        return (
                            f"{answer}\n\n"
                            f"---\n⚠️ Verification failed after {self._retry_count} retries:\n"
                            + self.verifier.summary()
                        )
                    if verbose:
                        helper._print_with_emoji(f"Verification failed, retrying ({self._retry_count}/{self.budget.max_retries})", '🔄')
                        print(self.verifier.summary())
                    # 注入验证失败反馈，让 LLM 改进
                    self.messages.append({
                        "role": "user",
                        "content": f"质量检查未通过，请改进：\n{self.verifier.summary()}"
                    })
                    continue

            # ── Act: 执行工具 ──
            for tc in resp.get("_parsed_tool_calls", []):
                tool = self.tools.get(tc["name"])
                if not tool:
                    result = f"[Unknown tool: {tc['name']}]"
                    helper._print_with_emoji(f"Unknown tool: {tc['name']}", '⚠️')
                else:
                    if verbose:
                        print(f"[Iter {i}] 🛠  {tc['name']}({json.dumps(tc['args'], ensure_ascii=False)[:200]})")
                    result = tool.execute(**tc['args'])

                # ── Observe ──
                self.messages.append({
                    "role": "tool", "tool_call_id": tc["id"], "content": result
                })
                step = Step(iteration=i, role="act",
                            tool_name=tc["name"], tool_args=tc["args"],
                            tool_result=result[:200])
                self.history.append(step)

                if verbose:
                    preview = result[:120].replace("\n", " ")
                    print(f"         ↳ {preview}...")

            # 每轮保存检查点
            if self.state.checkpoint_path:
                self.state.save()

        # 循环自然结束
        self.state.status = "max_iterations"
        self.state.summary = f"Reached max {self.budget.max_iterations} iterations"
        self.state.save()
        last = self.messages[-1].get("content", "") if self.messages else ""
        return last or "[Max iterations reached — no final output]"


# ──────────────────────────────────────────────
# 7. 内置 Tool 工厂
# ──────────────────────────────────────────────

def make_tools(workdir: str = ".") -> list[ToolBase]:

    def web_search(query: str, limit: int = 5) -> str:
        """Search the web for information."""
        tavily_key = os.environ.get("TAVILY_API_KEY", "")
        if not tavily_key:
            return (
                "[web_search 错误] 缺少 TAVILY_API_KEY 环境变量。\n"
                "请设置后重试：export TAVILY_API_KEY='your-tavily-key'\n"
                "或使用其他搜索方式。"
            )
        import urllib.parse
        encoded = urllib.parse.quote(query)
        r = subprocess.run(
            ["curl", "-s",
             "-H", f"Authorization: Bearer {tavily_key}",
             f"https://api.tavily.com/search?query={encoded}&limit={limit}"],
            capture_output=True, text=True, timeout=15
        )
        if r.stdout.strip():
            return r.stdout[:6000]
        return f"[web_search] No results for: {query}"

    def web_extract(url: str) -> str:
        """Extract content from a URL."""
        r = subprocess.run(
            ["curl", "-sL", url, "-o", "/tmp/_agent_page.html", "-w", "%{http_code}"],
            capture_output=True, text=True, timeout=30
        )
        if r.stdout.strip() == "200":
            size = os.path.getsize("/tmp/_agent_page.html")
            return f"[Fetched {size} bytes from {url}]"
        return f"HTTP {r.stdout.strip()}"

    def read_file(path: str) -> str:
        """Read a local file."""
        full = path if path.startswith("/") else os.path.join(workdir, path)
        if not os.path.exists(full):
            return f"[File not found: {full}]"
        with open(full) as f:
            return f.read()[:8000]

    def write_file(path: str, content: str) -> str:
        """Write content to a local file."""
        full = path if path.startswith("/") else os.path.join(workdir, path)
        os.makedirs(os.path.dirname(os.path.abspath(full)), exist_ok=True)
        with open(full, "w") as f:
            f.write(content)
        return f"✅ Written: {full} ({len(content)} bytes)"

    def run_python(code: str) -> str:
        """Execute Python code in a subprocess."""
        with open("/tmp/_agent_exec.py", "w") as f:
            f.write(code)
        r = subprocess.run(
            ["python3", "/tmp/_agent_exec.py"],
            capture_output=True, text=True, timeout=30
        )
        out = r.stdout.strip()[:4000]
        err = r.stderr.strip()[:2000]
        if err:
            out += f"\n[stderr]\n{err}"
        return out or "(no output)"

    return [
        ToolBase("web_search",  "Search the web for information", web_search),
        ToolBase("web_extract", "Extract content from a URL",     web_extract),
        ToolBase("read_file",   "Read a local file",              read_file),
        ToolBase("write_file",  "Write content to a local file",  write_file),
        ToolBase("run_python",  "Execute Python code",            run_python),
    ]


# ──────────────────────────────────────────────
# 8. 默认系统提示词
# ──────────────────────────────────────────────

DEFAULT_SYSTEM_PROMPT = """你是 ALoop，一名售前架构师 AI 助手。

## Loop 工作方式

按照「思考 → 行动 → 观察 → 验证」循环推进任务：
1. 先思考当前需要什么信息或操作
2. 调用工具获取结果
3. 观察结果，决定下一步
4. 输出最终答案前，确保内容充实且有实质价值

## 行为准则

- 结论优先：先给核心结论，再给细节。用表格/列表组织复杂信息
- 售前视角：站在客户业务价值角度思考
- 文件规范：{主题名称}-v{主版本}.{次版本}-{日期}.md

可用工具：web_search, web_extract, read_file, write_file, run_python
"""


# ──────────────────────────────────────────────
# 9. 入口
# ──────────────────────────────────────────────


def _print_help():
    """【打印帮助信息】"""
    print("\n" + "=" * 60)
    print("📖 Agent Loop v2 使用说明")
    print("=" * 60)

    print("\n【功能概述】")
    print("  基于 Loop Engineering 方法论的 AI Agent 循环框架")
    print("  Think → Act → Observe → Verify 闭环执行任务")

    print("\n【环境变量】")
    print("  DEEPSEEK_API_KEY     - DeepSeek API Key（必需）")
    print("  TAVILY_API_KEY      - Tavily 搜索 API Key（必需）")
    print("  DEEPSEEK_BASE_URL   - API Base URL（可选）")

    print("\n【输出格式】")
    print("  --pretty                   - PrettyTable 表格格式（默认）")
    print("  --report                   - 简洁报告格式")
    print("  --markdown                 - Markdown 格式")

    print("\n【支持的参数】")
    print("  <任务>              - 直接执行任务")
    print("  --model <模型>      - 指定 LLM 模型")
    print("  --api-key <key>     - 指定 API Key")
    print("  --base-url <url>    - 指定 API Base URL")
    print("  --system <文件>     - 自定义系统提示词文件")
    print("  --workdir <目录>     - 工作目录")
    print("  --checkpoint <路径> - 检查点文件路径")
    print("  --max-iter <N>       - 最大迭代次数（默认 25）")
    print("  --max-duration <秒> - 最大运行时长（默认 600）")
    print("  --quiet             - 静默模式")

    print("\n【内置工具】")
    print("  web_search   - 搜索互联网（需要 TAVILY_API_KEY）")
    print("  web_extract  - 提取网页内容")
    print("  read_file    - 读取本地文件")
    print("  write_file   - 写入本地文件")
    print("  run_python   - 执行 Python 代码")

    print("\n【使用示例】")
    print("  python3 agent-loop.py '搜索长亭科技最新动态，当前日期\$(date \"+%Y-%m-%d\")，整理为 markdown 文档'")
    print("  python3 agent-loop.py '分析代码' --model claude-sonnet-4")
    print("  python3 agent-loop.py '完成任务' --max-iter 10 --report")
    print("  python3 agent-loop.py --system custom-prompt.txt '任务'")

    print("\n" + "=" * 60)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Agent Loop Engineering v2", add_help=False)
    parser.add_argument("task", nargs="*", help="Task prompt")
    parser.add_argument("--model", default="", help="Model override")
    parser.add_argument("--base-url", default="", help="API base URL override")
    parser.add_argument("--api-key", default="", help="API key override")
    parser.add_argument("--system", default="", help="Custom system prompt file")
    parser.add_argument("--workdir", default=".", help="Working directory")
    parser.add_argument("--checkpoint", default="", help="Path for state persistence")
    parser.add_argument("--max-iter", type=int, default=0, help="Max iterations")
    parser.add_argument("--max-duration", type=int, default=0, help="Max duration (seconds)")
    parser.add_argument("--quiet", action="store_true", help="Suppress iteration output")
    parser.add_argument("--pretty", action="store_true", help="Pretty output")
    parser.add_argument("--report", action="store_true", help="Report output")
    parser.add_argument("--markdown", action="store_true", help="Markdown output")
    parser.add_argument("--help", "-h", action="store_true", help="Show this help message")
    args = parser.parse_args()

    # 显示帮助
    if args.help:
        _print_help()
        sys.exit(0)

    # Task input
    if args.task:
        task = " ".join(args.task)
    else:
        task = sys.stdin.read().strip()
    if not task:
        _print_help()
        sys.exit(1)

    # 打印风格
    print_style = 'pretty'
    if args.report:
        print_style = 'report'
    elif args.markdown:
        print_style = 'markdown'

    # LLM config (default: deepseek-v4-flash)
    config = LLMConfig(
        api_key=args.api_key or LLMConfig.api_key,
        base_url=args.base_url or LLMConfig.base_url,
        model=args.model or "deepseek-v4-flash",
    )

    # Budget
    budget = Budget(
        max_iterations=args.max_iter or 25,
        max_duration=args.max_duration or 600,
    )

    # System prompt
    system = DEFAULT_SYSTEM_PROMPT
    if args.system:
        with open(args.system) as f:
            system = f.read()

    # Build & run
    llm = LLM(config)
    tools = make_tools(workdir=args.workdir)
    verifier = Verifier()
    agent = Agent(llm, tools, system_prompt=system, verifier=verifier, budget=budget)

    # 根据打印风格输出
    if print_style == 'report':
        print(f"[Agent Loop v2] {config.model} | Budget: {budget.max_iterations} iters / {budget.max_duration}s")
        print(f"Task: {task[:80]}...")
        print("-" * 50)
    elif print_style == 'markdown':
        print(f"## Agent Loop v2 — {config.model}")
        print()
        print(f"**任务**: {task[:80]}...")
        print()
        print("| 配置 | 值 |")
        print("|------|-----|")
        print(f"| 模型 | {config.model} |")
        print(f"| 最大迭代 | {budget.max_iterations} |")
        print(f"| 最大时长 | {budget.max_duration}s |")
        print()
        print("---")
    else:
        print(f"🤖 Agent Loop v2 — {config.model}")
        print(f"📝 Task: {task[:120]}...")
        print(f"🔧 Tools: {', '.join(t.name for t in tools)}")
        print(f"⚙️ Budget: {budget.max_iterations} iters / {budget.max_duration}s / {budget.max_retries} retries")

    try:
        result = agent.run(task, verbose=not args.quiet, checkpoint=args.checkpoint)

        # 根据打印风格输出结果
        if print_style == 'report':
            print("-" * 50)
            print(f"Status: {agent.state.status}")
            print(f"Result:\n{result}")
        elif print_style == 'markdown':
            print("---")
            print()
            print(f"**状态**: {agent.state.status}")
            print()
            print("### 结果")
            print()
            print(result)
        else:
            print(f"\n{'='*50}")
            print(f"📋 FINAL RESULT [{agent.state.status}]")
            print(f"{'='*50}")
            print(result)

    except ValueError as e:
        helper._print_with_emoji(f"配置错误: {e}", '❌')
        sys.exit(1)
    except KeyboardInterrupt:
        helper._print_with_emoji("用户中断操作", '⚠️')
        sys.exit(1)
    except Exception as e:
        helper._print_with_emoji(f"运行错误: {type(e).__name__}: {e}", '❌')
        sys.exit(1)


if __name__ == "__main__":
    main()
