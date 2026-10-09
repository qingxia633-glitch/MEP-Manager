---
name: mep-contract-development
description: 在 MEP-Manager 中进行模块设计、代码分析、实现、Bug 修复、契约迁移及 Review 时，按证据、信任边界和不变量驱动开发，并验证独立执行准入与冻结回归。纯文档修改只做对应文档验证，不启动全量业务加固。
---

# MEP-Manager 契约驱动开发

## 适用范围与开始条件

本 Skill 是项目开发方法，不是当前代码安全性已经通过的证明，也不自动开启新一轮 Review。遵守用户当前任务范围；明确只读的任务仅调查和报告，不修复、不保存原图、不签发净量。

1. 确认仓库根目录、HEAD、已有改动以及相关指令。未找到目标 checkout 时停止并说明，不能换用同名旧项目。
2. 先打开相关调用入口、实现、schema、测试和原始证据，再下结论。报告区分已验证事实、推断、冲突和未解决事项，保留文件/函数/对象身份等可复核引用。旧报告和通过数量不能代替当前验证。
3. 影响工程语义、范围或验收标准的歧义先向用户澄清；等待期间仅推进不依赖该答案的只读工作。已确认的范围不重复请求批准。

## 先定义，再实现

每个新模块在模块说明或本次设计记录中先写以下四项，再实现。既有模块修复可用简短记录补充受影响部分，无需另建庞大文档系统。

| 项目 | 必须说清楚的内容 |
| --- | --- |
| Contract | 输入/输出及版本、职责与非职责、所有调用入口、外部或持久化数据的信任边界、依据来源 |
| Invariant | 哪些关系始终成立；用可观测结果表达，注明在哪个边界强制执行 |
| Failure | 缺失、未知、冲突、伪造、跨实例、版本不兼容时如何拒绝；阻断状态及禁止产生的副作用 |
| Acceptance | 独立判定依据、合法正例、adversarial matrix、回归入口、冻结基线和明确的完成标准 |

先画清相关边界：CAD/外部 evidence → discovery → semantic approval → eligibility → 不可信 QuantityBuildPlan → Builder → DesignNetQuantity。不能假设上游正常调用路径是唯一入口。

区分局部 bug 与 invariant 缺失：若已有规则明确、仅局部实现偏离，做最小修复；若多个 finding 都源于相同信任假设、入口漏验或证据覆盖缺口，先归纳共同根因，修复实际边界并验证同类路径。不要把每个症状变成一个孤立 if，也不要借机改造无关模块。

## 执行准入不变量

- Builder/其他执行入口将所有输入视为不可信，包括手工 JSON、持久化计划、声称 eligible 或 generation_allowed 的对象。执行算术及写出正式结果前独立验收；可调用共享纯验证器，不能因上游调用过而跳过。验证器不得补字段、推断工程语义或创造证据。
- candidate 不等于 approved。Gate 必须明确通过，批准角色、accepted evidence、context/provenance 与计划完整对象身份一致。身份按当前契约包含 project、drawing/snapshot、完整 parent_path、Handle、segment/scope；相关 ATTRIB 保留 owner。不能仅凭同 Handle、图层、颜色、邻近文字或图例绑定对象。
- 缺失、unknown、partial、conflicting、失败或跨实例证据不得静默升级为 supported，不得生成正式数量。上下文证据与直接对象/适用规则绑定分开报告。
- 原始几何、source unit、经审核的换算记录、准确因子、转换结果、base_path 与 execution contract 必须贯通验证。字段彼此自洽不证明物理换算正确。SI 单位换算与 CAD drawing scale 分开；使用准确 Decimal，不进行中间舍入。3D 模式按批准契约验收，不把 Builder 扩展成 CAD 推理器。
- 所有 admission-critical evidence（包括嵌套高度、豁免规则和 semantic evidence）按显式证据覆盖范围校验 assumptions、provenance、identity 和 applicability。必需引用必须存在、已批准、有来源、同身份且条件满足；新增证据类型同步检查准入及 replay 覆盖。
- 对于 admission-critical evidence，不允许只检查字段存在/容器非空；必须定义 evidence authorization、provenance structure、dependency policy。
- replay 必须保留并比较影响准入的证据。数值相等不等于证据契约完整；内容哈希只能检测内容一致性，不证明外部来源或审核人真实性。未实现的身份认证不得声称已提供，也不为假想需求擅自增加签名系统。

## 测试与 Review 修复

Bug 先写最小复现并运行，确认因目标缺陷失败，再修复；新功能先写契约及独立正/负向单元测试。测试期望来自工程规则、准确换算或可追溯源证据，不从待测实现复制答案。测试不得仅断言内部实现细节。

实现前按实际边界列出 adversarial matrix：入口、被破坏的不变量、输入变体、预期拒绝/输出、依据、测试位置。至少评估下列维度；不适用项说明原因，不能机械为所有内部函数堆校验。

