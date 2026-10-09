# DesignStatement Bridge 固定种子质量审计

结果：ew0002-design-statements-reviewed-v2-20260924.json。固定种子20260924；各组先按statementId排序，再Fisher-Yates打乱；顺序抽取10条partial和10条unresolved。supported为0，不补造该组。审计对象是候选质量，不报告准确率。

## paragraph:21:0 — partial

```text
4.11 低压配电线路保护低压主进线断路器按二段式保护设计，设过载长延时、短路短延时保护脱扣器，并暂保留接地故障保护功能，当高压侧三相过电流保护兼作低压侧接地故障保护其灵敏度不够时启动此功能。
```

- Handle: 23424, 23425, 23426
- 页面: EW-0002; columnScopeRef: 7360ADB34A4E0BACACD2768261FBB3E19835C07C65F9F4959F94BAE5751A249F:50708:sheet:column:7; textColumnRef: text-region:7:column
- Section: 4.11 / 23424
- SubItem: 
- 类型候选: requirement; 上游Atomic类型: requirement
- subjectScopeCandidate: unresolved; scopeSource: unresolved; 自动应用: false
- 条件/备选/引用: 当高压侧三相过电流保护兼作低压侧接地故障保护其灵敏度不够时
- Raw span反查: True；原文覆盖此Atomic，不等于完整Section或完整工程语义。
- 质量审计判断: 条件span在同一Atomic内；4.11重复编号仍保留，未把编号相同当作同一结构。完整度继续未决。
- 未决原因: instance_applicability_unresolved; semantic_split_candidate_not_rule; section_completeness_unresolved

## paragraph:22:0 — partial

```text
4.12.1 非消防负荷：较短的线路，设过载长延时和短路瞬时脱扣；
```

- Handle: 23428
- 页面: EW-0002; columnScopeRef: 7360ADB34A4E0BACACD2768261FBB3E19835C07C65F9F4959F94BAE5751A249F:50708:sheet:column:7; textColumnRef: text-region:7:column
- Section: 4.12.1 / 23428
- SubItem: 
- 类型候选: requirement; 上游Atomic类型: requirement
- subjectScopeCandidate: 非消防负荷; scopeSource: hierarchy; 自动应用: false
- 条件/备选/引用: 较短的线路
- Raw span反查: True；原文覆盖此Atomic，不等于完整Section或完整工程语义。
- 质量审计判断: 短线路条件与保护要求对应；非消防负荷由标题context span支持，未注入rawText，阈值未决。
- 未决原因: instance_applicability_unresolved; semantic_split_candidate_not_rule

## paragraph:23:0 — partial

```text
4.12.2 消防负荷：设过载报警（不跳闸）和短路瞬时脱扣，所有电动机负荷配电断路器订货采购时采用电动机型短路瞬时脱扣（即32002）断路器。
```

- Handle: 23429, 2342A
- 页面: EW-0002; columnScopeRef: 7360ADB34A4E0BACACD2768261FBB3E19835C07C65F9F4959F94BAE5751A249F:50708:sheet:column:7; textColumnRef: text-region:7:column
- Section: 4.12.2 / 23429
- SubItem: 
- 类型候选: requirement; 上游Atomic类型: requirement
- subjectScopeCandidate: 消防负荷; scopeSource: hierarchy; 自动应用: false
- 条件/备选/引用: 
- Raw span反查: True；原文覆盖此Atomic，不等于完整Section或完整工程语义。
- 质量审计判断: 消防负荷标题可提供局部对象范围；采购/型号文字保留原值，未应用到具体断路器。
- 未决原因: instance_applicability_unresolved; semantic_split_candidate_not_rule; section_completeness_unresolved

## paragraph:38:0 — partial

```text
6.2 本工程照明设计照度标准、统一眩光值、显色指数、照明功率密度值要求详见表6.1。
```

