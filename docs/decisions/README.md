# 架构决策记录（ADR）

本目录记录对架构有长期影响的关键决策及其取舍依据，不记录琐碎选择。

## 规则

- 只追加，不删改已接受的 ADR 正文。
- 新决策推翻旧决策：新 ADR `status: accepted`，旧 ADR 改 `status: superseded by NNNN` 并移动到 `archive/`，正文保留。
- 单文件聚焦一个决策；跨模块大决策拆成多个 ADR。
- 编号 `NNNN-kebab-title.md`，四位序号，`0001` 起步，不复用、不重排。

## 编写流程

1. 复制 [0001-template.md](0001-template.md) 为 `NNNN-<短标题>.md`。
2. 填写 Context / Decision / Consequences / Alternatives。
3. `status: proposed` → 评审通过后改 `accepted`。
4. 推翻时新建 ADR，旧 ADR 移入 `archive/` 并标注 `superseded by NNNN`。

## ADR 索引

| 编号 | 标题 | 状态 | 日期 |
|---|---|---|---|
| [0001](0001-template.md) | ADR 模板 | stable | 2026-07-17 |
| [0002](0002-generator-strategy.md) | 工时生成核心策略 | accepted | 2026-07-17 |
| [0003](0003-ratio-denominator-and-staff-change.md) | 比例口径与人事变更记录 | accepted | 2026-07-17 |
| [0004](0004-project-lifecycle-profile.md) | 项目生命周期时间分布 | accepted | 2026-07-17 |
| [0005](0005-global-generation-and-dictionary.md) | 多项目全局生成与字典管理 | accepted | 2026-07-17 |
| [0006](0006-session-model-and-retention.md) | 会话模型与数据留存策略 | accepted | 2026-07-17 |
| [0007](0007-staff-input-defaults.md) | 人事输入默认值与最简场景 | accepted | 2026-07-17 |
| [0008](0008-daily-hours-full-and-split.md) | 每日工时满载与跨项目拆分 | accepted | 2026-07-17 |
| [0009](0009-generator-algorithm.md) | 生成算法定位与求解策略 | accepted | 2026-07-17 |
| [0010](0010-daily-hours-1h-granularity.md) | 跨项目拆分 1h 粒度与比例精确凑配 | accepted | 2026-07-17 |
| [0011](0011-split-continuity-semantics.md) | 拆分场景下的持续性语义 | accepted | 2026-07-17 |
| [0012](0012-tuning-ux-and-param-export.md) | 调参 UX 与参数导出复用 | accepted | 2026-07-17 |
| [0013](0013-runtime-model-and-tech-stack.md) | 运行时模型与技术栈确认 | accepted | 2026-07-17 |
| [0014](0014-holiday-api-fallback.md) | 节假日 API 降级策略 | accepted | 2026-07-17 |

## 归档

已被推翻的旧 ADR 见 [archive/](archive/README.md)。
