"""
MCP Client — 通过 stdio JSON-RPC 2.0 连接 MCP Server

用法:
    client = MCPClient({"command": "python3", "args": ["path/to/server.py"]})
    tools = client.list_tools()
    result = client.call_tool("tool_name", {"arg1": "val1"})
"""

import json
import subprocess
import sys
import os
from pathlib import Path
from typing import Optional


class MCPClientError(Exception):
    """MCP 协议调用异常"""


class MCPClient:
    """MCP stdio 客户端

    通过 subprocess 启动 MCP Server，通过 stdin/stdout 进行 JSON-RPC 2.0 通信。

    用法:
        config = {
            "command": "python3",
            "args": ["/path/to/mcp-server.py"],
            "env": {"API_KEY": "xxx"}  # optional
        }
        client = MCPClient(config)
        tools = client.list_tools()
        result = client.call_tool("submit", data={...})
        client.close()
    """

    def __init__(self, server_config: dict):
        self.proc: Optional[subprocess.Popen] = None
        self._req_id = 0
        self._connect(server_config)

    def _connect(self, config: dict):
        """启动 MCP Server 子进程并完成初始化握手"""
        env = os.environ.copy()
        if config.get("env"):
            env.update(config["env"])

        self.proc = subprocess.Popen(
            [config["command"]] + config.get("args", []),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
        )

        # Step 1: initialize
        result = self._call("initialize", {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "agent-loop-mcp", "version": "1.0"},
        })
        self.server_info = result
        self._req_id = 0

    def list_tools(self) -> list:
        """获取 MCP Server 提供的工具列表"""
        result = self._call("tools/list")
        return result.get("tools", [])

    def call_tool(self, name: str, arguments: dict = None) -> dict:
        """调用 MCP 工具"""
        params = {"name": name}
        if arguments:
            params["arguments"] = arguments
        return self._call("tools/call", params)

    def _call(self, method: str, params: dict = None) -> dict:
        """发送 JSON-RPC 2.0 请求并等待响应"""
        self._req_id += 1
        req = {
            "jsonrpc": "2.0",
            "id": self._req_id,
            "method": method,
        }
        if params:
            req["params"] = params

        req_str = json.dumps(req, ensure_ascii=False)
        self.proc.stdin.write(req_str + "\n")
        self.proc.stdin.flush()

        resp_line = self.proc.stdout.readline()
        if not resp_line:
            raise MCPClientError("MCP Server 无响应（进程可能已退出）")

        resp = json.loads(resp_line)

        if "error" in resp:
            err = resp["error"]
            raise MCPClientError(
                f"MCP 错误 [code={err.get('code')}]: {err.get('message', 'unknown')}"
            )

        return resp.get("result", {})

    def close(self):
        """关闭 MCP Server 子进程"""
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ===== 测试 =====
if __name__ == "__main__":
    # 默认连接 llm-radar MCP Server
    server_path = os.path.expanduser(
        "~/CodeSpace/llm-radar.jaden.tech/llm-radar-mcp-server.py"
    )

    config = {
        "command": "python3",
        "args": [server_path],
        "env": {"LLM_RADAR_MCP_KEY": "llm-radar-mcp-2026"},
    }

    with MCPClient(config) as client:
        # 1. 列出工具
        tools = client.list_tools()
        print(f"Tools ({len(tools)}):")
        for t in tools:
            print(f"  - {t['name']}: {t.get('description', '')[:60]}")

        # 2. 健康检查
        health = client.call_tool("health_check", {"api_key": "llm-radar-mcp-2026"})
        print(f"\nHealth: {health.get('status')} ({health.get('total_entities')} entities)")

        # 3. 提交测试数据
        test_data = {
            "api_key": "llm-radar-mcp-2026",
            "hotspots": [{
                "id": "test-mcp-client",
                "title": "MCP Client integration test",
                "summary": "Testing agent-loop MCP Client -> llm-radar MCP Server",
                "date": "2026-07-01",
                "source": "agent-loop",
                "url": "",
                "confidence": "high",
            }]
        }
        submit = client.call_tool("submit_entities", test_data)
        status = submit.get("status", "?")
        detail = submit.get("detail", {})
        print(f"\nSubmit: {status} (new={detail.get('new',0)}, updated={detail.get('updated',0)})")
        print("All MCP Client tests passed")