- Handle: 23434
- 页面: EW-0002; columnScopeRef: 7360ADB34A4E0BACACD2768261FBB3E19835C07C65F9F4959F94BAE5751A249F:50708:sheet:column:10; textColumnRef: text-region:10:column
- Section: 6.2 / 23434
- SubItem: 
- 类型候选: reference_statement; 上游Atomic类型: reference_statement
- subjectScopeCandidate: unresolved; scopeSource: unresolved; 自动应用: false
- 条件/备选/引用: 详见表6.1
- Raw span反查: True；原文覆盖此Atomic，不等于完整Section或完整工程语义。
- 质量审计判断: 表6.1引用有原文span，目标未解析；未因本工程字样扩大scope。
- 未决原因: instance_applicability_unresolved; semantic_split_candidate_not_rule; section_completeness_unresolved

## paragraph:26:0 — partial

```text
5.1 采用~380/220V放射式和树干式相结合的配电系统，按不同设备组及防火分区划分回路。
```

- Handle: 2342D
- 页面: EW-0002; columnScopeRef: 7360ADB34A4E0BACACD2768261FBB3E19835C07C65F9F4959F94BAE5751A249F:50708:sheet:column:7; textColumnRef: text-region:7:column
- Section: 5.1 / 2342D
- SubItem: 
- 类型候选: requirement; 上游Atomic类型: requirement
- subjectScopeCandidate: unresolved; scopeSource: unresolved; 自动应用: false
- 条件/备选/引用: 
- Raw span反查: True；原文覆盖此Atomic，不等于完整Section或完整工程语义。
- 质量审计判断: 系统方案陈述暂保留requirement候选；类型证据仍粗，不能把partial当成已验证规则。
- 未决原因: instance_applicability_unresolved; semantic_split_candidate_not_rule

## paragraph:29:49 — partial

```text
低压侧按供电部门不同电价要求分设子表；
```

- Handle: 23419, 2341A
- 页面: EW-0002; columnScopeRef: 7360ADB34A4E0BACACD2768261FBB3E19835C07C65F9F4959F94BAE5751A249F:50708:sheet:column:6; textColumnRef: text-region:6:column
- Section: 4.8 / 23418
- SubItem: 
- 类型候选: requirement; 上游Atomic类型: requirement
- subjectScopeCandidate: unresolved; scopeSource: unresolved; 自动应用: false
- 条件/备选/引用: 
- Raw span反查: True；原文覆盖此Atomic，不等于完整Section或完整工程语义。
- 质量审计判断: 分设子表原文跨两个TEXT，span可恢复；未从电价字样生成计价规则。
- 未决原因: instance_applicability_unresolved; semantic_split_candidate_not_rule

## paragraph:34:0 — partial

```text
6.2.1 选用的LED灯的光度性能应符合下列规定：1、LED灯的初始光通量不应低于额定光通量的90％，且不应高于额定光通量的120％；
```

- Handle: 478BB, 478BC
- 页面: EW-0002; columnScopeRef: 7360ADB34A4E0BACACD2768261FBB3E19835C07C65F9F4959F94BAE5751A249F:50708:sheet:column:9; textColumnRef: text-region:9:column
- Section: 6.2.1 / 478BB
- SubItem: 
- 类型候选: requirement; 上游Atomic类型: requirement
- subjectScopeCandidate: unresolved; scopeSource: unresolved; 自动应用: false
- 条件/备选/引用: 
- Raw span反查: True；原文覆盖此Atomic，不等于完整Section或完整工程语义。
- 质量审计判断: 标题与第1子项同处一个Atomic；Section正确，SubItemRef未强挂。语义/子项边界仍partial，Evidence阶段应保留此限制。
- 未决原因: instance_applicability_unresolved; semantic_split_candidate_not_rule; section_completeness_unresolved

## paragraph:10:0 — partial

```text
4.6.1 高压配电系统的短路故障保护应具备可靠、快速且有选择地切除被保护设备和线路的短路故障的功能。
```

- Handle: 2380A
- 页面: EW-0002; columnScopeRef: 7360ADB34A4E0BACACD2768261FBB3E19835C07C65F9F4959F94BAE5751A249F:50708:sheet:column:4; textColumnRef: text-region:4:column
- Section: 4.6.1 / 2380A
- SubItem: 
- 类型候选: requirement; 上游Atomic类型: requirement
- subjectScopeCandidate: unresolved; scopeSource: unresolved; 自动应用: false
- 条件/备选/引用: 
- Raw span反查: True；原文覆盖此Atomic，不等于完整Section或完整工程语义。
- 质量审计判断: 应具备提供要求候选依据；具体设备适用范围保持未决。
- 未决原因: instance_applicability_unresolved; semantic_split_candidate_not_rule

