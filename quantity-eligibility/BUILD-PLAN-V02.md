# QuantityBuildPlan schema v0.2

新增 `plan_v02.export_plan`，只扩充已eligible的旧Decision，不改变v0.1 Resolver、旧BuildPlan或任何正式DesignNetQuantity。这里没有Builder。

## 新执行契约

- eligibility、formula_ready、generation_allowed三个门槛均进入计划；保留design_net_quantity_generation_allowed别名。
- approved_semantic_role从已通过的Gate携入，不重审语义。
- deduplication保留原status=supported，新增evidence_status=supported和execution_status=passed；passed表示引用上游已完成的资格与去重检查，未重算去重。
- unit_execution_contract逐项保存原值/原单位、归一值/归一单位、量纲、显式conversion及来源。当前Golden各项已为m，执行转换为经审核的identity factor=1。原二维mm→m换算保留为audit_only，不重复进入公式。非同单位输入须先补明确转换，v0.2导出器不猜换算。
- arithmetic_policy指定Decimal及足够精度，intermediate Inexact/Rounded均应拒绝；只在最终reporting阶段执行9位ROUND_HALF_EVEN。
- project_numeric_reporting_policy是当前项目批准的软件规则，明确is_drawing_fact=false、is_national_standard=false。
- source_build_plan_hash、source_decision_artifact_hash、source_evidence_hashes、content_hash保留来源及确定性。content_hash为去掉自身content_hash后的排序UTF-8 JSON SHA256。

## 纠正证据

CorrectionEvidence从原报警快照DWG字段读取正确basename，保留原乱码值、纠正值、来源原文/哈希、授权依据和两个目标object_id。仅新计划副本中匹配原值的drawing_ref被纠正，逐条保存JSON路径。历史JSON不反写；来源哈希或目标不匹配拒绝导出。

## 产物与测试

`outputs/quantity-build-plan-v02/`包含两份新计划、纠正证据、数值报告政策和numeric-precheck。生成脚本拒绝替换内容不同的已有产物。

`tests/generate_v02_evidence.py`内的求值仅为本轮数值预检查，不构造DesignNetQuantity。保留原精确base_path、两个transition及multiplier，无修正项。schema required/const契约由专项测试校验；尚未集成第三方全量JSON Schema验证器。

运行：
```powershell
python quantity-eligibility/tests/test_plan_v02.py
```
