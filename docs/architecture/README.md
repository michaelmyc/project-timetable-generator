# 架构文档索引

本目录记录"怎么搭、模块如何协作"，不重复需求、不写排期。

| 文档 | 说明 | 状态 |
|---|---|---|
| [overview.md](overview.md) | 系统总览、技术栈、模块边界 | active |
| [data-model.md](data-model.md) | 数据模型（项目/人员/投入目标/每日工时记录等） | active |
| [generator-design.md](generator-design.md) | 工时生成算法与固化合规约束设计 | active |
| [ui-architecture.md](ui-architecture.md) | NiceGUI UI 架构与状态流 | draft |

## 编写约定

- 架构图优先用 Mermaid 代码块，位图存 [../assets/](../assets/README.md)。
- 引用需求时用 `../requirements/functional-requirements.md#FR-NNN`，不复述。
- 模块边界变更必须伴随新 ADR（见 [../decisions/](../decisions/README.md)）。