## paragraph:14:0 — partial

```text
4.2 供电电源 一级负荷应由双重电源供电，当一个电源发生故障时，另一个电源不应同时受到损坏。
```

- Handle: 23408, 2361D
- 页面: EW-0002; columnScopeRef: 7360ADB34A4E0BACACD2768261FBB3E19835C07C65F9F4959F94BAE5751A249F:50708:sheet:column:5; textColumnRef: text-region:5:column
- Section: 4.2 / 23408
- SubItem: 
- 类型候选: requirement; 上游Atomic类型: requirement
- subjectScopeCandidate: unresolved; scopeSource: unresolved; 自动应用: false
- 条件/备选/引用: 当一个电源发生故障时
- Raw span反查: True；原文覆盖此Atomic，不等于完整Section或完整工程语义。
- 质量审计判断: 当一个电源发生故障时与后续要求处于同一Atomic，宿主正确；不产生供电连接。
- 未决原因: instance_applicability_unresolved; semantic_split_candidate_not_rule

## paragraph:24:0 — partial

```text
5.3 对于因过负荷引起断电而造成更大损失的供电回路，过负荷保护应作用于信号报警，不应切断电源。
```

- Handle: 23729
- 页面: EW-0002; columnScopeRef: 7360ADB34A4E0BACACD2768261FBB3E19835C07C65F9F4959F94BAE5751A249F:50708:sheet:column:7; textColumnRef: text-region:7:column
- Section: 5.3 / 23729
- SubItem: 
- 类型候选: requirement; 上游Atomic类型: requirement
- subjectScopeCandidate: unresolved; scopeSource: unresolved; 自动应用: false
- 条件/备选/引用: 对于因过负荷引起断电而造成更大损失的供电回路，
- Raw span反查: True；原文覆盖此Atomic，不等于完整Section或完整工程语义。
- 质量审计判断: 对于供电回路的条件span与报警/不切电要求同宿主；不据此认定任何实际回路。
- 未决原因: instance_applicability_unresolved; semantic_split_candidate_not_rule

## paragraph:15:0 — unresolved

```text
4.3 应急备用电源本项目采用2路独立10kV高压电源，两路电源在末端自动切换一主一备，以保证一、二级负荷的要求。
```

- Handle: 2340C, 2340D
- 页面: EW-0002; columnScopeRef: 7360ADB34A4E0BACACD2768261FBB3E19835C07C65F9F4959F94BAE5751A249F:50708:sheet:column:5; textColumnRef: text-region:5:column
- Section: 4.3 / 2340C
- SubItem: 
- 类型候选: unknown; 上游Atomic类型: requirement
- subjectScopeCandidate: unresolved; scopeSource: unresolved; 自动应用: false
- 条件/备选/引用: 
- Raw span反查: True；原文覆盖此Atomic，不等于完整Section或完整工程语义。
- 质量审计判断: 应急并非应当要求信号；保留系统方案原文，类型unknown，未为了提升率强分。
- 未决原因: instance_applicability_unresolved; semantic_split_candidate_not_rule; statement_type_unresolved; atomic_type_signal_only

## hierarchy-bridge-paragraph:7360ADB34A4E0BACACD2768261FBB3E19835C07C65F9F4959F94BAE5751A249F:23406:0 — unresolved

```text
二级普通用电负荷:地下车库普通照明、小区变配电房。
```

- Handle: 23406
- 页面: EW-0002; columnScopeRef: text-region:5:column; textColumnRef: text-region:5:column
- Section: 4.1 / 23361
- SubItem: 
- 类型候选: unknown; 上游Atomic类型: unknown
- subjectScopeCandidate: unresolved; scopeSource: unresolved; 自动应用: false
- 条件/备选/引用: 
- Raw span反查: True；原文覆盖此Atomic，不等于完整Section或完整工程语义。
- 质量审计判断: 新增桥接正文已进入共享Atomic流程，负荷类别声明仍unknown；不能拿类型未定当作读取失败。
- 未决原因: instance_applicability_unresolved; semantic_split_candidate_not_rule; statement_type_unresolved

