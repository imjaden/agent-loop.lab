# Agent Loop × LLM Radar — 联动方案

> 在 agent-loop 的理论框架中加入 llm-radar 的实践数据流，形成
> **理论流程图 + 实践实现**的双栏对照。
> 目标：一眼看出抽象框架如何在真实项目中落地。

---

## 方案总览

```
三阶段实施:

Phase A: README 双栏对照     ✅ 已完成
  ├─ 流程图旁标注 llm-radar 实现
  ├─ 每个阶段列对应代码行
  └─ 验证场景表（理论场景 → 实践项目）

Phase B: 演示页面切换         ← 设计方案，待实施
  ├─ agent-loop.lab 增加"理论/实践"切换开关
  ├─ 节点点击跳转对应源码文件
  └─ 实时数据流可视化

Phase C: MCP 互通             ✅ 已完成
  ├─ agent-loop 实现 MCP Client（mcp_client.py）
  ├─ 直接调用 llm-radar 的 submit_entities
  └─ 两条 Agent Loop 数据管道交汇
```

---

## Phase A: README 双栏对照

### A.1 流程图改造

当前流程图（纯理论）：

```text
┌───────────────────────────────────────────┐
│  Agent Loop                               │
│  [Think] → [Act] → [Observe] → [Verify]  │
└───────────────────────────────────────────┘
```

改造后（双栏对照）：

```text
  理论 Agent Loop                实践 llm-radar
  ──────────────────              ──────────────────

  [Think]                        llm-radar-collector.py:872
  LLM 判断下一步                  _think() — 检查间隔 ≥6h
   │                             连续失败 ≥3 仍继续尝试
   │
   ▼
  [Act]                          llm-radar-collector.py:412
  执行工具                       fetch_all() → Selenium 抓取 6 源
   │                             extract_entities() → DeepSeek 提取
   │                             45 实体 / 次
   │
   ▼
  [Observe]                      llm-radar-collector.py:935
  结果注入上下文                  _observe() → metrics.json 记录
   │                             源健康状态更新
   │                             snapshot.json 持久化
   │
   ▼
  [Verify]                       llm-radar-collector.py:906
  输出质量检查                   _verify() — 新鲜度 < 7 天
  不合格 → 重试                 热点 ≥ 3 条 → 通过
                                  → 否则 auto-push 跳过
   │
   └──→ 循环
```

### A.2 验证场景对照表

```markdown
| 理论场景（agent-loop） | 实践项目（llm-radar） | 对应实现 |
|:---|:---|:---|
| 多源 web research | 7 新闻源 Selenium 抓取 | `fetch_all()`, SCRAPERS |
| 文档合成 | 实体合并到 snapshot.json | `merge_entities()`, changelog |
| 数据抓取与分析 | 结构化文章提取 → LLM 提取实体 | `_selenium_extract()`, `extract_entities()` |
| 工具即插即用 | MCP Server 工具注册 | `mcp-radar-mcp-server.py` TOOL_REGISTRY |
| 质量门禁 | 新鲜度 + 热点数量校验 | `_verify()` |
| 状态持久化 | snapshot.json + metrics.json | `_save_snapshot()`, `_observe()` |
| 错误恢复 | Selenium 重试 + 源降级 | `_selenium_extract()` 2 次重试 |
```
```

---


## Phase B: 演示页面切换

### B.1 需求

agent-loop.lab.jaden.tech 当前展示纯理论的 Agent Loop 流程图。
增加"理论/实践"切换开关，让访问者可以：

```text
默认视图: 纯理论流程图

切换后:   理论 → 实践
          每个节点下方显示 llm-radar 对应的代码片段
          点击节点跳转到 GitHub 对应源码行
```

### B.2 架构

```text
index.html（现有）
  │
  ├─ 默认: 显示纯理论流程图（不变）
  │
  └─ toggle switch → "Show Practice"
       │
       ├─ 每个节点新增浮层标注
       │   Think    → _think():872 (llm-radar-collector.py)
       │   Act      → fetch_all():412
       │   Observe  → _observe():935
       │   Verify   → _verify():906
       │
       ├─ 点击节点 → 打开 GitHub 对应源码行
       │
       └─ 底部显示实时数据仪表盘 iframe
           src="https://llm-radar.lab.jaden.tech"
```

### B.3 数据来源

```text
理论模式数据: 硬编码在 index.html 中（现有）
实践模式数据:
  - 代码行引用: 硬编码（不会频繁变化）
  - GitHub 链接: https://github.com/imjaden/llm-radar.lab/blob/main/llm-radar-collector.py#L872
  - 仪表盘 iframe: https://llm-radar.lab.jaden.tech
