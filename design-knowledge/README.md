# Project Design Knowledge v1

无固定Handle的正文发现器见 [AUTOMATIC-READER.md](AUTOMATIC-READER.md)，所有自动发现能力当前为experimental。

正文段落与原子声明扩展见 [DESIGN-STATEMENTS.md](DESIGN-STATEMENTS.md)。原图例fixture和接口继续兼容。

设计知识是 Evidence 来源，不是工程对象或连接生成器。本模块不访问 AutoCAD，不改写快照，不生成 Circuit、连接、网络、路径或工程量。

## 结构与边界

- `ProjectDesignKnowledge`：来源、图例区域、图例行、符号候选、原始片段、阅读顺序候选、跨图对照、冲突、Evidence、ReviewItem、能力覆盖。
- `DesignKnowledgeSource / DesignScope`：项目、文档、快照指纹、楼栋、楼层、来源类型和版本；未知值保留未知。人工转录没有原始快照时不伪造指纹。
- `LegendRegion`：完整标题、表头、边界与网格证据。重复表头及表格线全部保留，不据此生成第二张表。
- `LegendEntry`：行ID、符号表示、原始代号、名称片段、名称候选、型号片段、备注与安装片段、源Handle及布局。`noteFragments`中的单位列原文通过布局列范围定位，不将其解释为安装要求。
- `SymbolDefinitionCandidate`：复用 ModelCore 契约；定义身份和跨图符号几何等同性仍未确认。
- `TextFragmentCandidate / ReadingOrderCandidate`：原文不变；拼接只作为有依据的阅读假设。
- `CrossDrawingLegendComparison`：同义/相容等逐项对照，不继承对方作用域。
- `DesignConflict`：保存图例和实例双方声明、快照、依赖及未决状态，同时输出 ModelCore ReviewItem。

`Resolve-DesignLegendSource`只优先返回目标项目、文档、快照均一致的本地图例证据。它不裁决实例冲突，也不将系统图说明的作用域自动扩展到另一份平面DWG。跨文档候选继续独立保存。

`ConvertTo-DesignEvidence`输出带明确 SystemScope 的 ModelCore DerivedInference，状态最多 candidate（或 conflicting）。图例含义已读到不等于平面设备身份已确认。报警、广播、电话等仍由既有 ModelCore 隔离规则约束；本模块不创建 LogicalNetwork。未研究行的系统作用域不猜测。

## 第一份真实 fixture

`tests/garage-legend.json`是经调查的样本选择清单：固定快照哈希、表格范围、51行网格、8项人工对照和I/O分片例外。这些坐标、Handle与行号只属于样本适配器，未进入通用模型契约，也不声称已经实现全图图例发现。

`GarageLegendFixture.psm1`从固定快照重新读取原始记录，验证来源、结束标记、错误数、每条横向边界，再按网格/列整理候选。符号INSERT附属属性保留自身Handle、Tag、隐藏标志、原始DXF及来源；定义中的存在不等于已确认可见。

- `23EA4 / 23E54`是同位置表头；同一 LegendRegion 保留两者。
- 51行均保留原始名称和表格布局证据。8项重点：I、I/O、SI、2I/2O、M、M1~M4、O、B。
- `23899 → 23900`保留两段原文；后者插入点跨行边界约7.801019图形单位，阅读顺序及规范名称均为候选。原始行成员仍如实记录它的位置。
- 对照来源限定为 `电气/4号楼/EC-4#-P+TBD_t8_t3.dwg`；人工转录没有原始截图Handle或快照，保持 `not_supplied`。
- 平面实例1851F和18516的隐藏名称与I代号共同保留；本地图例I=输入模块形成两项 `legend_vs_instance_semantics` 冲突。不自动选任何一方。

## 运行

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File design-knowledge/Read-GarageLegend.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File design-knowledge/tests/Test-DesignKnowledge.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File model-core/tests/Run-Regressions.ps1
```

读取入口仅向stdout输出JSON，不保存或迁移旧快照/结果。完整回归保留既有Discovery结果恢复机制。

## 当前限制

只验证当前表格的样本级区域/行整理，不处理其他布局、自动全图发现、跨图符号形状识别或全部设计说明。重复实体不删除，缺失型号不补造，隐藏属性与图面可见文字分开。知识层仅为DeviceRole、SystemIdentity、InformationRequirement、ReviewItem及后续SearchScope提供证据；本轮不实现搜索执行器或计量规则。

Layout-aware candidate reader: [scope and validation](LAYOUT-READER.md).

TEXT bbox continuity: [evidence, scope and tests](BBOX-CONTINUITY.md).

Real B1/B2 comparison: [metrics and changed-paragraph inspection](BBOX-CONTINUITY-VALIDATION.md).

Experimental section hierarchy: [contracts, scope and entry point](SECTION-HIERARCHY.md).

Experimental sheet/page scope: [real frame transforms, identity and spatial overlay](SHEET-SCOPE.md).

Experimental raw text coverage: [dispositions, short continuations and termination diagnostics](PARAGRAPH-COVERAGE.md).

Experimental [Hierarchy / Paragraph bridge](HIERARCHY-PARAGRAPH-BRIDGE.md) evaluates only existing hierarchy gaps and preserves general unresolved body dispositions.

Experimental [automatic DesignStatement bridge](DESIGN-STATEMENT-BRIDGE.md) runs the shared Atomic pipeline for accepted paragraphs and retains source/structure/clause uncertainty. It does not import formal Evidence.

Experimental [design evidence admission](EVIDENCE-ADMISSION.md) archives traceable statements separately from per-use candidate-context permissions. Existing ModelCore consumers are not automatically satisfied.

Experimental [evidence investigation consumption](EVIDENCE-INVESTIGATION.md) produces source-local search directions and missing-information hints, filters incompatible Golden tasks, and never updates InformationRequirement status.

Experimental [system scope propagation](SYSTEM-SCOPE-PROPAGATION.md) preserves ontology terms and inherited scope evidence through statements and admission, enabling same-project system-topic investigation without resolving actual networks.

Experimental [document target resolution](DOCUMENT-TARGETS.md) ranks metadata-only investigation candidates from registered inventories and SearchScopes, preserving revision ties and missing content evidence.