| 维度 | 示例反例与断言 |
| --- | --- |
| Gate | missing、failed、conflicting、false flags、角色错配；直接调用 Builder 仍拒绝 |
| Identity | 同 Handle 不同 parent_path/owner、不同 project/drawing/segment；拒绝串证 |
| Geometry/unit | raw=10 mm、factor=1、converted/base=10 m，即使重算内容哈希仍拒绝；另测缺 conversion、正确因子错误结果、正确结果错误因子及 scale 混用 |
| Assumptions/applicability | height 引用不存在假设、未批准假设、缺 provenance、外来身份、条件不满足；不得 built |
| Version/replay | legacy 冒充 current、手工 JSON 绕过上游、修改准入证据但保留相同数值；拒绝或明确标为证据不完整 |
| 正例/副作用 | 同契约合法输入成功，拒绝路径无正式数量/registry 写入；原输入与冻结对象不变 |

边界反例必须直接调用执行入口，不能只证明 Eligibility 拒绝。变异测试应从明确标识的 synthetic 正例复制；除专门测试哈希损坏外，重算封装哈希以测试深层验证，不能只因外层哈希失败就宣称准入正确。合成测试不是项目已批准证据。

Review finding 先记录 severity、入口、最小复现、实际/预期结果、影响、测试缺口和架构根因，再按根因聚合修复。只做需求所需的共享校验；不为 hypothetical future 建通用框架。复审次数不等于质量；达到本轮约定退出条件后结束该轮，非阻塞项入 backlog，不擅自无限复审或宣布未经验证的 Critical/High 为零。

## Current 与 legacy 分层

当前仓库的 QuantityBuildPlan v0.3 是 executable contract，v0.2 是 legacy；这不是 Builder 自身 VERSION 字段。后续版本以实际 schema/入口和明确迁移记录为准。

- 不静默改写旧 schema 的 required 语义，不把旧对象补默认字段后冒充新契约。
- 禁止通过改 expected、历史 fixture、冻结对象、补空身份/默认高度或伪造 Gate/geometry evidence 恢复绿灯。
- 必需迁移只能创建独立新对象，逐字段记录真实来源、定位、hash、版本及推导；无来源则保持 legacy_incomplete/blocked。冻结 Golden 不回填、不重签。
- current 正负向通过、原始 legacy 失败、intentional legacy rejection、missing real source evidence 分开统计；保留原始失败和 traceback。新出现的未分类失败必须调查，不能用旧分类清单吞掉。

## 实现后验收与回归入口

从仓库根目录执行，先确认 Python、依赖及 PowerShell 7。以下为当前可定位入口，不是过去成绩的保证；运行前读取脚本的参数、数据依赖和写入行为，保存本次日志及退出码。

- 公共 Builder-direct adversarial：`python -B -m unittest discover -s post-hardening-pass3/tests -v`。
- current Pass 2 与私有来源/冻结检查：`post-hardening-pass3/current_checks.py`；Builder、Unified Safety、source-backed current：`post-hardening-pass3/current_suites.py`。两者需一个新的结果文件名参数，并独占创建到各自 OUT 目录；先核对依赖来源，不覆盖既有结果。
- 对应模块及八模块回归：定位各模块 tests；`contract-migration/run_suite.py` 接收测试目录及新的结果 JSON 路径，保存真实原始结果。结合 current 适配入口运行；legacy 的非零退出不能算通过。
- Test 15：`pwsh -NoProfile -File model-core/tests/Run-Regressions.ps1`；历史为 51 套，不将这个数字当成永久目标，报告本次实际结果。
- 核对 private Golden、真实 report/ATTRIB identity，以及 frozen JSON、历史测试源和 Golden DesignNetQuantity 的逐文件 SHA-256。来源范围可查 `post-hardening-pass3/current_checks.py` 及 `post-hardening-pass3/finalize.py`。必须对照改动前和已有可信冻结清单，记录清单范围、数量及差异，不能重建基线掩盖变化。
- `finalize.py` 是历史验收汇总，固定旧输出、commit 和差异集合；不能直接作为通用验收、修改其历史 expected 来迁就新任务，或把旧日志当作新运行。迁移脚本同样不是每次回归必跑的修复工具。

业务实现/修复完成前，必须运行对应 current-contract、直接入口 adversarial、Test 15 以及相关 Golden/冻结哈希检查；按受影响契约选择必要模块。涉及公共准入、身份、单位、replay 时覆盖整个受影响链和上述 current 套件。缺私有数据/依赖时说明缺项和影响，只能报告部分验证，不能造源或宣称全部验收通过。

纯规则/文档变更仅验证 Skill frontmatter、引用可达、规则一致性及 Git 差异范围，不为文档运行无关业务回归。只读 Review 依其约定范围验证并披露未执行项。

交付记录：范围/基线、已读证据、Contract/Invariants、finding 与根因（如有）、改动文件、before/after、实际命令及结果、current/legacy 分账、Test 15、冻结差异、未验证项。只报告本次有证据支持的完成状态；通过测试不等于可以自动发布或签发数量。
