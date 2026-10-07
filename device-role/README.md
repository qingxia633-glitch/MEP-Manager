# DeviceRoleResolver v0.1

仅输出 `INSERT → DeviceRoleEvidence`，与 `geometry-connection/` 无代码依赖。输入不使用线路、坐标、邻近文字、图层或厂家资料判断角色。结果不可用于直接生成电气连接、回路或工程量。

## 入口

```powershell
python device-role/resolve.py --snapshot <MEP-full-entity-report.txt> --probe <block-definition-probe.txt> --device 13017 --output <new-role-evidence.json>
python device-role/tests/test_resolver.py
pwsh -NoProfile -File model-core/tests/Run-Regressions.ps1
```

`RoleContext.from_reports(snapshot, probes, legends=None, role_tags=('A',))` 自动读取实例ATTRIB、定义ATTDEF、直接子INSERT的实例ATTRIB。报告DWG来源必须相同。`resolve_device_role(handle, context)` 不修改context或来源文件。也可以从已有结构化实例/定义属性记录构造RoleContext，不能将已由线路推断的角色伪装为原始属性。

## 优先级

| 级别 | 证据 | 常规状态 |
|---|---|---|
| 1 | 实例自身角色ATTRIB | supported |
| 2 | 当前定义内直接子INSERT的自身ATTRIB | supported，路径保留父/子handle |
| 3 | 定义ATTDEF默认角色 | inherited，evidence_type=block_definition_default |
| 4 | 限定来源且经审核绑定的项目图例 | partial，仅符号/类型证据 |
| 5 | 同图同精确定义的独立实例ATTRIB重复语义 | 至少两个一致实例才inherited；一个为partial |

实例值覆盖默认值，记录 `overridden_defaults` 和 `lower_priority_disagreements`，不产生假冲突。最高有效优先级内角色或属性值矛盾才 `conflicting`，此时不选择任一角色。更高优先级出现未识别角色文字时保留unknown，不跳过它去套较低默认值。

`raw_role_text` 和各条 `raw_value` 保留原文。`evidence`包含原始属性，`selected_evidence`指出实际采用的证据。显示码取自身`$TEXT$`，其次自身明确代码属性，再其次直接子INSERT显示码；显示码不参与角色推断。`I`、`I/O`、`M1`、`M2`单独不证明设备角色，`B=1`不解释为地址、回路或数量。

## 图例准入

`--legend-evidence` 为经审核的结构化证据列表，不从附近图例行自动绑定。只允许来源文件 `EC-4#-P+TBD_t8_t3.dwg`。每条需：

```json
{
  "source_drawing": "EC-4#-P+TBD_t8_t3.dwg",
  "source_handle": "2399E",
  "raw_value": "模块箱",
  "target_drawing": "与快照DWG字段完全相同的来源字符串",
  "target_block_name": "当前实例精确块定义名",
  "binding_verified": true,
  "binding_evidence_refs": ["已审核符号/定义对应证据引用"]
}
```

上例仅说明输入格式，不宣称已建立某个目标绑定。同显示码、不同定义且没有明确绑定时拒绝采用；其他来源图例保留为ignored evidence。v0.1不自动证明跨DWG块等价。

## 首批角色及属性

仅支持 smoke_detector、heat_detector、manual_call_point、input_module、input_output_module、module_box、fire_damper、smoke_exhaust_outlet。词典为有限原文别名，不进行模糊邻近或行业常识推断。其他原文保持unknown。

当前防火阀温度解析限定已出现的70/280℃动作常开/常闭表达，分开保存action_temperature、temperature_unit、normal_state。实际实例280℃优先于定义默认70℃。

## 技术边界

- 离线快照/probe适配器；缺失定义不自动调用AutoCAD。
- 子实例属性只读一层，不推测更深层子组件是父设备的角色。
- 同定义继承只用同一快照的原始实例ATTRIB，不循环传播derived角色，不以effective name相同替代同定义。
- 原始属性角色标签默认只有A，可显式配置；REMARK或任意文字不会自动当设备名称。
- 未知属性值不会扩展词典；没有数值confidence假精度。
- 真实13304/134D9显示码为I，隐藏属性为单输入单输出模块，均保留，不用I覆盖角色。

专项测试与原51套回归分别运行；不修改历史expected、项目规则及冻结JSON。
