# 正文知识最小模型

本层消费已有快照；不访问AutoCAD，不修改原图，不确定实际设备整定或计价规则。

## 原文与候选语义

`SourceRegion → DesignStatementGroup → DesignStatementCandidate[]`

- `SourceRegion`保留图签INSERT、标题/图号ATTRIB、上下文原文及段落边界依据。图签归属不等于已展开图框几何。
- `DesignStatementGroup`是原始段落。完整保存TEXT、Handle、位置、快照及阅读顺序候选。`normalizedStatementCandidate`只是一份派生连接文本。
- `DesignStatementCandidate`是原子声明，不默认一段就是一条规则。声明及条件、备选项、目的、例外、引用均使用`TextSpanReference`指回原片段。
- 字符位置为零起算UTF-16代码单元，与.NET字符串索引一致；跨TEXT表达保留多个span。重复子串必须提供唯一上下文或明确片段偏移，不自动取第一个。
- `ApplicabilityCondition`的定性长度条件保留原文，`thresholdStatus=unresolved`；任意观察长度均不能由此自动满足条件。
- `AlternativeClause`表达备选，不是合取或例外，不选择具体项。
- `PurposeClause`分别保存主体、连接词和目的；C的`statementType=purpose_statement`，不是普通备注。
- `ExceptionClause / CrossDrawingReference`提供最小通用契约。真实本段两者均为空，不虚构例外或引用目标。

## 第二份真实fixture

`tests/design-statement.json`是已审阅样本清单，不是自动正文解析规则。使用与车库图例相同的固定快照SHA-256。`DesignStatementFixture.psm1`读取三个TEXT并校验原文、布局和指纹，按审阅的子串声明建立精确source spans；并未实现通用自然语言条件抽取。

原始段落：`23428 → 23401 → 23402`，编号`4.12.1`。

| 声明 | 条件/关系 | 输出 |
|---|---|---|
| A | 非消防负荷、较短的线路 | 过载长延时和短路瞬时脱扣要求候选 |
| B | 非消防负荷、较长的线路 | 保护要求、瞬时/短延时备选及整定要求候选 |
| C | 非消防负荷上下文 | 短延时脱扣器 → 用以 → 保证上下级选择性要求 |

`discipline=electrical`、`subjectScope=non_fire_load`、楼栋/楼层未决、`documentApplicability=local_document_statement`。power系统类别仅承载声明候选，未选择任何具体系统网络。文件名不构成范围继承依据。

上方`23424 / 4.11 低压配电线路保护`与`4.12.1`形成`StructuralAnomalyCandidate`及待定ReviewItem，不更改编号，不阻塞解析。记录的是“上级标题候选不一致”，不是已确认标题从属或排版错误。

## Evidence接口与兼容性

原LegendEntry接口保持可用，`New-ProjectDesignKnowledge`末尾增加可选的`StatementGroups / Statements / StructuralAnomalies`参数。

`ConvertTo-DesignEvidence`现在接受正文候选，返回ModelCore `DerivedInference / candidate`，携带声明、来源和SystemScope。它可以作为InformationRequirement、属性候选、ReviewItem、SearchScope或后续规则匹配的依据；本阶段不增加实际设备属性赋值器或搜索执行器。不得将candidate提升为实际条件已满足。

`New-DesignConflict`支持正文与局部事实的对照：必须显式提交局部原文、快照、Handle和矛盾依据，不能只靠两个字符串不同生成冲突。两方来源保留，状态未决，不设说明/平面全局优先级。当前真实段落没有新增局部工程矛盾；冲突接口使用标明synthetic的受控样本测试。

## 运行与边界

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File design-knowledge/Read-DesignStatement.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File design-knowledge/tests/Test-DesignStatements.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File model-core/tests/Run-Regressions.ps1
```

读取入口只输出stdout JSON，不写新结果文件。完整回归包含新套件，仍恢复Discovery旧结果原始字节。本阶段没有Circuit、实际连接、整定值、计量结果或计价规则。
