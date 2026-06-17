#!/usr/bin/env python3
"""
Agent Loop Engineering v1.3 — 最小化 Agent 循环框架

基于 Loop Engineering 方法论：Think → Act → Observe → Verify 闭环执行。
默认 LLM: deepseek-v4-flash（OpenAI 兼容）
"""

import json, os, subprocess, sys, time, hashlib
from dataclasses import dataclass, field, asdict
from typing import Callable, Optional
from datetime import datetime, timezone
from pathlib import Path

# ──────────────────────────────────────────────
# 0. 辅助工具
# ──────────────────────────────────────────────
def _load_config(path: str = "config.json") -> dict:
    """读取配置文件，不存在返回默认配置"""
    default = {
        "tavily_api_key": "",
        "model": "deepseek-v4-flash",
        "api_key": "",
        "base_url": "https://api.deepseek.com/v1",
        "prompt": "prompts/default.md",
        "workdir": ".",
        "checkpoint": "",
        "max_iter": 10,
        "max_duration": 600,
        "verbose": True,
    }
    if os.path.exists(path):
        try:
            with open(path) as f:
                loaded = json.load(f)
                return {**default, **loaded}
        except json.JSONDecodeError:
            print(f"⚠️ 配置文件 {path} 格式错误，使用默认配置")
            return default
    return default

# ──────────────────────────────────────────────
# 1. LLM 接口（OpenAI 兼容，默认 deepseek-v4-flash）
# ──────────────────────────────────────────────
@dataclass
class LLMConfig:
    api_key: str = ""
    base_url: str = "https://api.deepseek.com/v1"
    model: str = "deepseek-v4-flash"
    max_tokens: int = 16384

class LLM:
    """OpenAI 兼容 LLM 调用层"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = None

    def _ensure(self):
        if self._client is None:
            if not self.config.api_key:
                raise ValueError("缺少 api_key，请在 config.json 中配置")
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
    max_iterations: int = 10
    max_tokens: int = 15000       # 估算上限
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
                    print(f"⏰ Budget exceeded at iteration {i}")
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
                        print(f"✅ Verified ({len(answer)} chars)")
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
                            print(f"❌ Max retries ({self.budget.max_retries}) exceeded")
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
                        print(f"🔄 Verification failed, retrying ({self._retry_count}/{self.budget.max_retries})")
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
                    if verbose:
                        print(f"⚠️ Unknown tool: {tc['name']}")
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
def make_tools(workdir: str = ".", config: dict = None) -> list[ToolBase]:
    cfg = config or {}

    def web_search(query: str, limit: int = 5) -> str:
        """Search the web for information."""
        tavily_key = cfg.get("tavily_api_key", "") or os.environ.get("TAVILY_API_KEY", "")
        if not tavily_key:
            return "[web_search] 错误: 缺少 tavily_api_key，请在 config.json 中配置"
        payload = json.dumps({"api_key": tavily_key, "query": query, "limit": limit}).encode()
        r = subprocess.run(
            ["curl", "-s", "-X", "POST",
             "-H", "Content-Type: application/json",
             "-d", payload, "https://api.tavily.com/search"],
            capture_output=True, text=True, timeout=15
        )
        return r.stdout[:6000] if r.stdout.strip() else f"[web_search] 无结果: {query}"

    def web_extract(url: str) -> str:
        """Extract content from a URL."""
        import uuid
        tmp_file = f"/tmp/_agent_page_{uuid.uuid4().hex[:8]}.html"
        r = subprocess.run(
            ["curl", "-sL", url, "-o", tmp_file, "-w", "%{http_code}"],
            capture_output=True, text=True, timeout=30
        )
        if r.stdout.strip() == "200":
            with open(tmp_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()[:8000]
            os.remove(tmp_file)
            return f"[HTTP 200 from {url}]\n\n{content}"
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
        import uuid
        tmp_file = f"/tmp/_agent_exec_{uuid.uuid4().hex[:8]}.py"
        with open(tmp_file, "w") as f:
            f.write(code)
        r = subprocess.run(
            ["python3", tmp_file],
            capture_output=True, text=True, timeout=30
        )
        os.remove(tmp_file)
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
# 8. 入口
# ──────────────────────────────────────────────
def _print_help():
    """【打印帮助信息】"""
    print("\n" + "=" * 60)
    print("📖 Agent Loop v1.3 使用说明")
    print("=" * 60)

    print("\n【功能概述】")
    print("  基于 Loop Engineering 方法论的 AI Agent 循环框架")
    print("  Think → Act → Observe → Verify 闭环执行任务")

    print("\n【配置文件】")
    print("  config.json - 所有配置项（api_key, model, 预算等）")

    print("\n【使用示例】")
    print("  python3 agent-loop.py '搜索长亭科技最新动态，整理为 markdown 文档'")
    print("  cat task.txt | python3 agent-loop.py")

    print("\n" + "=" * 60)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Agent Loop Engineering v1.3", add_help=False)
    parser.add_argument("task", nargs="*", help="任务描述")
    parser.add_argument("--help", "-h", action="store_true", help="显示帮助信息")
    args = parser.parse_args()

    if args.help:
        _print_help()
        sys.exit(0)

    task = " ".join(args.task) if args.task else sys.stdin.read().strip()
    if not task:
        _print_help()
        sys.exit(1)

    cfg = _load_config()

    config = LLMConfig(
        api_key=cfg["api_key"],
        base_url=cfg["base_url"],
        model=cfg["model"],
    )

    budget = Budget(
        max_iterations=cfg["max_iter"],
        max_duration=cfg["max_duration"],
    )

    prompt_file = cfg["prompt"]
    if os.path.exists(prompt_file):
        system = open(prompt_file).read()
    else:
        system = ""
        if cfg["verbose"]:
            print(f"⚠️ Prompt 文件不存在: {prompt_file}")

    llm = LLM(config)
    tools = make_tools(workdir=cfg["workdir"], config=cfg)
    verifier = Verifier()
    agent = Agent(llm, tools, system_prompt=system, verifier=verifier, budget=budget)

    print(f"[Agent Loop v1.3] {config.model} | Budget: {budget.max_iterations} iters / {budget.max_duration}s")
    print(f"Task: {task[:80]}...")
    print("-" * 50)

    try:
        result = agent.run(task, verbose=cfg["verbose"], checkpoint=cfg["checkpoint"])
        print("-" * 50)
        print(f"Status: {agent.state.status}")
        print(f"Result:\n{result}")

    except ValueError as e:
        print(f"[Error] 配置错误: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("[Warning] 用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"[Error] 运行错误: {type(e).__name__}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
