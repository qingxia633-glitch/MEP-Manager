# Rule Baseline v0.1 Record Contract

本文件定义 Rule Baseline v0.1 的记录级公共约束。

它是工程知识治理契约，不是 QuantityBuildPlan / Builder 等软件执行契约。

---

# 一、公共字段

正式记录至少应包含：

- `id`
- `status`
- `statement`
- `applicability`
- `sources`
- `provenance_gaps`
- `created_from`
- `supersedes`
- `superseded_by`
- `notes`

## provenance_gaps

每条正式记录必须包含 `provenance_gaps`，类型必须是数组；每个元素必须是非空且非纯空白的字符串。

- `[]`：当前 portable baseline 未发现已知 provenance 缺口，不代表独立认证已完成。
- 非空数组：逐项记录当前缺失的来源链信息，例如私有来源载荷未随 checkout 提供、历史人工确认原始消息或身份复核缺失。
- provenance gap ≠ engineering unresolved。目标绑定、全局回路身份、材料选型等工程未决问题由 `status` / statement / notes 表达，除非确实缺失来源链信息，否则不重复放入此字段。
- `status` 与 provenance completeness 是两个不同维度。AI 不得因数组非空自动推翻、升级或降级已批准 / 已支持状态；也不得忽略已记录的 gap 而声称来源链完整。
- 不使用数值 confidence score，不增加自动状态转换逻辑。

校验器对字段缺失、非数组或非字符串 / 空白元素报错；空数组和非空字符串数组均合法。校验不改变任何记录的工程状态，也不替代现有 source / status / supersede 校验。

## id

必须：

- 非空；
- 在整个 Rule Baseline v0.1 中唯一；
- 已引用的历史 ID 不得重新用于另一条规则或证据。

建议前缀：

- `ER-`：engineering rule
- `PE-`：project evidence
- `PA-`：project-approved assumption
- `AE-`：authority evidence
- `UR-`：unresolved / rejected / conflicting record

---

# 二、Applicability

Applicability 使用多维适用条件，不建立一棵强制层级树。

允许的主要维度：

- `discipline`
- `jurisdiction`
- `project`
- `drawing`
- `system`
- `zone`
- `object_selector`
- `effective_revision`

未填写某个维度不代表自动全局适用。

规则的真实适用范围必须由记录类型、来源和已确认条件共同决定。

项目特定证据不能因为某个 applicability 字段为空而自动升级为全局规则。

---

# 三、状态

## Engineering Rules

允许：

- `candidate`
- `confirmed`
- `active`
- `deprecated`
- `superseded`
- `rejected`

AI 不得自动把 `candidate` 升级成 `confirmed`。

## Project Evidence

允许：

- `supported`
- `partial`
- `unresolved`
- `conflicting`
- `rejected`
- `superseded`

## Approved Assumptions

允许：

- `approved`
- `deprecated`
- `superseded`
- `rejected`

## Authority Evidence

允许：

- `active`
- `superseded`
- `rejected`

## Unresolved Register

允许：

- `candidate`
- `unresolved`
- `conflicting`
- `rejected`
- `deprecated`
- `superseded`

---

# 四、来源要求

`confirmed`、`supported`、`approved`、`active`、`rejected`
等会影响工程判断的状态必须具有可追溯来源。

不能使用：

- AI 常识；
- “通常都是这样”；
- 无出处的行业印象；

作为唯一正式来源。

行业共识也必须有来源。

---

# 五、Human Confirmation

人工确认默认只适用于：

当前项目 + 明确作用范围。

除非用户明确批准提升，不能进入通用工程规则。

如果新的 authority evidence 与旧 human confirmation 冲突：

- 保留旧确认；
- 建立 conflicting / superseded 关系；
- 不静默覆盖；
- 由用户重新批准当前项目最终口径。

---

# 六、Authority Evidence

设计回复、图纸会审、RFI、技术核定、设计变更等应尽量记录：

- `authority_id`
- `document_number`
- `issue_date`
- `issuer`
- `revision`
- `source_file`
- `source_sha256`
- `affected_drawings`
- `applicability`
- `statement`
- `supersedes`
- `superseded_by`
- `status`

原正式依据不得因为新版本出现而被删除。

---

# 七、Supersede

历史记录不物理删除。

替代关系使用：

- `supersedes`
- `superseded_by`

表示。

例如：

R-002 supersedes R-001

则：

R-002:
`supersedes = ["R-001"]`

R-001:
`superseded_by = ["R-002"]`

---

# 八、正式算量与预估

## Formal

正式 DesignNetQuantity 只能使用：

- 有适用性的 confirmed/active engineering rule；
- supported project evidence；
- active authority evidence；
- approved project assumption。

行业共识如果尚未获得项目批准，不得直接参与正式数量。

## Provisional / Estimate

可以使用有来源的行业共识进行快速预估。

但必须明确：

- `provisional`
- 使用的 assumption；
- assumption 来源；
- 当前未确认事项。

预估结果不得冒充正式净量。

---

# 九、Unresolved / Rejected

以下内容必须保留：

- unknown
- unresolved
- conflicting
- rejected
- superseded

特别是已经排除过的错误解释，不得删除。

这样可以防止 AI 在未来重新提出同一个已经否定的结论。

---

# 十、软件执行契约分离

以下内容不是工程规则：

- ProjectSpecificEvidenceGate
- QuantityBuildPlan
- DesignNetQuantityBuilder
- Replay
- EvidenceAuthorizationContract
- ProvenanceRecordContract
- AssumptionDependencyPolicy

这些继续由软件执行契约管理。

Rule Baseline 负责回答：

“工程事实和项目依据是什么？”

软件执行契约负责回答：

“软件怎样安全使用这些事实？”

---

# 十一、v0.1 范围

v0.1 坚持：

Small and correct.

优先覆盖：

- 消防电 Golden
- Golden 项目证据
- 项目批准假设
- 已否定 / unresolved
- Leader Evidence 相关规则

暂不批量迁移全部历史聊天。
