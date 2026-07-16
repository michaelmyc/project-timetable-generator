# 用例索引

本目录存放按场景拆分的用例文档，编号 `UC-<场景名>-NNN`。

## 编写约定

- 每个用例一个文件，命名 `uc-<场景名>-NNN.md`，场景名小写 kebab-case。
- 文件顶部带 frontmatter（见 [../../README.md](../../README.md#三文档头-frontmatter)）。
- 正文至少含：参与者、前置条件、主流程、异常流程、后置条件。
- 每个用例末尾设"设计影响"章节，记录该用例对架构/数据模型/UI 的具体影响与对应 ADR。

## 用例列表

| 编号 | 场景 | 文件 | 状态 |
|---|---|---|---|
| UC-init-001 | 首次初始化组织数据 | [uc-init-001.md](uc-init-001.md) | draft |
| UC-project-001 | 单项目补录生成 | [uc-project-001.md](uc-project-001.md) | draft |
| UC-project-002 | 多项目同期全局生成 | [uc-project-002.md](uc-project-002.md) | draft |
| UC-project-003 | 参数调整重生成 | [uc-project-003.md](uc-project-003.md) | draft |
| UC-audit-001 | 审计前合规自查 | [uc-audit-001.md](uc-audit-001.md) | draft |
| UC-export-001 | 汇总导出 | [uc-export-001.md](uc-export-001.md) | draft |
