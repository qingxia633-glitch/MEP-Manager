# 通用证据模型 v1

本模块只消费已读取证据，不操作 AutoCAD，不搜索新图纸，不生成 Circuit、终端连接、路径或工程量。旧采集器、几何内核、领域模块和历史 JSON 均保留。

第二样本新增系统身份隔离、显式跨系统候选和图例冲突，见 [FIRE-SAMPLE.md](FIRE-SAMPLE.md)。下面的空网络和四项缺失描述指第一份golden sample；旧未标注系统的数据不能用于满足新系统专属需求。

## 模块边界

| 文件 | 职责 |
|---|---|
| `ModelCore.psm1` | 通用契约、作用域校验、信息需求评估、复核与网络骨架 |
| `GoldenSample.psm1` | 已审核真实样本适配；不是发现算法 |
| `capabilities.json` | 能力覆盖目录；明确实现、人工调查和计划功能的区别 |
| `tests/golden-sample.json` | 样本 Handle、局部作用域、会话人工确认和任务需求 |
| `tests/source-manifest.json` | 十份不可变输入的路径与 SHA-256；不自动迁移快照 |
| `Read-GoldenModel.ps1` | 只向 stdout 输出模型 JSON，不写历史结果 |

## 契约

### CapabilityCoverage / ValidationProfile

`capabilityId, domain, objectType, capabilityType, status, validatedSamples, applicableScope, knownLimitations, unresolvedCases, evidenceRefs, version`。

每条含 `ValidationProfile`：验证层级、样本、作用域、限制及依据。不按测试断言数量自动升级。当前没有能力标为 `reusable`；该枚举保留，但晋级尚需独立多样本评审政策。`validated_sample` 仅证明目录内样本和范围；新通用模块为 `experimental`。目录是显式维护的覆盖登记，不是自动审计整个代码库。

### AssociationCandidate

`subject, relationType, candidateTargets, supportingEvidence, opposingEvidence, missingEvidence, scope, status, provenance`。

七种关系：usesConfiguration、sameBuildingLocation、represents、suppliesCandidate、controlsCandidate、belongsToSystemCandidate、categoryMembershipCandidate。

subject/targets 使用带快照的身份引用；证据保持独立。支持证据必须在请求项目、快照和对象作用域内。`supported` 仍表示该候选命题有支持，`physicalConnection` 始终未决。存在反对证据时不能直接声明 supported。不同专业使用同一关系契约，而领域视图只引用关联 ID。

### Evidence 与 InformationRequirement

证据保留 `evidenceId, kind, fact, claim, status, scope, dependencies, provenance`。原有 DrawingFact 原文保存在完整原始模型/报告记录中；人工确认单独保存，不覆盖事实。

需求保留 `requirementId, taskType, requiredFact, status, satisfiedByEvidence, missingReason, searchScopeCandidates, blocking`，并附评估作用域和证据层级。评估结果为 satisfied / partial / missing / conflicting / not_applicable；失效证据、缺失依赖或循环推导不能满足需求。需求目录由任务适配器明确提供，本阶段不从自然语言自动生成任务计划、不自动检索资料。

### 三层网络

| 网络 | 后续承载内容 | 本阶段 |
|---|---|---|
| LogicalNetwork | 系统声明及逻辑关系 | 空结构 |
| CarrierNetwork | 桥架、管道等承载设施 | 空结构 |
| RoutingNetwork | 安装线路路径假设 | 空结构 |

每层提供 nodes / edges / ports / connectionHypotheses / routeHypotheses / gaps / boundaryEndpoints。元素类型为 NodeCandidate、EdgeCandidate、PortCandidate、ConnectionHypothesis、RouteHypothesis、Gap、BoundaryEndpoint，带 sourceRefs、endpointRefs、ownerRef、coordinateContextRef、证据和未决方向。BoundaryEndpoint 默认 unknown_continuation。扩展 data 保存类型特有的候选数据，不执行寻路。跨层引用不会自动生成边；几何接触不是电气连接，载体不是电缆。

### ReviewItem

按 requirement/association ID 生成稳定复核项：来源文档、对象 Handle/坐标、候选解释、影响任务/能力、缺失证据、待定人工决策、失效依赖。低置信度关联、歧义和需求冲突都可进入复核。人工决策尚无 UI；后续应追加证据再重新评估，不能改写 RawEntity。当前只保存依赖并在需求评估时处理指定失效证据，不实现后台变更监听。

### RuleReference

`ruleId, version, applicability, evidenceDependency, sourceRef, executionStatus`。规则来源为《MEP-Manager安装算量完整规则库 v1.0》。仓库已提供PDF，第二样本仅引用已核对的第14页R072；第一样本 `ruleReferences=[]` 保持不变。不执行计量规则。项目内“同名配置”来自人工确认，不冒充规则库规则。

## Golden sample

完整保存三份旧候选 JSON，包括原 E1DB 配置关联和原坑模型 unresolved 状态。另建 3DA9 原始实例记录及人工确认覆盖层：

- 3DA9 → usesConfiguration → QWB1 配置候选；
- K1-4 → sameBuildingLocation → 3DA9；
- 三条表示路径的候选集合 → represents → K1-4；
- 3DA9 → suppliesCandidate → 泵组，限组级支持。

`PumpGroupElectricalAssociationCandidate` 是最后一条通用关联的领域视图，引用配置和三条 OutgoingRowCandidate。未建立左右泵分配、水位设备绑定或物理供电连接。

位置覆盖层为 canonical_placement_candidate，保留 52 / 3380 / 531D→69F4 三条表示，selectedRawRepresentation 未决；本模块不重新计算 WCS。类别参数、16270 运行逻辑均不继承。

八项需求前四项 satisfied：配置、安装实例、泵组位置、组级关联。后四项 missing：逐泵映射、水位绑定、物理路线、采购界面。生成四项 ReviewItem，整个任务仍 blocked_for_confirmed_supply。

## 运行和测试

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File model-core/Read-GoldenModel.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File model-core/tests/Test-Model.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File model-core/tests/Run-Regressions.ps1
```

最后一个命令执行 21 套离线测试，不调用 AutoCAD；Discovery 测试的旧结果文件在 finally 中按原字节恢复。静态 LISP 测试不能代替真实 AutoCAD 运行验收；本次没有新增 CAD 行为。

下一步优先用另一专业的独立已审核样本检验通用契约和需求/复核输出，不扩大当前样本线路调查，也不凭本次成功将能力晋级为全图通用。
