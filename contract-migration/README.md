# Source-backed input contract migration

本目录是当前项目的独立输入迁移和验收工具，不是通用 Resolver，也不会签发数量。

## 保存边界

- 原始 JSON、fixture、expected、frozen quantity 保持原始字节。
- 新输入保存为 `outputs/source-backed-contract-migration-20261008/fixtures/` 下的包装对象。
- `fixture` 是执行输入；外层保存 migration_id、原/新版本、逐字段补证来源、时间、工具版本及 hash。
- 内部 QuantityBuildPlan 仍遵守 schema 0.2；`input-contract/2` 是输入证据契约版本，不冒充新 schema。
- 运行 `migrate.py` 使用独占创建；已有输出不会覆盖。

## 来源边界

Golden 的 `parent_path=[]` 来自原始报告的 ModelSpaceTopLevelAllLayers 声明与唯一 13CF5 顶层记录。
项目身份来自原审核 Gate bundle；edge scope 来自原 measurement_scope.kind。
已有 geometry/height evidence 保留其原始状态，并验证引用文件 hash 和 JSON pointer。
本轮没有创造新的高度 supported 证据，也没有把任一合成样本迁移为真实项目正样本。
无来源合成输入保持 legacy_incomplete；不能因为其中写了 planar 就忽略其端部 transition 的证据缺口。

## 测试版本分离

1. 原套件完整原样运行，保留原始失败/错误和 traceback；不改旧 expected。
2. 5 个可合法补证的新输入走同一现有 Gate/Eligibility/Builder。
3. SourceBackedEligibility 和 SourceBackedBuilder 复用原断言，只在新测试类中装载有来源的 v2 输入。
4. 每个历史契约不匹配都有独立可执行阻断检查；合法迁移者还重跑原正向断言。
5. classification-catalog.json 只列已检查的 50 项。出现任何新失败或分类外失败，验收必须失败。
6. 无法补齐的合成输入保留并继续验证 fail-closed，不把其旧正向断言伪报为通过。

原始结果与新契约结果分开报告。原始八模块不是 224/224 绿灯；其 35 项旧契约不匹配和 Safety
15 项不匹配保留为原始记录。新验收总数由未受影响的历史通过项、新版本正/负向测试以及
Post-Hardening 18 项组成，不删除任何旧测试文件。

## 执行

- `python -B contract-migration/migrate.py`：首次生成源支持输入，后续拒绝覆盖。
- `python -B -m unittest discover -s contract-migration/tests -v`：迁移、原始拒绝、源支持重放、分类覆盖。
- `run_suite.py`：保存真实 unittest case 结果；失败依然返回非零，不修改测试语义。

本轮所有数量求值仅用于内存中的 replay/native test；不输出正式数量文件，不登记 registry。
