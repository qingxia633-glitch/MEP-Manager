# MEP-Manager Rule Baseline v0.1

Rule Baseline 用于保存工程识图与算量中的工程事实、项目证据、批准假设和未决事项。

它不替代软件执行契约。

Gate、QuantityBuildPlan、Builder、Replay、EvidenceAuthorizationContract、
ProvenanceRecordContract 等仍属于独立的软件安全 / 执行契约。

---

## 1. engineering-rules.json

只保存已经验证、允许跨项目复用的工程规则。

项目特例、单张图纸结论、Golden 特例不得直接进入这里。

通用规则升级至少满足以下一种条件：

1. 有明确国家 / 行业规范依据，并确认：
   - discipline
   - jurisdiction
   - version
   - applicability

2. 多个独立真实项目验证一致，并由用户明确批准提升为通用规则。

AI 不得自行把 candidate 升级为 confirmed。

---

## 2. project-evidence.json

保存具体项目、图纸、系统、区域、对象的直接证据。

例如：

- DWG Handle
- parent_path
- TEXT / MTEXT
- ATTRIB
- LEADER / MLEADER
- 图例
- 系统图关系
- 直接标注
- 明确对象关联

项目证据不得自动升级为通用工程规则。

---

## 3. approved-assumptions.json

保存当前项目明确批准采用的计算政策或假设。

例如：

- 图纸缺失高度时经批准采用的高度
- 项目批准 transition allowance
- 项目批准的预留或计算口径

默认只在明确 applicability 范围内有效。

行业共识若尚未获得当前项目批准，只能用于：

provisional / estimate

不能直接进入正式 DesignNetQuantity。

---

## 4. authority-evidence.json

保存正式项目权威依据，包括：

- 设计回复
- 图纸会审纪要
- RFI
- 技术核定
- 设计变更
- 甲方 / 监理正式指令

建议记录：

- authority_id
- document_number
- issue_date
- issuer
- revision
- source_file
- source_sha256
- affected_drawings
- applicability
- statement
- supersedes
- status

正式依据冲突时保留历史，不覆盖删除旧依据。

---

## 5. unresolved-register.json

保存：

- candidate
- unresolved
- conflicting
- rejected
- deprecated
- superseded

已否定结论必须长期保留，避免 AI 重复犯已经排除过的错误。

---

# Applicability

规则不采用单一树形层级。

使用多维适用条件，例如：

- discipline
- jurisdiction
- project
- drawing
- system
- zone / region
- object selector
- effective revision

未填写的维度不代表自动全局适用，必须结合规则类型解释。

---

# Human confirmation

人工确认默认只适用于：

当前项目 + 明确范围。

除非明确批准升级，否则不能成为全局工程规则。

如果后续正式项目文件与人工确认冲突：

1. 保留原人工确认；
2. 记录冲突；
3. 正式 authority evidence 不得被旧确认静默覆盖；
4. 由用户重新批准最终项目处理。

---

# Rule lifecycle

规则和证据不删除历史。

允许状态包括：

- active
- confirmed
- candidate
- unresolved
- conflicting
- rejected
- deprecated
- superseded

被替代内容使用 supersedes / superseded_by 建立版本关系。

---

# Formal vs Estimate

正式算量模式：

没有足够工程 / 项目证据时保持 unresolved。

行业共识不能自动进入正式数量。

预估模式：

可以使用有来源的 industry-consensus assumption，
但必须显式标记 provisional / estimate，并展示使用了什么假设。

---

# Quantity explanation

长期目标是每个正式数量都能展开看到：

1. 使用了哪些工程规则；
2. 使用了哪些项目 / 图纸证据；
3. 使用了哪些 authority evidence；
4. 使用了哪些项目批准假设；
5. 哪些 unresolved / conflicting 项没有参与计算；
6. 使用的是哪些规则和证据版本。

---

# Baseline v0.1 scope

首版坚持“小而准”。

优先只整理：

- 消防电 Golden 已确认规则；
- 已确认项目证据；
- 已批准项目假设；
- 已否定 / unresolved 结论；
- 当前 Leader Evidence 相关规则。

不一次性迁移全部历史聊天。
