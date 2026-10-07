# Block Text Index

独立的只读 AutoCAD Windows 2021+ 诊断入口，不依赖或修改主采集器。

## 一次导出

在目标 DWG 中 APPLOAD `BlockTextIndex.lsp`，运行 `MEPBLOCKTEXTINDEX`，将报告保存到新目录中的 `block-text-index.txt`。已有同名文件会被保护，不覆盖。

一次运行枚举当前数据库的 BlockTable：

- 本地块定义：直接内部 TEXT、MTEXT、ATTDEF 及 INSERT 引用；不读取其他内部几何。
- ModelSpace / PaperSpace：只登记顶层 INSERT 引用，分别标记来源。
- XREF / 外部依赖块：登记名称、原始标志、路径和未扫描状态；不打开或展开外部 DWG。
- 每个定义仅遍历一次；遇到内部 INSERT 仅登记引用，不递归展开。

没有 EXPLODE、DWG 写入、动态状态切换、对象识别或工程量计算。定义文字存在不表示实例可见，引用可达不表示工程归属。

## 报告与查询

报告版本 `1.0`，模式 `BlockTableDirectTextAndReferences`。Block 记录保留实际块名、记录 Handle、flags、基点、XREF 路径和读取状态。Text 记录保留原文、类型、内部 Handle、源块、图层、原始坐标、DXF60、ATTDEF 标志/tag/prompt/default 及有序 DXF 文本片段。Reference 记录保留父块、实际引用块名、内部 INSERT Handle 和来源空间。

坐标保持原始 DXF 局部/OCS 语义，不变换到实例 WCS；MTEXT 的 DXF11 是方向。未导出的 flags 为 nil，不伪造 CAD 默认字段。MTEXT 合并 DXF3/1 文本片段并保留原片段；多行 ATTDEF 的嵌入数据保留在 RawDXF，不宣称完整语义恢复。

统计区分别记录 BlockTable 总记录数、排除布局容器后的块定义数（包含未扫描外部定义）、含文字块数、TEXT/MTEXT/ATTDEF 数、引用数、未扫描外部块数、代理计数和 ReadErrorCount。错误或截断报告仍可人工检查；查询器拒绝用其证明文字不存在。

PowerShell 查询只读文件，结果写到控制台：

```powershell
./block-text-index/Search-BlockText.ps1 -Report '<导出目录>/block-text-index.txt' -Query @('QWB1','QWB3','QWB4','QWB5','QWB8')
```

这些标识只是查询参数，没有进入采集或关联规则。匹配方式是原始 Text_RAW 的不区分大小写字面包含，不执行正则或 CAD 格式解释。重复文字不去重。结果包含直接父引用、循环安全的反向引用图及可达顶层 INSERT；不生成实例绑定。所有文本、引用及查询结果携带文件 SHA-256 / 来源 DWG，保留新快照身份。

未找到时仅返回 `not_found_in_readable_block_definition_text`，不能据此断言 DWG 没有相应配置。代理/TABLE、外部 DWG、实例附着 ATTRIB、动态可见性求值仍不在本模块范围；顶层文字和实例属性继续使用原快照。

`LISPSYS=0` 时按系统 ANSI 导出，查询需传 `-Encoding Default`；其他情况导出 UTF-8 BOM，默认按 UTF-8 读取。未在程序中修改 LISPSYS。

## 验证

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File block-text-index/tests/Test-BlockTextIndex.ps1
```

测试使用合成报告检查读取、溯源、计数、重复实体、循环引用、隐藏属性、错误拒绝与只读静态约束。测试不能替代 AutoCAD 实际导出验收。

API 依据：[IsXRef / IsLayout](https://help.autodesk.com/cloudhelp/2026/DEU/AutoCAD-ActiveX-Reference/files/GUID-2DB912E6-401E-4859-8D71-CAF474483D91.htm)、[MTEXT DXF 文本片段](https://help.autodesk.com/cloudhelp/2015/ENU/AutoCAD-DXF/files/GUID-5E5DB93B-F8D3-4433-ADF7-E92E250D2BAB.htm)。具体 AutoCAD 2021 运行兼容性仍需真实导出验证。
