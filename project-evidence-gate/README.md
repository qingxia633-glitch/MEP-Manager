# ProjectSpecificEvidenceGate v0.1

`CandidateSemanticEvidence + reviewed project evidence/bindings → ProjectSpecificSemanticDecision`。不导入前三个 Resolver，不重算几何、角色、候选规则、拓扑、长度或工程量。

## 入口

```powershell
python project-evidence-gate/resolve.py --candidate candidate.json --evidence project-evidence-gate/project-evidence/garage-golden.json --project-id "current garage fire-alarm project" --drawing-ref "EX-BX地下车库火灾报警平面图_t8_t3.dwg" --output new-decision.json
python project-evidence-gate/tests/test_resolver.py
```

Python接口：`evaluate_semantics(candidate, bundle, context)`；文件入口使用 `load_bundle(path)` 校验来源文件SHA256和JSON pointer assertions。来源哈希或字段变化报错，不静默迁移。

## 项目证据契约

每条证据保存 evidence_id、evidence_type、evidence_strength、status、semantic_role、assertion（affirm/deny）、binding_id、provenance。文件方式还要求 source_ids 指向已验证来源。绑定保存 binding_id、review_status=reviewed、project_id、drawing_ref、edge_handle、可选segment_id、evidence_ids及provenance。

项目/图纸/edge/segment必须精确一致。部分segment授权不扩展到整条edge。只有设备绑定、缺少明确线路映射时不能授权整条线。实例device_handles可记录为辅助来源，但不传播至该设备的其它incident edges。

### 可参与supported的类型

| evidence_type | 接受强度 |
|---|---|
| edge_annotation | direct_object_binding |
| circuit_bus_identifier | direct_object_binding / system_mapping |
| local_wiring_diagram | direct_local_design_binding |
| system_diagram_mapping | system_mapping |
| unique_design_statement | project_rule_binding |
| reviewed_project_rule | project_rule_binding |
| human_project_confirmation | direct_object_binding / direct_local_design_binding / project_rule_binding |

厂家资料、网络资料、图层、规格、邻近文字、模式样本、candidate confidence永远不能单独升级，即使输入错误地标为direct。pattern_only/contextual_only/external_generic只保留辅助上下文，不作为正式授权。

## 决策

- 有已审核、明确绑定的supported affirmation且无未决直接证据：supported；candidate规则成熟度不限制直接证据。
- 直接证据明确另一个角色：覆盖candidate，保留candidate_vs_direct记录；这不是直接证据之间的冲突，不阻断。
- 同对象两个直接肯定角色不同，或同一角色affirm/deny冲突：conflicting。v0.1不自行在四种直接强度间制定权威排序，全部作为peer保守处理。
- 适用的直接证据status未决、审核未完成或缺provenance：阻断通过；已有肯定时partial，否则unresolved。
- 明确直接deny当前candidate角色且无肯定：rejected，只否定该语义，不否定物理或间接电气关系。其他角色的deny不等于拒绝当前candidate。
- 只有candidate或弱证据：partial；完全未知且无证据：unresolved。

## 语义与计量隔离

supported才输出 `semantic_gate_passed=true`、`design_net_quantity_eligible=true`。后者仅指语义层允许进入QuantityEligibilityResolver；同时固定 `quantity_eligibility_status=not_evaluated`、`quantity_generated=false`。本模块不检查高度、范围、transition、规格、去重或计量口径，不生成数量对象。

## Golden适配

新增garage-golden.json只引用冻结的局部busSegment语义、正式项目规则、正式发行记录。以原busSegment明确的13CF5及fire_alarm_bus_segment为语义来源，加上用户本轮确认的正式Golden样板授权；不由净量值推定角色，不重算既有数值。其它四条线只消费上一阶段输出，无直接绑定时不通过。

## 技术边界

这是已审核结构化证据Gate，不是图纸文字/引线提取器，不自动判定某说明能否唯一映射到线路。SHA256防止来源静默变化，不证明审核人身份或文档权威；API调用者负责提供真实项目审核及context。没有电子签名、审批工作流或来源高低排序。原证据和上游JSON均不反写。
