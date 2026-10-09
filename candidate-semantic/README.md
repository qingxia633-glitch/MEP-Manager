# CandidateSemanticResolver v0.1

输入两端的 `GeometryConnectionEvidence`、`DeviceRoleEvidence` 和外部项目规则，输出 `CandidateSemanticEvidence`。通用模块不导入前两个 Resolver，不读 CAD、不计算距离、不识别属性。几何接触与设备类型只能来自上游对象。

## 使用

```powershell
python candidate-semantic/resolve.py --input edge-evidence.json --rules candidate-semantic/project-rules/garage-fire-alarm.json --output new-candidate.json
python candidate-semantic/tests/test_resolver.py
```

输入需有 `edge_handle`、`scope`、`endpoint_A/B.geometry_connection`、`endpoint_A/B.device_role`；`edge_metadata` 可保存 layer、specification_evidence、nearby_text。scope 的 project、validation_area 必须与项目规则精确相符，不通过坐标推定分区。

## 外部规则

原项目规则文件保持冻结。`project-rules/garage-fire-alarm.json` 是本次用户要求的机器可读配套配置：列出角色集合、无方向匹配及 confidence 政策，通过路径和 SHA256 引用原规则。`rules.load_rules` 从原文件读取 candidate_role、validation_status、scope、provenance 等，配置不得覆盖它们。原规则哈希变化须重新审核，不能静默继续。

通用代码不包含 A/B/C/D 角色组合或项目图层名称。context_restriction 规则保留在输出，所有图层、规格、附近文字均只作为 supporting_context；匹配器只读取端点角色组合。

## 证据门槛

- 两端几何 supported 才能正常分类；partial 输出 partial / confidence unknown；unresolved、rejected、非法状态阻断组合匹配。
- 角色 supported 正常参与；inherited 保留来源并降低一级 confidence；partial、unresolved、conflicting、unknown 阻断。
- edge/target/device handle 必须一致，缺失或混配阻断。
- 默认无方向；仅规则显式 directional=true 才按输入 A/B 顺序匹配，不能据 CAD 起终点生成方向。
- 不同候选角色同时命中输出 ambiguous；相同候选角色合并规则，保留全部来源，confidence 采用最保守等级。

## Confidence 与状态

配置中 supported/validated → high；当前项目 A/C 的 **partial_pattern_support → medium**，不把它当成正式已验证。inherited 再降一级，最低 low。B 的 insufficient_project_local_evidence → low。未知验证状态阻断；有几何 blocker 则 confidence unknown。

candidate_status=candidate 仅表示候选规则已匹配，不是项目正式语义。所有输出固定 `project_specific_status=not_evaluated`、`design_net_quantity_eligible=false`。输入旧项目状态仅保留在 prior_project_specific_status，不反写源对象。

## 验证与边界

tests/build_fixtures.py 是独立测试准备程序，调用未修改的上游 Resolver，读取已指定项目证据生成结构化输入；语义模块不调用它。9个真实边样本包括4个Golden关联、4个独立样本和14423负例。12EA0混合fixture使用真实继承角色和明确标记的合成几何；Rule B正向组合仅为合成测试，不是项目真实验证。

不验证电气端子、可编址性、具体回路、线规传播或计量。只信任调用方提供的上游证据和项目scope；不提供防篡改签名或自动跨图身份认证。原始证据、项目规则、输入上下文和限制随输出保留。
# Evidence identity hardening

Inputs must include `evidence_identity.project_id` and `drawing_ref`.
The item uses `parent_path`; Geometry evidence uses `edge_parent_path` and
`target_parent_path`; DeviceRole evidence uses `parent_path`. Arrays contain the
complete enclosing INSERT path (`[]` explicitly represents ModelSpace).
Missing or mismatched identities stop composition as unresolved. Handles alone
are not cross-drawing identities. Legacy JSON is not rewritten or implicitly trusted.
