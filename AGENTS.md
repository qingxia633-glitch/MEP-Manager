# MEP-Manager 项目开发入口

适用于本仓库及其子目录。开始代码分析、模块设计、实现、修复、迁移或 Review 前，必须读取并应用 [mep-contract-development](.agents/skills/mep-contract-development/SKILL.md)。若运行环境未自动发现 Skill，直接读取该文件并按其执行；不能把未加载当作已应用。

- 先检查实际 checkout、HEAD、工作区改动及相关源码/证据；历史聊天和测试成绩只作线索。
- 每个新模块先写 Contract / Invariant / Failure / Acceptance；Bug 先复现，Review finding 先归纳根因再设计修复。
- 执行入口独立验收不可信输入；缺证据、冲突或适用条件不明时 fail closed，禁止默认补齐或伪造批准。
- 测试依据独立契约和证据判定正确性；禁止为了恢复绿灯修改 expected、历史 fixture 或 frozen 数据。
- 实现完成必须按 Skill 跑对应 current-contract、adversarial、Test 15 和冻结哈希回归；未执行项明确报告，不得当作通过。
- 原始 CAD/私有证据保持只读。仅修改任务所需文件，保留已有工作；本规则不授予提交、推送、发布评论、签发净量或修改原图的权限。

显式调用：`$mep-contract-development`，或“先读取 AGENTS.md 及其引用的 SKILL.md，再处理本任务”。

Codex 从本仓库或子目录启动的新任务应读取此入口。普通 ChatGPT 对话不保证能读取本机仓库：需提供这两个文件并明确要求遵守。仅粘贴文件路径或引用旧聊天不等于已加载规则。
