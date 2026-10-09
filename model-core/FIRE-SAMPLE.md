# 第二 Golden Sample：系统身份隔离

## 实现边界

使用既有火灾报警快照和会话中的4号楼消防图例人工确认，不操作 AutoCAD，不扩展图纸搜索。运行 `Read-FireGoldenModel.ps1` 只向 stdout 输出 JSON。原 QWB1/K1-4 fixture、来源指纹和历史结果均保留。

新增 `SystemIdentity.ps1`、`LegendCandidates.ps1`、`FireGoldenSample.psm1`、`tests/fire-fixture.json` 和 `tests/Test-SystemIsolation.ps1`。ModelCore 原有函数以可选参数扩展；回归入口增加新套件。

## 系统身份与默认拒绝

`SystemIdentity = { systemType, systemId, identityStatus }`

`SystemScope = { projectId, systemIdentity, propagation: explicit_only }`

支持 fire_alarm、fire_alarm_power、fire_phone、fire_broadcast、monitoring_security、other_weak_current、unknown，以及用于隔离验证的 power、lighting。

- systemType 区分专业系统类别，systemId 区分具体系统/回路实例。未取得回路编号时为 unresolved，不捏造真实系统号。
- 本样本的网络只是**系统类别的候选集合**。同类别、systemId=unresolved 的候选可进入同一类别集合，不能据此认定同一真实回路。显式不同 systemId 不相容；类别级证据不能自动满足某一已编号回路的需求。
- Evidence、AssociationCandidate、InformationRequirement、LogicalNetwork、NodeCandidate、EdgeCandidate均携带systemIdentity/systemScope。
- 需求评估和普通关联校验必须匹配项目、系统类别和系统ID。unknown 不匹配任何系统，包括另一个 unknown。
- 旧数据两边均未提供系统作用域时保留旧接口行为；系统专属任务不能借未标注旧证据绕过校验，带系统证据也不能通过未标注任务绕过。
- 网络成员只能经 `Add-LogicalNetworkElement` 校验加入；跨系统、缺少系统、unknown成员被拒绝。候选边/连接的端点必须已属于该网络。不会依据同坐标、同代号、同块名去重或生成边。
- 以上是构造与评估API的校验，并非对任意外部手工修改的JSON提供密码学完整性保护。

## 显式跨系统关系

`CrossSystemAssociationCandidate` 保存subject/targets、源系统与各目标系统作用域、来源及支持/反对/缺失证据；状态为candidate，`networkMergeAllowed=false`。

样本 `18548` 的名称声明含电话插孔，因此建立报警设备角色与电话插孔角色的两个候选节点。两者共享原始表达来源，但分属两个逻辑网络，只通过显式跨系统候选关联，不确认实体端口、电话连接或报警回路归属。

## 图例与冲突

- `CrossDrawingLegendCandidate` 保存完整用户映射、HumanConfirmation及“当前项目/4号楼/电气/4号楼/EC-4#-P+TBD_t8_t3.dwg”作用域。原说明图快照与Handle尚未提供，明确not_supplied。
- `I/O`：18526与141AB的名称、代号属性支持 `LegendEntryCandidate(status=supported)`，仅适用于已核对表达；不全项目推广。
- `SI`、`2I/2O`：车库适用性保持unresolved；不从重复代号推导短路隔离器或卷帘用途。
- `SymbolDefinitionCandidate` 记录块名体系和语义来源，几何未比较，跨图符号定义一致性未决。
- `1851F/18520/18521`、`18516/18517/18518`分别产生 `ReviewItem(type=legend_semantic_conflict)`。4号楼图例“I=输入模块”、车库隐藏名称“单输入单输出模块”和非隐藏“I”均保留；不多数投票、不覆盖。对应角色需求为conflicting。

## 样本与需求结果

保留10个指定局部原始实体，加两个冲突INSERT，共12条顶层记录及全部已导出属性。141AB只作为此前调查已知的额外图例支持来源，不扩展局部窗口。

- 5个消防报警候选节点；1个电话插孔候选节点；其他系统集合为空。
- 消防、电话图层只提供线路系统候选；五条线路都未加入LogicalNetwork。
- 两条WIRE-消防控制线为unknown，不推导为电源或报警总线。
- 18575顶点与18526插入点的几何相同经快照坐标复核，保存一个未入网的ConnectionHypothesis；端口和电气关系未决。
- I/O角色需求satisfied，表示名称声明支持候选角色；两个I角色需求conflicting；电话关系、广播关系missing；实际逻辑网络成员需求partial。
- 没有RoutingNetwork、Circuit、实际路线、线长或工程量。

## 规则来源

`reference/rules/MEP_Manager_安装算量完整规则库_v1.0.pdf`

SHA-256：`53DE2C47DDCDFE132C3E1077153D7D1BD13E6355805F61688FCDCAD6CB2F1A5D`

已只读核对第14页 R072：“综合布线、监控、门禁、消防报警独立建网，禁止跨系统寻路。”

只登记R072，保持executionStatus=not_executed；模型隔离按本轮明确需求实现。R075涉及按系统图确定线型芯数，本轮不实现、不推导这些属性。未调用计量规则。规则来源登记更新为available，第一样本的已用规则列表仍为空。

## 验证入口

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File model-core/tests/Test-SystemIsolation.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File model-core/tests/Run-Regressions.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File model-core/Read-FireGoldenModel.ps1
```

目录新增：system_identity_isolation、cross_system_association、cross_drawing_legend均为experimental；legend_conflict_review为validated_sample。不标记reusable。
