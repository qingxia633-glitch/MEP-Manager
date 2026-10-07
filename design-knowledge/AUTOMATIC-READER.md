# Experimental Design Statement Reader

`Read-DesignTextSnapshot → Find-DesignStatementCandidates`不加载fixture清单、不接受验收Handle或窗口，不访问AutoCAD。输入仅为既有全图层顶层快照。

## 流程

1. 保留TEXT、MTEXT和INSERT附属ATTRIB原文、Handle、父实例、坐标、图层、原始记录与快照指纹。隐藏属性不用于正文发现；MTEXT格式当前不求值，进入ReviewItem。
2. 在长中文文本重复X对齐中估计最常见行距，以此作为布局尺度。编号必须与单位数值区分，例如数字后直接接`m`不作为段落编号。
3. 依据编号、首行/续行缩进、Y顺序、行距、标点、跨行延续线索及下一编号停止条件形成段落和阅读顺序候选。同行竞争表示保留，低置信度不拼接。
4. 按同列和连续范围组成DesignTextRegionCandidate，输出编号密度、对齐文本、图层及附近标题/图签属性候选。区域是正文列段，不等于完整图纸区域。图层不是身份结论，标题不采用最近归属。表格/图框几何当前未参与判断，明确not_evaluated。
5. 句号/分号及语言信号生成保守原子候选；条件、备选、目的可能仍只是signalCandidates，未实现完整语法理解。较短/较长阈值未决。条件性调整不自动决定作用对象或做法。
6. 引用产生原文、来源span、类型和目标名称候选。系统图和标准图集分开；三次引用可以只有两种语义类型。所有目标解析状态保持unresolved，不检索外部图集。

## 通用契约补充

- ExceptionClause：exceptionKind（exclusion/override/conditional_exception/unresolved）、triggerConditionRefs、effectStatementRefs。
- ApplicabilityCondition.kind：新增general_predicate，不枚举具体工程句子。
- CrossDrawingReference：referenceType、targetNameCandidate。sourceHandles继续由source spans派生。

## ReviewItem

多阅读顺序、边界/区域范围不确定、条件作用域、其它/其余排除集合、多个引用目标、章节编号异常和未求值格式进入复核。局部工程冲突由调用方显式提供LocalConflicts，本模块不凭正文自动推断图纸冲突。

## 用法

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File design-knowledge/Read-DesignStatementsAuto.ps1 -ReportPath local_test_data/system-t8t3-verified-snapshot-20260916/MEP-full-entity-report.txt -Summary
powershell -NoProfile -ExecutionPolicy Bypass -File design-knowledge/tests/Test-Reader.ps1
```

入口仅输出stdout，不生成结果文件。省略Summary输出完整候选与原始证据。

## 验证与限制

验收Handle只在测试中使用。通用算法在全快照输入上重新恢复两个已知段落，并接受整份记录Handle替换及整体平移/缩放测试。重复文本不合并，同行歧义不得强拼接。

这不是全项目说明理解：当前为近水平中文、多级数字编号、单一主行距假设。混合比例、旋转文字、复杂分栏、段落跨栏、无编号正文、格式化MTEXT、数字开头的非编号中文表达均可能漏检/误分。区域和段落数量是候选数，不是覆盖率或准确率。未自动生成旧fixture中完整的工程语义树，不推断阈值、安装归属、网络、Circuit或工程量。所有五项新能力为experimental。
