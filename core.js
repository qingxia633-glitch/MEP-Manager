(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.MEP = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const SYSTEMS = ['给水', '排水', '强电', '弱电', '消防', '其他'];
  const UNITS = ['m', '个', '套', '台', '处', '根', '节', '只', 'kg'];
  function number(value, label, min = 0, max = 1e9) {
    if (value === '' || value === null || typeof value === 'boolean' || !Number.isFinite(Number(value))) throw new Error(label + '请填写有效数字');
    const n = Number(value);
    if (n < min || n > max) throw new Error(label + '应在 ' + min + ' 到 ' + max + ' 之间');
    return n;
  }
  function required(value, label, max = 120) {
    if (typeof value !== 'string' || !value.trim() || value.trim().length > max) throw new Error(label + '不能为空，且最多 ' + max + ' 字');
    return value.trim();
  }
  function distance(points) {
    return points.slice(1).reduce((sum, p, i) => sum + (p.breakBefore ? 0 : Math.hypot(p.x - points[i].x, p.y - points[i].y)), 0);
  }
  function calibrate(points, realMeters) {
    if (points.length !== 2 || distance(points) < 1) throw new Error('请选择两个不同的标定点');
    return number(realMeters, '实际长度', 0.001, 1e6) / distance(points);
  }
  function calculate(item) {
    const base = number(item.base, '基础数量');
    const copies = number(item.copies, '重复份数', 1, 100000);
    if (!Number.isInteger(copies)) throw new Error('重复份数需要填写整数');
    const extra = number(item.extra, '补充数量');
    const allowance = number(item.allowance, '备料损耗率', 0, 100);
    const price = number(item.price, '单价', 0, 1e8);
    const quantity = base * copies + extra;
    if (quantity > 1e9) throw new Error('合计数量过大，请拆分记录');
    const purchase = quantity * (1 + allowance / 100);
    if (purchase * price > 1e12) throw new Error('单笔估算金额过大，请拆分记录');
    return { quantity, purchase, cost: Math.round((purchase * price + Number.EPSILON) * 100) / 100 };
  }
  function validateItem(item) {
    required(item.id, '记录编号'); required(item.name, '材料或设备名称');
    if (!SYSTEMS.includes(item.system) || !UNITS.includes(item.unit)) throw new Error('请选择有效的专业和单位');
    for (const key of ['spec', 'location', 'note']) if (typeof item[key] !== 'string' || item[key].length > 500) throw new Error('记录文字格式不正确');
    calculate(item);
    return item;
  }
  function summarize(items) {
    const groups = new Map();
    for (const item of items) {
      const key = JSON.stringify([item.system, item.name.trim(), item.spec.trim(), item.unit]);
      if (!groups.has(key)) groups.set(key, { system: item.system, name: item.name.trim(), spec: item.spec.trim(), unit: item.unit, quantity: 0, purchase: 0, cost: 0, count: 0 });
      const group = groups.get(key), result = calculate(item);
      group.quantity += result.quantity; group.purchase += result.purchase;
      group.cost = Math.round((group.cost + result.cost) * 100) / 100; group.count++;
    }
    return [...groups.values()];
  }
  function csv(rows) {
    return '\uFEFF' + rows.map(row => row.map(value => {
      let s = String(value ?? '');
      if (/^[\s]*[=+@-]/.test(s)) s = "'" + s;
      return '"' + s.replace(/"/g, '""') + '"';
    }).join(',')).join('\r\n');
  }
  function checkPoints(points, drawing, min) {
    if (!Array.isArray(points) || points.length < min || points.length > 20000) throw new Error('图纸测量点格式不正确');
    for (const p of points) { if(p.breakBefore!==undefined&&typeof p.breakBefore!=='boolean')throw Error('支路标记格式不正确'); strictNumber(p.x, '测量点横坐标', 0, drawing.width); strictNumber(p.y, '测量点纵坐标', 0, drawing.height); }
  }
  function strictNumber(value, label, min = 0, max = 1e9) {
    if (typeof value !== 'number') throw new Error(label + '必须为数值');
    return number(value, label, min, max);
  }
  function validateBackup(data) {
    if (!data || data.version !== 1 || !Array.isArray(data.projects) || data.projects.length > 200) throw new Error('不是本软件支持的备份文件');
    const ids = new Set();
    function unique(id) { required(id, '编号'); if (ids.has(id)) throw new Error('备份中有重复编号'); ids.add(id); }
    for (const project of data.projects) {
      unique(project.id); required(project.name, '项目名称');
      if (typeof project.location !== 'string' || project.location.length > 500) throw new Error('项目位置格式不正确');
      if (!Array.isArray(project.items) || !Array.isArray(project.drawings) || !Array.isArray(project.cash) || project.items.length > 50000 || project.drawings.length > 100 || project.cash.length > 50000) throw new Error('项目数据格式或数量不正确');
      for (const drawing of project.drawings) {
        unique(drawing.id); required(drawing.name, '图纸名称');
        strictNumber(drawing.width, '图纸宽度', 1, 16000); strictNumber(drawing.height, '图纸高度', 1, 16000);
        if (typeof drawing.data !== 'string' || drawing.data.length > 30e6 || !/^data:image\/(png|jpeg|webp);base64,[A-Za-z0-9+/=]+$/.test(drawing.data)) throw new Error('备份包含不支持的图纸图片');
        if(drawing.cad?.geometryVersion===1){const segs=drawing.cad.segments;if(!Array.isArray(segs)||segs.length>1000000)throw Error('CAD线段数据格式不正确');for(const s of segs){if(!s||![s.a,s.b].every(p=>Array.isArray(p)&&p.length===2&&p.every(n=>typeof n==='number'&&Number.isFinite(n)&&Math.abs(n)<1e12))||!Array.isArray(s.clips)||s.clips.length>32||s.clips.some(c=>!Array.isArray(c)||c.length<3||c.length>10000||c.some(p=>!Array.isArray(p)||p.length!==2||p.some(n=>!Number.isFinite(n)))))throw Error('CAD线段坐标格式不正确');}}
        if (drawing.scale !== null) strictNumber(drawing.scale, '图纸比例', 1e-12, 1e6);
      }
      for (const item of project.items) {
        unique(item.id); validateItem(item);
        for (const key of ['base', 'copies', 'extra', 'allowance', 'price']) strictNumber(item[key], '工程量数值');
        if (item.source) {
          const drawing = project.drawings.find(d => d.id === item.source.drawingId);
          if (!drawing || !['length', 'count'].includes(item.source.kind)) throw new Error('工程量的图纸来源已丢失');
          checkPoints(item.source.points, drawing, item.source.kind === 'length' ? 2 : 1);
          let expected;
          if (item.source.kind === 'length') {
            strictNumber(item.source.scale, '测量比例', 1e-12, 1e6);
            if (item.unit !== 'm') throw new Error('长度测量必须使用米');
            expected = distance(item.source.points) * item.source.scale;
          } else expected = item.source.points.length;
          if (Math.abs(expected - item.base) > Math.max(1e-6, expected * 1e-9)) throw new Error('工程量与图纸测量点不一致');
        }
      }
      for (const entry of project.cash) {
        unique(entry.id); required(entry.name, '收支说明');
        if (!['income', 'expense'].includes(entry.type) || !/^\d{4}-\d{2}-\d{2}$/.test(entry.date) || Number.isNaN(Date.parse(entry.date))) throw new Error('收支记录格式不正确');
        strictNumber(entry.amount, '收支金额', 0.01, 1e9);
      }
    }
    return data;
  }
  return { SYSTEMS, UNITS, number, required, distance, calibrate, calculate, validateItem, summarize, csv, validateBackup };
});
