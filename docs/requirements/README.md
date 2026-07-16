# 需求文档索引

本目录记录"做什么、为什么"，不含实现方案与排期。

| 文档 | 说明 | 状态 |
|---|---|---|
| [product-vision.md](product-vision.md) | 产品愿景、目标用户、核心场景 | active |
| [functional-requirements.md](functional-requirements.md) | 功能性需求清单（FR-xxx 编号） | active |
| [non-functional-requirements.md](non-functional-requirements.md) | 非功能需求（合规/性能/打包等） | active |
| [use-cases/](use-cases/README.md) | 用例（按场景拆分） | draft |

## 编写约定

- 功能需求编号 `FR-001` 起始，非功能 `NFR-001`，用例 `UC-<场景>-001`。
- 编号一经引用即冻结；废弃保留并标注 `Status: Deprecated`。
- 每个正式文档顶部带 frontmatter（见 [docs/README.md](../README.md#三文档头-frontmatter)）。
