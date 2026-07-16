# 文档中心

本目录是排班打卡时间表生成器项目的文档治理入口，集中管理需求、架构、实现计划与架构决策记录（ADR）。

> **项目本质**：回溯性合规工具。根据"项目周期投入目标比例（全员工时为分母）"和"人员情况（工种/业务线，按人事变更记录动态化或默认值兜底）"，生成满足固化合规规则的每日工时记录（项目-员工-日期-工时），并按日/周/月/年粒度汇总。一次性会话模型，用完即弃不留痕。非实时排班优化，非考勤校验，不记录打卡时间点。

## 文档地图

> 状态徽章：`draft` 草案 · `active` 维护中 · `stable` 稳定 · `deprecated` 已过时

### requirements/ — 需求（做什么、为什么）

| 文档 | 说明 | 状态 |
|---|---|---|
| [product-vision.md](requirements/product-vision.md) | 产品愿景、目标用户、核心场景 | active |
| [functional-requirements.md](requirements/functional-requirements.md) | 功能性需求清单（FR-xxx 编号） | active |
| [non-functional-requirements.md](requirements/non-functional-requirements.md) | 非功能需求（合规/性能/打包等） | active |
| [use-cases/](requirements/use-cases/README.md) | 用例（6 个：初始化/单项目/多项目/重生成/自查/导出） | draft |

### architecture/ — 架构（怎么搭、模块协作）

| 文档 | 说明 | 状态 |
|---|---|---|
| [overview.md](architecture/overview.md) | 系统总览、技术栈、模块边界 | active |
| [data-model.md](architecture/data-model.md) | 数据模型（项目/人员/投入目标比例/每日工时记录等） | active |
| [generator-design.md](architecture/generator-design.md) | 工时生成算法、固化合规约束、核心策略与生命周期分布 | active |
| [ui-architecture.md](architecture/ui-architecture.md) | NiceGUI UI 架构（最简路径优先，内存态不留痕） | draft |

### plans/ — 实现计划（何时做、分几步交付）

| 文档 | 说明 | 状态 |
|---|---|---|
| [roadmap.md](plans/roadmap.md) | 里程碑路线图（M1-M5） | active |
| [implementation-status.md](plans/implementation-status.md) | 实现状态矩阵（领域概念×里程碑） | active |
| [epics/](plans/epics/README.md) | 按主题拆分的实现计划 | draft |

### decisions/ — 架构决策记录（ADR）

| 文档 | 说明 | 状态 |
|---|---|---|
| [0001-template.md](decisions/0001-template.md) | ADR 模板 | stable |
| [0002-generator-strategy.md](decisions/0002-generator-strategy.md) | 工时生成核心策略 | accepted |
| [0003-ratio-denominator-and-staff-change.md](decisions/0003-ratio-denominator-and-staff-change.md) | 比例口径与人事变更记录 | accepted |
| [0004-project-lifecycle-profile.md](decisions/0004-project-lifecycle-profile.md) | 项目生命周期时间分布 | accepted |
| [0005-global-generation-and-dictionary.md](decisions/0005-global-generation-and-dictionary.md) | 多项目全局生成与字典管理 | accepted |
| [0006-session-model-and-retention.md](decisions/0006-session-model-and-retention.md) | 会话模型与数据留存策略 | accepted |
| [0007](decisions/0007-staff-input-defaults.md) | 人事输入默认值与最简场景 | accepted |
| [0008](decisions/0008-daily-hours-full-and-split.md) | 每日工时满载与跨项目拆分 | accepted | 2026-07-17 |
| [0009](decisions/0009-generator-algorithm.md) | 生成算法定位与求解策略 | accepted | 2026-07-17 |
| [0010](decisions/0010-daily-hours-1h-granularity.md) | 跨项目拆分 1h 粒度与比例精确凑配 | accepted | 2026-07-17 |
| [0011](decisions/0011-split-continuity-semantics.md) | 拆分场景下的持续性语义 | accepted | 2026-07-17 |
| [0012](decisions/0012-tuning-ux-and-param-export.md) | 调参 UX 与参数导出复用 | accepted | 2026-07-17 |
| [0013](decisions/0013-runtime-model-and-tech-stack.md) | 运行时模型与技术栈确认 | accepted | 2026-07-17 |
| [0014](decisions/0014-holiday-api-fallback.md) | 节假日 API 降级策略 | accepted | 2026-07-17 |
| [archive/](decisions/archive/README.md) | 已被推翻的旧 ADR 归档 | — |

