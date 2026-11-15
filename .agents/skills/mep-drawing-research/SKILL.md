---
name: mep-drawing-research
description: 在 MEP-Manager 正式设计新的 CAD/工程图纸语义或调查未知 AutoCAD、DXF、天正行为前，执行轻量 Research Gate，复用已有研究并明确证据边界和最小安全方向。已知契约内的 bug、测试、重构及已有当前明确研究结论的主题不重复完整研究。
---

# MEP Drawing Research

只负责研究真实 CAD 机制、标准与成熟做法，确定 evidence、边界和最小安全方向；不复制完整开发流程，也不授予修改原图、批准规则或签发数量的权限。随后使用 [mep-contract-development](../mep-contract-development/SKILL.md) 定义 Contract / Invariant / Failure / Acceptance，实施、测试和回归。

## 触发与跳过

正式设计前，以下新语义或未知行为进入 Research Gate：
- 新 CAD / DXF object、CAD 对象继承或引用关系；未知 AutoCAD / DXF / Tianzheng 行为。
- 新 Drawing / Sheet / Layout / View 语义，drawing registry、drawing identity / title block 解释。
- 新 Xref、cross-sheet relation、Field / ATTRIB / TABLE / Leader / MLeader 语义。
- 新 Note / Scope、Circuit / Network Trace 或其他工程图纸语义。

已有 contract 内的小 bug、regression fix、测试补充、parser 已知契约修复、refactor、Git / PR / merge、文档更新、benchmark runner 修改，默认直接进入 mep-contract-development；只有发现影响本任务的未知行为才补研究。已有当前且明确结论的重复主题复用结论，不重复完整 Research Gate。

## 先复用，再补缺口

1. 先检查仓库中的官方机制结论、research note、contract 文档、真实 project evidence 和已验证 benchmark；核对来源、版本、适用范围与当前问题。
2. 足够时标记 `reuse existing research`，引用已有结论及路径，不重复搜索。
3. 只有缺少会影响架构或正确性的关键事实时才补外部研究。需核实的时效、版本或适用性可以是关键缺口；只查该缺口，不扩成全主题调研。

需要外部研究时，按问题适用性优先使用：中国国家/行业标准及住建等权威资料 → Autodesk 官方 DXF/API/AutoCAD 文档 → 成熟工程软件公开做法 → 必要时高质量论文 → 当前真实项目 evidence 对照。产品实践优先引用厂商一手资料，可参考 Autodesk Build / Forma、Procore、Bluebeam 等 drawing management、takeoff、BIM 平台。

关键结论保留可复核来源（链接或本地路径、版本/条款/对象定位），明确资料是否实际取得；无法取得的关键事实保持未知。国外标准、产品做法和论文仅是 architecture / product / research reference，不能自动升级为中国工程规则。Rule Baseline 仍走现有治理流程。

## 来源分类

每条关键结论标明来源类别，不混写事实、批准和推断：
- A：中国权威标准 / authority。
- B：Autodesk native CAD mechanism。
- C：mature-product architecture practice。
- D：academic/research method。
- E：project-specific drawing evidence。
- F：human-confirmed project decision。
- G：hypothesis / model inference。

`B / C / D != engineering_rule`；标准或项目材料的存在也不替代适用性判断和项目批准。

## 证据与语义边界

- 采集可靠性默认偏好：native CAD evidence > explicit handle/object relation > Field / ATTRIB / TABLE / Leader / Xref relation > document structure / geometry > text matching > spatial proximity > OCR / screenshot inference。这是 evidence acquisition 偏好，不是通用工程语义优先级；对象关系不自动证明工程含义。
- 原生 DWG 优先读取 DXF、Handle、Field、TABLE、ATTRIB、Leader/MLeader、Xref、Block、Layout、geometry。只有原生对象确实无法取得才考虑 OCR / screenshot / visual inference；视觉结果单独标记来源，不能冒充 native evidence。
- 跨图保持 Drawing Registry → Explicit Reference → Target Identity → Cross-Sheet Evidence → Entity Resolution，不跳过 Drawing/Sheet identity。same text、same S、same equipment number、same panel name、same color、same linetype、same layer、same filename、same nearby geometry 均不能单独建立跨图绑定，最多为 candidate；多候选必须 ambiguous，禁止自动取第一个。
- 区分 DWG Drawing File、ModelSpace、Layout / PaperSpace、Sheet、View、Viewport。缺证据保持 unresolved；不能因当前仅支持 ModelSpace 而把 drawing_ref 当成 sheet_id。
- Xref 关系至少保留 host drawing → xref instance → referenced drawing → attach / overlay → transform → nested path，不能简化成无实例身份的“A references B”。
- 保持 note observed != note classified != scope established != applicability approved。“未注明”“余同”“其余同上”“详见”不能只凭关键词传播。
- 颜色、线型、线宽、图层先作为 contextual / supporting evidence：same color != same circuit；same linetype != same circuit；same layer != same system；same style != same route ownership。

## 最小输出与交接

默认只输出以下五项的简洁 brief，可引用已有研究，不要求另写报告文件：
- **Native mechanism**：CAD 中真实对象/关系是什么；当前 exporter 实际能看到什么。
- **Authoritative evidence**：相关标准/官方机制及来源分类、版本和适用性；明确未取得的关键资料。
- **Current project evidence**：当前仓库、真实项目 evidence、benchmark 已有结论；哪些关系显式、哪些只是推断。
- **Known boundary**：未解决项、冲突、采集范围；判断错误会污染哪一层。
- **Minimum safe next step**：最小、安全、可验证的第一版及剩余前提，然后交给 mep-contract-development。

只有真正未知、冲突或高风险问题才按需展开。真实 CAD 对象、exporter 可见范围、显式证据与推断、错误影响层、最小可验证版本这五个问题未清楚时，不直接做大型实现；保留 unresolved 并指出最小取证步骤。普通 bug/test/refactor 不因此每次执行长篇 Research。
