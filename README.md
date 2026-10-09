# MEP-Manager

## 开发规则与 AI 使用入口

开发、修复和 Review 前先读取 [AGENTS.md](AGENTS.md)，再应用项目 Skill [mep-contract-development](.agents/skills/mep-contract-development/SKILL.md)。规则涵盖证据先行、Contract/Invariant/Failure/Acceptance、执行入口独立准入、反例测试、current/legacy 分层及冻结回归。

Codex 可显式调用 `$mep-contract-development`；从本仓库启动的新任务通过 AGENTS.md 进入该流程。普通 ChatGPT 对话需提供 AGENTS.md 和 SKILL.md 的内容或可读取文件，并明确要求应用，不能假定本机文件自动同步。文件尚未提交时仅在当前 checkout 持久化；其他 checkout 需包含同样规则。

水电安装工程管理与算量工具

## 项目目标

这个项目用于建筑机电安装工程的日常管理，主要服务于水电安装施工、工程量计算、材料管理和人工工资管理。

## 计划功能

- 水电安装工程量计算
- 工人工资及计件管理
- 材料采购、入库和使用记录
- 电线电缆价格记录与成本分析
- 项目收入与支出管理
- 工程数据统计与报表
- CAD 图纸及工程量数据处理

## 后续计划

逐步加入自动算量和 AI 辅助功能，提高水电安装工程的算量及现场管理效率。