### domain/ — 领域知识（世界是什么样的）

| 文档 | 领域 | 说明 |
|---|---|---|
| [README.md](domain/README.md) | 索引 | 领域边界与编写约定 |
| [glossary.md](domain/glossary.md) | 术语 | 所有领域术语统一定义 |
| [work-hours.md](domain/work-hours.md) | 工时 | 满载/8h/1h拆分/节假日/年假 |
| [project.md](domain/project.md) | 项目 | 生命周期/投入比例/工种需求/关联员工 |
| [staff.md](domain/staff.md) | 人事 | 工种/业务线/在职区间/人事变更/默认值 |
| [ratio.md](domain/ratio.md) | 投入比例 | 分母/分子/周期/离散化/容差 |
| [compliance.md](domain/compliance.md) | 合规 | 硬约束/软目标/审计语义/生成器定位 |

### assets/ — 文档配图

| 文档 | 说明 | 状态 |
|---|---|---|
| [assets/](assets/README.md) | 架构图、流程图等配图存放处 | — |

---

## 文档治理规范

### 一、目录职责

| 目录 | 职责 | 禁止内容 |
|---|---|---|
| `requirements/` | 需求：做什么、为什么 | 不写实现方案、不写排期 |
| `architecture/` | 架构：怎么搭、模块协作 | 不重复需求、不写排期 |
| `plans/` | 实现计划：分几步、何时交付 | 不重复需求/架构正文 |
| `decisions/` | ADR：关键决策的取舍依据 | 不记录琐碎选择 |
| `assets/` | 文档配图 | 不放代码或产物 |

交叉引用而非复制：需求变更影响架构时，在架构文档里引用 `requirements/functional-requirements.md#FR-012`，不复述。

### 二、编号规范

- 功能需求 `FR-001`，非功能 `NFR-001`，三位起始，不复用、不重排。
- 用例 `UC-<场景名>-001`。
- ADR `NNNN-kebab-title.md`，四位序号，`0001` 起步。
- 实现 epic `<name>-plan.md`，epic 名 kebab-case；epic 内任务用 `T1/T2` 或 checkbox。
- 编号一旦发布（被其他文档引用）即冻结，废弃保留文件并标注 `Status: Deprecated`。

### 三、文档头 frontmatter

每个正式文档（requirements / architecture / plans 下的正文）顶部带 YAML frontmatter：

```markdown
---
title: 功能需求清单
status: draft | active | stable | deprecated
owner: <github handle 或留空>
last-reviewed: 2026-07-17
related: [FR-001, ADR-0003]
---
```

ADR 头部用专用字段：`status: proposed | accepted | superseded | deprecated`，并加 `deciders`、`date`。

### 四、ADR 规则

- 只追加，不删改已接受的 ADR 正文。
- 新决策推翻旧决策：新 ADR `status: accepted`，旧 ADR 改 `status: superseded by NNNN` 并移动到 `decisions/archive/`，正文保留。
- 模板字段：Context / Decision / Consequences / Alternatives。
- 单文件聚焦一个决策；跨模块大决策拆成多个 ADR。

### 五、时效与过时处理

- 不设硬性复核阈值；文档明确过时时由维护者手动在顶部标注：

  ```markdown
  > ⚠️ 已过时，替代文档：xxx.md
  ```

- 过时文档不静默删除，保留历史。
- 重大架构变更必须伴随新 ADR 或架构文档章节修订。
- 文档与代码同仓库、同 PR 提交；PR 描述含"文档影响"检查项。

### 六、命名与格式

- 文件名：小写 kebab-case，`.md`。
- 标题层级：每个文件 `#` 为文档标题，`##` 一级章节，最多到 `####`。
- 图片放 `docs/assets/`，文档内相对路径 `../assets/xxx.png`；优先 Mermaid 代码块代替位图。
- 代码示例带语言标签；外部引用给链接，不贴大段原文。
- 中文文档，术语首次出现给英文原文（如"合规约束（compliance constraints）"）。
