# Epic 索引

本目录存放按主题拆分的实现计划，每文件一个 epic。

## 编写约定

- 文件命名 `<name>-plan.md`，name 用 kebab-case。
- 顶部带 frontmatter（见 [../../README.md](../../README.md#三文档头-frontmatter)）。
- 正文结构：目标、TDD 步骤（Red-Green-Refactor）、验收测试、集成点、branch。
- 覆盖的 `FR-NNN`、关联的 `ADR-NNNN` 以链接引用，不复述。

## Epic 列表

| Epic | 文件 | 状态 |
|---|---|---|
| M1 MVP（10 个子 Epic + 8 个集成点） | [m1-mvp-plan.md](m1-mvp-plan.md) | active |

## M1 MVP 子 Epic 概览

| Epic | branch | 依赖 | 集成到 |
|---|---|---|---|
| 1 Domain Models | feature/m1-domain-models | 无 | integration/m1-models |
| 2 Holiday API | feature/m1-holiday-api | Epic 1 | integration/m1-models-holiday |
| 3 Generator Core | feature/m1-generator-core | Epic 1+2 | integration/m1-gen-holiday |
| 4 Generator Multi | feature/m1-generator-multi | Epic 3 | integration/m1-gen-multi |
| 5 CSV Export | feature/m1-csv-export | Epic 1 | integration/m1-gen-csv |
| 6 Param IO | feature/m1-param-io | Epic 1 | integration/m1-core-pipeline |
| 7 UI Session | feature/m1-ui-session | Epic 1 | integration/m1-ui-assembly |
| 8 UI Input | feature/m1-ui-input | Epic 7 | integration/m1-ui-assembly |
| 9 UI Generate | feature/m1-ui-generate | Epic 8+3/4 | integration/m1-ui-assembly |
| 10 UI Export | feature/m1-ui-export | Epic 9+5/6 | integration/m1-ui-assembly |
| E2E | integration/m1-full-e2e | 全部 | 合回 main |

## 集成里程碑

| 集成点 | 里程碑意义 |
|---|---|
| integration/m1-gen-csv | **垂直切片：生成→CSV 端到端可验证** |
| integration/m1-core-pipeline | **核心管线全通（无 UI）** |
| integration/m1-full-e2e | **M1 完整端到端，合回 main** |