## paragraph:19:72 — unresolved

```text
断路器自带弹簧储能操动机构，操作电源为DC110V，40Ah。
```

- Handle: 2341F, 23420
- 页面: EW-0002; columnScopeRef: 7360ADB34A4E0BACACD2768261FBB3E19835C07C65F9F4959F94BAE5751A249F:50708:sheet:column:6; textColumnRef: text-region:6:column
- Section: 4.10 / 2341E
- SubItem: 
- 类型候选: unknown; 上游Atomic类型: unknown
- subjectScopeCandidate: unresolved; scopeSource: unresolved; 自动应用: false
- 条件/备选/引用: 
- Raw span反查: True；原文覆盖此Atomic，不等于完整Section或完整工程语义。
- 质量审计判断: DC110V/40Ah原文完整；现有类型未确认，未转为设备参数事实。
- 未决原因: instance_applicability_unresolved; semantic_split_candidate_not_rule; statement_type_unresolved

## paragraph:30:44 — unresolved

```text
系统为集散型综合自动化控制模式，每一个开关柜上要求配置一套完整的保护监察装置，当一台开关柜上的微机保护装置出现故障时，其它柜的保护装置仍处于正常工作状态。
```

- Handle: 23384, 23385, 23386
- 页面: EW-0002; columnScopeRef: 7360ADB34A4E0BACACD2768261FBB3E19835C07C65F9F4959F94BAE5751A249F:50708:sheet:column:6; textColumnRef: text-region:6:column
- Section: 4.7 / 23383
- SubItem: 
- 类型候选: unknown; 上游Atomic类型: unknown
- subjectScopeCandidate: unresolved; scopeSource: unresolved; 自动应用: false
- 条件/备选/引用: 当一台开关柜上的微机保护装置出现故障时
- Raw span反查: True；原文覆盖此Atomic，不等于完整Section或完整工程语义。
- 质量审计判断: 故障条件宿主可定位，但系统模式/装置配置仍未完成类型与原子化理解。
- 未决原因: instance_applicability_unresolved; semantic_split_candidate_not_rule; statement_type_unresolved

## paragraph:32:171 — unresolved

```text
系统主电源恢复后，应连锁控制其配接灯具的光源恢复原工作状态；
```

- Handle: 23513
- 页面: EW-0002; columnScopeRef: 7360ADB34A4E0BACACD2768261FBB3E19835C07C65F9F4959F94BAE5751A249F:50708:sheet:column:8; textColumnRef: text-region:8:column
- Section: 6.5.1 / 23511; 6.5 / 2350F
- SubItem: 
- 类型候选: requirement; 上游Atomic类型: requirement
- subjectScopeCandidate: unresolved; scopeSource: unresolved; 自动应用: false
- 条件/备选/引用: 
- Raw span反查: True；原文覆盖此Atomic，不等于完整Section或完整工程语义。
- 质量审计判断: 6.5和6.5.1两级引用并存，未强选父节；不是工程冲突裁决。
- 未决原因: instance_applicability_unresolved; semantic_split_candidate_not_rule; section_context_unresolved; section_completeness_unresolved

## paragraph:18:139 — unresolved

```text
并要求荧光灯，气体放电灯单灯就地补偿，功率因数不小于0.9。
```

- Handle: 23421
- 页面: EW-0002; columnScopeRef: 7360ADB34A4E0BACACD2768261FBB3E19835C07C65F9F4959F94BAE5751A249F:50708:sheet:column:6; textColumnRef: text-region:6:column
- Section: 4.9 / 2341B
- SubItem: 
- 类型候选: unknown; 上游Atomic类型: unknown
- subjectScopeCandidate: unresolved; scopeSource: unresolved; 自动应用: false
- 条件/备选/引用: 
- Raw span反查: True；原文覆盖此Atomic，不等于完整Section或完整工程语义。
- 质量审计判断: 并要求依赖上下文，原文和Section可追溯；现有切分/类型覆盖不足，保持unknown。
- 未决原因: instance_applicability_unresolved; semantic_split_candidate_not_rule; statement_type_unresolved

## paragraph:4:0 — unresolved

