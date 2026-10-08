# QuantityEligibilityResolver v0.1

消费ProjectSpecificSemanticDecision和已审核的结构化计量证据，返回资格判断及未求值的QuantityBuildPlan。不导入或重跑前四个Resolver，不生成DesignNetQuantity，不计算最终净量。

## 使用

```powershell
python quantity-eligibility/resolve.py --input quantity-eligibility/fixtures/golden.json --output new-eligibility.json
python quantity-eligibility/tests/test_resolver.py
```

`load_evidence` 校验来源文件SHA256和本模块source_id引用；Gate内部来源命名空间原样保留，不重新审核。`resolve_eligibility(item)`检查调用方提供的已审核证据。

## 检查维度

1. Gate supported、两个许可标志严格为true；否则立即blocked。
2. 明确edge/segment范围，与Gate的handle、segment、项目和图纸一致。v0.1尚不支持多边bounded path。
3. 基础几何长度、原始实体、单位、显式转换及provenance。使用Decimal验证单位换算一致性，不算最终净量。
4. 规格和敷设方式由direct_project_binding或reviewed_project_rule绑定；不解析附近文字/候选语义。
5. multiplier必须明确有来源和解释，不能从2×1.5解析倍数。
6. 高度支持或有来源的not_applicable；3D base_path必须有高度依据。
7. 每个transition的owner、device、type、length、unit、状态、来源和假设引用；预期端点清单必须完整。
8. 去重键edge_handle+segment_id+device+transition_type，独立adjustment_id也不能重复；邻边owner冲突阻断。
9. vertical/other字段缺失不能当零；not_applicable需理由、来源和绑定。
10. 假设有批准状态、来源、局部作用范围及条件匹配；Golden的300mm条件不推广。
11. 数值必须有限、单位一致；同级measurement_claims与主transition/multiplier矛盾时conflicting。
12. 非design_net调整禁止进入公式。采购和计价上下文不作为资格条件。

## 状态

blocked：Gate未通过或明确禁止；conflicting：重复、邻边归属或数值证据矛盾；unresolved：关键条件缺失；partial：假设缺作用范围等不足；eligible：所有检查通过。只有eligible提供计划和generation_allowed=true；其他状态不提供可执行计划。

## QuantityBuildPlan

保存base_path、owned_adjustments、multiplier、specification、binding、assumptions、provenance及符号公式：`(base_path.value + owned_adjustments[].length) × multiplier.value`。不执行公式，无total_length/最终quantity字段，quantity_generated=false。

Golden的raw 2D和换算是审计事实；计划base_path使用冻结3DRouteCandidate的slabFollowingLengthMeters。坡面已包含在base_path，不再把原始2D或坡面差额加一次。两端0.150m作为独立transition项。没有重算或复制正式总净量值。

## Fixture边界

tests/build_fixtures.py只投影指定冻结JSON字段，既有单位证据决定mm和0.001；来源哈希全部保留。不重算GeometryConnection/角色/候选语义/Gate/最终净量。base几何仅引用既有长度字段，不重新研究其历史结构标高调查。Gate负样本直接消费上一阶段四条线的决策。

## 技术缺口

仅验证已审核结构化证据，不自动从图纸解析计量条件。来源哈希验证不等于审核真实性认证；API调用者负责完整录入所有同级冲突证据和预期transition清单。当前量纲为线性长度，单位换算要求输入精确十进制值；不处理混合计量单位、多边路径和自动单位推断。没有Quantity Builder，不处理采购/计价，也不修改任何冻结对象。
# Export and arithmetic hardening

`export_plan(..., correction=None, policy=...)` is allowed for a valid original
drawing reference. Supplied correction evidence still requires approval, source
hash, exact target/historical binding, corrected reference and provenance.
No historical object is rewritten. Conversion checks use a private Decimal
context sized from operand coefficients; rounding or inexact arithmetic blocks
eligibility rather than depending on the caller's context.
