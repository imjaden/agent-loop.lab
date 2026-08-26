---
name: features-template
description: Flat line-level feature inventory template for project root
version: 1.0
author: IRIS
tags: [template, governance, project]
quality:
  coverage: 0.55
  depth: 0.40
  maintainability: 0.85
  cross_profile: 0.90
---

# agent-loop — Features

<!--
⚠️  AI 指令: 如需更新此文件，请直接编辑本 features.md，
   不要创建新文件（如 documents/features-v1.0.md）。
   此文件遵循风格 B（无版本号、项目根、持续更新）。
-->

> 产出文档的元信息必须遵循 `skills-governance/document-frontmatter.md` 规范。

> 项目功能框架。由 dev profile 维护，新增需求以 flat line-level 格式追加。
>
> 文件命名: 固定为 `features.md`，小写，无版本号。
>
> 适用: 风格 B 文件（无版本号，持续更新），存放在项目根目录。

## 功能域划分建议

- **按模块划分**: 适用于有明确定义子系统/模块的项目，如 `Session管理`、`Skills治理`、`review管线`
- **按工作流划分**: 适用于流程驱动的项目，如 `开发 → 构建 → 部署`
- **按主题划分**: 适用于工具类项目，如 `CLI工具`、`Web工具`、`脚本工具`

选择一个划分维度并在本项目内保持一致。

> 功能域命名建议参考 governance handbook §1-§11 章节主题，如 `文档规范`（§1）、`Commit 规范`（§5）、`审计规范`（§6）。

## {功能域 1}

1. {功能描述} {状态标记} — {关联文档/产出}
2. {功能描述} {状态标记} — {关联文档/产出}

## {功能域 2}

1. {功能描述} {状态标记} — {关联文档/产出}

## 待定/规划

1. {待定功能} 🚧
2. {待定功能} 🚧

## 关联文档引用格式

`— {关联文档/产出}` 部分支持以下格式：

| 类型 | 格式 | 示例 |
|------|------|------|
| review 报告 | `documents/reviews/{topic}-review-v{X}.{Y}-{date}.md` | `documents/reviews/handbook-v1.1-audit-v1.0-20260715.md` |
| 设计文档 | `documents/{topic}-design-v{X}.{Y}-{date}.md` | — |
| 工具脚本 | `{path/to/script.py}` | `skills-governance/quality-check.py` |
| 无产出 | — | 留空 |

## 状态标记说明

| 标记 | 含义 | 使用场景 |
|------|------|---------|
| ✅ | 已完成/活跃 | 功能已实现且稳定运行 |
| 🟡 | 稳定运行中 | 功能可用但需持续关注（如依赖外部服务、已知限制） |
| 🚧 | 规划/待定 | 已明确需求但尚未实现 |
| 🔴 | 已废弃 | 不再维护，保留用于历史追溯 |

## 功能序号与代码注释关联

功能条目编号应与代码注释序号保持一致，便于从功能定位到实现代码。

代码中按 `【N】` 标注功能序号：

```python
# 【1】协议适配
# 【2】数据加载
# 【3】页面渲染
```

features.md 条目一一对应：

```
1. 协议适配 ✅ — src/adapters.py
2. 数据加载 ✅ — src/loader.py
3. 页面渲染 🚧
```

| 检查项 | 规则 |
|:-------|:------|
| 序号连续 | 代码注释 `【N】` 从 1 开始连续递增 |
| 一一对应 | `【N】` 数与 features.md 编号一一对应 |
| 检查命令 | `hm check cli --features <path>` |