```text
2.1.建设单位提供的有关部门（如：供电部门、消防部门、通信部门、公安部门等）认定的工程设计资料。
```

- Handle: 232EF
- 页面: EW-0002; columnScopeRef: 7360ADB34A4E0BACACD2768261FBB3E19835C07C65F9F4959F94BAE5751A249F:50708:sheet:column:1; textColumnRef: text-region:1:column
- Section: 2.1 / 232EF
- SubItem: 
- 类型候选: unknown; 上游Atomic类型: requirement
- subjectScopeCandidate: unresolved; scopeSource: unresolved; 自动应用: false
- 条件/备选/引用: 
- Raw span反查: True；原文覆盖此Atomic，不等于完整Section或完整工程语义。
- 质量审计判断: 建设/设计资料不是要求谓词；括号中的如：不作为标题scope。
- 未决原因: instance_applicability_unresolved; semantic_split_candidate_not_rule; statement_type_unresolved; atomic_type_signal_only

## paragraph:3:0 — unresolved

```text
2.3.相关专业提供给本专业的工程设计资料；
```

- Handle: 232F6
- 页面: EW-0002; columnScopeRef: 7360ADB34A4E0BACACD2768261FBB3E19835C07C65F9F4959F94BAE5751A249F:50708:sheet:column:1; textColumnRef: text-region:1:column
- Section: 2.3 / 232F6
- SubItem: 
- 类型候选: unknown; 上游Atomic类型: requirement
- subjectScopeCandidate: unresolved; scopeSource: unresolved; 自动应用: false
- 条件/备选/引用: 
- Raw span反查: True；原文覆盖此Atomic，不等于完整Section或完整工程语义。
- 质量审计判断: 设计资料中的设不作为独立设置要求；Atomic原判与DesignStatement降级结果均保留。
- 未决原因: instance_applicability_unresolved; semantic_split_candidate_not_rule; statement_type_unresolved; atomic_type_signal_only; section_completeness_unresolved

## paragraph:5:0 — unresolved

```text
2.2.客户设计任务书及设计要求；
```

- Handle: 232EE
- 页面: EW-0002; columnScopeRef: 7360ADB34A4E0BACACD2768261FBB3E19835C07C65F9F4959F94BAE5751A249F:50708:sheet:column:1; textColumnRef: text-region:1:column
- Section: 2.2 / 232EE
- SubItem: 
- 类型候选: unknown; 上游Atomic类型: requirement
- subjectScopeCandidate: unresolved; scopeSource: unresolved; 自动应用: false
- 条件/备选/引用: 
- Raw span反查: True；原文覆盖此Atomic，不等于完整Section或完整工程语义。
- 质量审计判断: 设计任务书条目未被强当工程要求；下一步可作为候选来源条目评估，当前不扩类型。
- 未决原因: instance_applicability_unresolved; semantic_split_candidate_not_rule; statement_type_unresolved; atomic_type_signal_only

## paragraph:25:34 — unresolved

```text
短路瞬时脱扣按躲过配电线路电动机启动的尖峰电流进行整定。
```

- Handle: 2342B, 23687
- 页面: EW-0002; columnScopeRef: 7360ADB34A4E0BACACD2768261FBB3E19835C07C65F9F4959F94BAE5751A249F:50708:sheet:column:7; textColumnRef: text-region:7:column
- Section: 5.4 / 2342B
- SubItem: 
- 类型候选: unknown; 上游Atomic类型: unknown
- subjectScopeCandidate: 线路末端电动机负荷; scopeSource: hierarchy; 自动应用: false
- 条件/备选/引用: 
- Raw span反查: True；原文覆盖此Atomic，不等于完整Section或完整工程语义。
- 质量审计判断: 整定声明原文保存，当前类型仍unknown；只继承线路末端电动机负荷局部标题候选，未自动整定。
- 未决原因: instance_applicability_unresolved; semantic_split_candidate_not_rule; statement_type_unresolved

## 审计结论

未见跨页、scope扩大或错误跨Atomic挂接。保留了类型粗分、标题/子项混合Atomic、Section多级引用及指代依赖等缺口。另对Golden全部三条声明、唯一Alternative及Purpose做了专项检查。声明完整度不是读取顺序置信度；所有候选仍禁止自动应用到工程对象。