```

### B.4 实现

只需要修改 `agent-loop.lab/index.html`：

```javascript
// 新增切换开关
const toggle = document.getElementById('practice-toggle');
toggle.addEventListener('change', () => {
  document.body.classList.toggle('show-practice');
});

// 实践模式标注数据
const practiceData = {
  think:   { file: 'llm-radar-collector.py', line: 872, code: '_think() - check interval >= 6h' },
  act:     { file: 'llm-radar-collector.py', line: 412, code: 'fetch_all() - Selenium 6 sources' },
  observe: { file: 'llm-radar-collector.py', line: 935, code: '_observe() - metrics.json' },
  verify:  { file: 'llm-radar-collector.py', line: 906, code: '_verify() - freshness < 7d' },
};
```

无需后端、无需构建步骤、纯前端改动。

### B.5 与 Phase A / C 的关系

```text
Phase A（README）: 文字描述，告诉访问者有这个对应关系
Phase B（演示页面）: 可视化展示，让访问者交互式体验
Phase C（MCP 互通）: 技术实现，让两个项目真正联通

三者互补，互不冲突。
```


## Phase C: MCP 互通

### C.1 架构

```text
agent-loop (MCP Client)                llm-radar (MCP Server)
─────────────────────                  ──────────────────────
Agent Loop run()                       llm-radar-mcp-server.py
  │                                       │
  ├─ tools/list ──────────→               ├─ health_check
  │                       ← 工具列表      ├─ submit_entities
  │                                       │
  ├─ tools/call:health                    │
  │                       ← {status: ok}  │
  │                                       │
  └─ tools/call:submit_entities ──→       │
                           ← { merged }   │
                                          │
  Agent Loop 结果 ← ───────────── snapshot.json
```

### C.2 agent-loop 新增 MCP Client

```python
# mcp_client.py — 新增文件
import subprocess, json

class MCPClient:
    """通过 stdio JSON-RPC 2.0 连接 MCP Server"""

    def __init__(self, server_config):
        self.proc = subprocess.Popen(
            [server_config['command']] + server_config['args'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE
        )
        # 发送 initialize 请求
        self._call('initialize', {'protocolVersion': '2025-03-26'})

    def list_tools(self):
        return self._call('tools/list')

    def call_tool(self, name, arguments):
        return self._call('tools/call', {'name': name, 'arguments': arguments})

    def _call(self, method, params=None):
        req = {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}}
        self.proc.stdin.write(json.dumps(req).encode() + b'\n')
        self.proc.stdin.flush()
        resp = json.loads(self.proc.stdout.readline())
        return resp.get('result')
```

### C.3 config.json 扩展

```json
{
  "model": "deepseek-v4-flash",
  "api_key": "sk-...",
  "mcp_servers": {
    "llm-radar": {
      "command": "python3",
      "args": ["/path/to/llm-radar-mcp-server.py"],
      "env": {"LLM_RADAR_MCP_KEY": "llm-radar-mcp-2026"}
    }
  }
}
```

### C.4 使用场景

```python
# agent-loop 的 tool 直接调用 llm-radar 的 MCP 工具
@ToolBase.register
def submit_to_llm_radar(data: dict) -> str:
    """将 5 维度实体数据提交到 LLM-Radar 仪表盘"""
    client = MCPClient(config['mcp_servers']['llm-radar'])
    result = client.call_tool('submit_entities', {
        'api_key': 'llm-radar-mcp-2026',
        **data
    })
    return f"Submitted: {result.get('new', 0)} new, {result.get('updated', 0)} updated"
```

---

## 实施路径

```text
Day 1:  更新 README（双栏流程图 + 验证场景表）        ← 1 小时
Day 2:  实现 mcp_client.py（MCP Client 基类）         ← 2 小时
Day 3:  config.json 扩展 + 在 agent-loop 中集成调用   ← 2 小时
Day 4:  测试（agent-loop → mcp_client → llm-radar）   ← 1 小时
```

---

## 效果预览

```text
agent-loop README 更新后，访问者会看到:

1. 左侧是干净的抽象流程图
2. 右侧是 llm-radar-collector.py:872 这样的代码行引用
3. 验证场景表里每个条目都是"xx项目 → xx代码行"
4. 知道这个理论框架在真实生产系统中是怎么跑的

MCP 互通后:

1. agent-loop 可以调用 llm-radar 的工具
2. llm-radar 的数据可以被 agent-loop 处理
3. 形成: agent-loop → MCP → llm-radar → snapshot → GitHub Pages
   的完整数据管道
```


*版本: 1.1 | 更新: 2026-07-01*
