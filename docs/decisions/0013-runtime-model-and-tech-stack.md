---
title: ADR-0013 运行时模型与技术栈确认
status: accepted
deciders: []
date: 2026-07-17
related: [FR-011, FR-018, NFR-010, NFR-020, NFR-030, ADR-0006 D3, ADR-0009 D5]
---

# ADR-0013 运行时模型与技术栈确认

> 正式确认 NiceGUI + Python 3.14 + PyInstaller 技术栈；明确生成必须异步不卡 UI（具体模型原型期定）、节假日缓存落盘到平台规范用户目录、支持多实例并行。

## 状态

accepted

## 上下文（Context）

- NiceGUI + Python 3.14 + PyInstaller 从 demo 模板继承，12 个 ADR 无一正式决策技术栈。
- 技术栈对产品合适（表单密集、桌面单机、Python 生态适配 CSV/Excel 与贪心算法、单人全包无并发用户），但运行时交互点未澄清。
- 问题 1：NiceGUI 是浏览器 GUI（FastAPI + WebSocket），生成算法（贪心 + N 次重试，多项目可能几十秒）同步执行会阻塞事件循环，UI 卡死、进度无法推送（ADR-0009 D5 要求进度反馈）。
- 问题 2：节假日缓存落盘位置未定（ADR-0006 D3 唯一允许落盘数据）；macOS 签名下 bundle 内只读，必须用用户目录。
- 问题 3：多实例并行是否支持未正式确认。
- 用户决策：异步模型原型对比后定；支持多实例。

## 决策（Decision）

### D1 技术栈确认

- **NiceGUI** + **Python 3.14** + **PyInstaller**（正式化继承的技术栈，不更换）。
- 理由：表单密集 UI ✅、桌面单机离线 ✅、Python 生态（CSV/Excel/贪心）✅、单人全包无并发 ✅。
- 打包遵循 AGENTS.md：uv 管理依赖、PyInstaller 隔离构建、三平台 CI 矩阵。

### D2 生成必须异步，不卡 UI（具体模型原型期定）

- 生成算法**必须在后台执行**，不阻塞 NiceGUI 事件循环，UI 保持响应。
- 进度反馈（当前轮次/总轮次、当前阶段，ADR-0009 D5）必须能实时推送到前端。
- 具体异步模型（asyncio 任务 + timer 轮询 vs 独立线程 + 队列）**原型期对比后定**，当前只约束"必须异步不卡 UI"。
- 候选方案：
  - asyncio 后台任务 + `ui.timer` 轮询进度变量
  - 独立线程 + 线程安全队列推送进度

### D3 节假日缓存落盘到平台规范用户目录

- 节假日 API 缓存（ADR-0006 D3 唯一允许落盘数据）写到平台规范用户目录：
  - macOS：`~/Library/Caches/<app>/holidays/`
  - Windows：`%LOCALAPPDATA%\<app>\holidays\`
  - Linux：`~/.cache/<app>/holidays/`（遵循 XDG）
- 不写 app bundle 内（macOS 签名下只读）或 exe 同目录（跨平台不一致）。
- 缓存按年度组织（ADR-0002 D4），用户可手动清理（后续可选 UI 入口）。

### D4 支持多实例并行

- 支持多实例并行运行（`find_open_port` 扫描 8000-8999，AGENTS.md 已实现）。
- 各实例独立内存态，无共享状态，符合 ADR-0006 一次性会话不留痕。
- 用户可开多个实例做不同批次，互不影响。

## 后果（Consequences）

- 正面：
  - 技术栈正式化，消除"继承未决策"的模糊。
  - 异步约束明确，实现期不会因 UI 卡死返工。
  - 缓存落盘位置跨平台规范，避免签名/权限坑。
  - 多实例支持符合用完即弃 + 多批次场景。
- 负面：
  - 异步模型未定，原型期需对比验证，有少量返工风险。
  - 多实例无共享意味着用户不能跨实例复用数据（符合设计，但需用户感知）。
- 后续需要做的事：
  - 原型期对比 asyncio vs 线程，定异步模型。
  - 实现缓存落盘路径逻辑（平台判断 + 目录创建）。
  - 验证多实例端口扫描在打包后仍正常。

## 备选方案（Alternatives）

- 换技术栈（如 Electron/Tauri）：被否，NiceGUI + Python 对产品合适，无更换理由。
- 同步生成 + 等待：被否，UI 卡死、进度无法反馈。
- 缓存落盘到 exe 同目录：被否，跨平台不一致、macOS 签名只读。
- 单实例运行：被否，用户明确支持多实例。

## 相关

- 需求：`FR-011`、`FR-018`、`NFR-010`、`NFR-020`、`NFR-030`
- 架构文档：`../architecture/overview.md`、`../architecture/ui-architecture.md`
- 上游：ADR-0006 D3（缓存落盘例外）、ADR-0009 D5（进度反馈）
- 基础：AGENTS.md（PyInstaller/uv/CI 矩阵）
