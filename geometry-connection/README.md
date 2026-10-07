# GeometryConnectionResolver v0.1

独立 Python 3 标准库模块，仅输出二维几何连接证据。无 AutoCAD 调用，无电气语义或工程量推断。
遵守 `outputs/fire-alarm-project-candidate-rules-20261005/geometry-connection-evidence-rules.json`；容差为必填参数，不内置项目的 0.001。

## API / CLI

`DrawingContext.from_reports(snapshot, probes)` 从 MEPFULLREAD 的 INSERT 和一层 probe 的原始 DXF 自动建立定义表，不要求调用方提供 POINT 坐标。调用方负责提供同一图纸版本的取证集合，禁止混入其他 DWG 的同名块。

`resolve_connection(edge_handle, edge_endpoint, target_insert_handle, context, connection_xy_tolerance, max_depth=16)` 返回连接证据。`edge_endpoint` 为真实线路端点 WCS XYZ；不是设备插入点。

```powershell
python geometry-connection/resolve.py --snapshot <report.txt> --probe <probe.txt> --probe <child-probe.txt> --edge 14147 --endpoint-index -1 --target 13017 --tolerance 0.001 --output <new-evidence.json>
python geometry-connection/tests/test_resolver.py
pwsh -NoProfile -File model-core/tests/Run-Regressions.ps1
```

## 变换与状态

每一级使用 `insertion + Rz(rotation) * scale * (point - definitionBasePoint)`，从内向外复合；支持XYZ缩放、负尺度、任意Z轴旋转、非零基点及嵌套。保留每级实例handle、定义名、参数及叶实体路径。只支持 normal=(0,0,1)；其他extrusion显式 unresolved，不忽略。

- POINT、LINE端点、开放直线多段线首尾：容差内 supported（仅几何锚点，非已确认电气端子）。
- 线段中部、闭合边界、圆周、保守线宽包络：partial。
- 未取得定义、未知动态状态、代理/不支持实体、曲线多段线、异常变换、嵌套循环/深度上限：阻止 rejected。已恢复的明确锚点仍可独立支持局部接触。
- 完整有效几何全部分离：rejected，仅否定直接二维接触。
- 只有文字或空定义：unresolved。忽略ATTRIB/ATTDEF作为锚点，保留报告来源，不生成设备角色；也不使用ATTDEF默认值覆盖实例属性。
- Z参与变换及原始XYZ残差，未赋物理标高语义，不影响XY接触分类。

## 支持边界

报告适配器：POINT、LINE、直线LWPOLYLINE、圆、直接INSERT及嵌套；ATTDEF/TEXT等不计连接几何。圆要求组合变换各级XY等尺度（可镜像）。多段线宽度按最大尺度构造保守包络，因此包络内仅partial。

规范化Context可接受已完整恢复VERTEX序列的直线POLYLINE；当前报告适配器不自行恢复legacy POLYLINE/VERTEX。ARC、bulge、SPLINE、ELLIPSE、SOLID、TRACE、HATCH、proxy、数组INSERT、非标准normal、动态可见性尚未支持，均显式降级。不以bbox代替真实几何。

probe中的ATTDEF空范围错误不影响其他完整原始几何；其他几何读取错误阻止完整性判定。报告getter的bbox不用于距离计算。

## 验收

专项测试包含原报告5个正向接触、1个真实拒绝、1个历史缺定义状态；合成测试覆盖旋转、镜像、非零基点、嵌套、文字/插入点误吸附、闭合多段线、宽度、Z语义、动态块及未知几何。真实报告仅只读，未复制预先转换的WCS POINT作为输入。
全量回归使用原有51套入口（项目称 Test 15），不修改历史expected。
