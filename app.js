/* MEP-Manager v0.1 — dependency-free, local-first takeoff workspace. */
(() => {
  'use strict';
  const $ = selector => document.querySelector(selector);
  const h = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const uid = () => 'm' + (globalThis.crypto?.randomUUID?.() || Date.now().toString(36) + Math.random().toString(36).slice(2));
  const fmt = (n, digits = 3) => Number(n).toLocaleString('zh-CN', { maximumFractionDigits: digits });
  const money = n => Number(n).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const unitLabel = unit => unit === 'm' ? '米' : unit;
  const dateNow = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; };
  const paths = {
    home: '<path d="M3 11 12 3l9 8M5 10v11h14V10M9 21v-8h6v8"/>',
    plan: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 10h10V3m0 7v6h8M8 15v6"/>',
    list: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6M9 12h6M9 16h4"/>',
    wallet: '<rect x="3" y="5" width="18" height="15" rx="2"/><path d="M3 8V4l14-2v3M21 11h-6v5h6M17 13.5h.1"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    arrow: '<path d="M5 12h14m-5-5 5 5-5 5"/>',
    upload: '<path d="M12 16V3m-5 5 5-5 5 5M4 16v5h16v-5"/>',
    download: '<path d="M12 3v13m-5-5 5 5 5-5M4 17v4h16v-4"/>',
    help: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 0 1 5 0c0 2-2.5 2-2.5 4M12 17h.01"/>',
    ruler: '<path d="m3 16 13-13 5 5L8 21zM12 7l2 2M8 11l2 2M4 15l2 2"/>',
    line: '<path d="M4 18 10 7l6 8 4-10"/><circle cx="4" cy="18" r="2"/><circle cx="20" cy="5" r="2"/>',
    count: '<circle cx="6" cy="6" r="3"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M15 18h6m-3-3v6"/>',
    pointer: '<path d="m5 3 14 10-7 1-4 7z"/>',
    undo: '<path d="M8 5 3 10l5 5M3 10h11a6 6 0 0 1 0 12"/>',
    check: '<path d="m4 12 5 5L20 6"/>',
    close: '<path d="m6 6 12 12M6 18 18 6"/>',
    edit: '<path d="m15 4 5 5M4 20l5-1L21 7l-4-4L5 15z"/>',
    trash: '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/>',
    folder: '<path d="M3 5h7l2 3h9v12H3z"/>',
    shield: '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6zM8 12l3 3 5-6"/>',
    search: '<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/>',
  };
  const icon = name => `<svg class="ico" viewBox="0 0 24 24" aria-hidden="true">${paths[name] || paths.list}</svg>`;
  const btn = (action, label, type = '', ico = '', attrs = '') => `<button type="button" data-action="${action}" class="${type}" ${attrs}>${ico ? icon(ico) : ''}${label}</button>`;
  let state = { version: 1, projects: [], currentProjectId: null };
  let view = 'overview', tableMode = 'detail', filter = '', systemFilter = '', drawingId = null;
  let tool = 'select', points = [], zoom = 100, selectedItem = null, pendingSource = null;
  let db, storageError = '', saveQueue = Promise.resolve(), saveCount = 0, savedCount = 0, diskRevision = 0;
  let toastTimer, confirmAction = null, nextBranch = false, pickMode = false, measureCategory='电线';
  const snapCache=new WeakMap();
  function snapIndex(d){if(d?.cad?.geometryVersion!==1)return null;if(!snapCache.has(d))snapCache.set(d,MEPSnap.index(d.cad.segments||[]));return snapCache.get(d);}
  function capture(plan,e){const p=plan.createSVGPoint();p.x=e.clientX;p.y=e.clientY;const q=p.matrixTransform(plan.getScreenCTM().inverse()),d=drawing(),idx=snapIndex(d),t=12/Math.hypot(plan.getScreenCTM().a,plan.getScreenCTM().b);return {q,idx,t,hit:idx?MEPSnap.find(idx,q,t):null};}
  const splitPaths=pts=>{const out=[];for(const p of pts){if(!out.length||p.breakBefore)out.push([]);out.at(-1).push(p);}return out;};
  const current = () => state.projects.find(p => p.id === state.currentProjectId) || null;
  const drawing = () => current()?.drawings.find(d => d.id === drawingId) || current()?.drawings[0] || null;
  const filtered = () => (current()?.items || []).filter(i => (!systemFilter || i.system === systemFilter) && [i.name, i.spec, i.location, i.note].join(' ').toLowerCase().includes(filter.toLowerCase()));
  const colors = { 给水: '#328bb5', 排水: '#468c75', 强电: '#cc823a', 弱电: '#8e77b5', 消防: '#cc6761', 其他: '#748477' };
  function tag(system) { return `<span class="tag ${['强电', '弱电'].includes(system) ? 'electric' : ['给水', '排水'].includes(system) ? 'water' : ''}">${h(system)}</span>`; }
  function toast(text) { $('#toast').textContent = text; $('#toast').classList.add('show'); clearTimeout(toastTimer); toastTimer = setTimeout(() => $('#toast').classList.remove('show'), 4500); }
  function connectDB() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open('mep-manager-v1', 1);
      req.onupgradeneeded = () => req.result.createObjectStore('workspace');
      req.onsuccess = () => resolve(req.result); req.onerror = () => reject(req.error);
      req.onblocked = () => reject(new Error('数据库被其他窗口占用'));
    });
  }
  function dbRead() {
    return new Promise((resolve, reject) => { const req = db.transaction('workspace').objectStore('workspace').get('state'); req.onsuccess = () => resolve(req.result); req.onerror = () => reject(req.error); });
  }
  function storageStatus() { document.querySelectorAll('.save-status').forEach(el => el.textContent = storageError ? '尚未保存 · 请备份' : savedCount === saveCount ? '已保存在此设备' : '正在保存…'); }
  function persist() {
    const snapshot = structuredClone(state), revision = ++saveCount;
    storageStatus();
    saveQueue = saveQueue.catch(() => {}).then(() => new Promise((resolve, reject) => {
      if (!db) return reject(new Error('本地存储不可用'));
      const tx = db.transaction('workspace', 'readwrite'), store = tx.objectStore('workspace');
      let conflict = false;
      const read = store.get('state');
      read.onsuccess = () => {
        if ((read.result?.revision || 0) !== diskRevision) { conflict = true; tx.abort(); return; }
        snapshot.revision = diskRevision + 1; store.put(snapshot, 'state');
      };
      tx.oncomplete = () => { diskRevision = snapshot.revision; resolve(); };
      tx.onerror = () => reject(tx.error);
      tx.onabort = () => reject(conflict ? new Error('其他窗口已修改数据。为避免覆盖，本页修改暂未保存。请先备份本页，再刷新并恢复备份合并。') : tx.error);
    })).then(() => { savedCount = revision; storageError = ''; storageStatus(); $('#storage-alert')?.remove(); }).catch(error => {
      storageError = error?.message?.startsWith('其他窗口') ? error.message : '本地保存失败。请立即点击“备份数据”保存文件，避免关闭页面后丢失。'; storageStatus();
      if (!$('#storage-alert')) $('.workspace').insertAdjacentHTML('afterbegin', `<div id="storage-alert" class="storage-error" role="alert">${h(storageError)}</div>`);
      toast('保存失败，请先备份数据');
    });
    return saveQueue;
  }
  function resetDrawing() { points = []; tool = 'select'; selectedItem = null; zoom = 100; pendingSource = null; nextBranch=false; }
  function go(next) {
    if (points.length) return confirmDialog('离开当前测量？', '当前还没有保存的测量点会被清除，已保存的工程量不受影响。', () => { points = []; go(next); }, '离开');
    view = next; render();
  }
  function art() { return `<svg viewBox="0 0 380 220" fill="none" aria-hidden="true"><g transform="translate(48 23) rotate(-8 145 90)"><rect x="9" y="12" width="270" height="174" rx="6" fill="#bfd1c1" opacity=".5"/><rect width="270" height="174" rx="6" fill="#fcfdf8"/><g stroke="#b8c9b6" stroke-width="2"><path d="M29 26h210v124H29zM107 26v79H29m78-33h75V26m0 46v78m-75-45v45M29 133h44"/><path d="M107 92c-17 0-29 13-29 29m104-40c16 0 28 12 28 28" stroke-width="1"/></g><path d="M47 126V46h45v79h70V88h55v43" stroke="#438b70" stroke-width="3" stroke-linecap="round"/><g fill="#fff" stroke="#438b70" stroke-width="2"><circle cx="47" cy="126" r="4"/><circle cx="92" cy="46" r="4"/><circle cx="162" cy="125" r="4"/><circle cx="217" cy="88" r="4"/></g><path d="M29 163h210" stroke="#c5a26e" stroke-dasharray="3 3"/><rect x="193" y="132" width="94" height="42" rx="8" fill="#2a6650"/><text x="207" y="150" fill="#bed6ba" font-size="8">MEASURED LENGTH</text><text x="207" y="166" fill="#fff" font-size="15" font-family="sans-serif">24.80 m</text></g></svg>`; }
  function shell(body) {
    const navItems = [['overview', 'home', '项目总览'], ['drawings', 'plan', '图纸算量'], ['quantities', 'list', '工程量清单'], ['materials','folder','材料库存'], ['workers','list','工人和工资'], ['cash', 'wallet', '项目收支']];
    return `<div class="layout"><aside class="sidebar"><div class="brand"><span class="brand-mark">M</span><div><strong>水电小助手</strong><small>MEP · MANAGER</small></div></div><div class="nav-label">我的工作台</div><nav class="nav" aria-label="主导航">${navItems.map(([id, ico, label]) => btn('nav', label, view === id ? 'active' : '', ico, `data-view="${id}" ${view === id ? 'aria-current="page"' : ''}`)).join('')}</nav><div class="sidebar-bottom"><div class="offline"><span class="dot"></span>本地工作，安心记录</div><p>项目数据保存在当前浏览器。<br>定期备份，换设备也能接着做。</p>${btn('help', '新手使用指南', '', 'help')}<p>试用版 · v0.3.0</p></div></aside><main class="workspace">${storageError ? `<div id="storage-alert" class="storage-error" role="alert">${h(storageError)}</div>` : ''}<header class="topbar"><div class="project-switch"><span>当前项目</span><select id="project-select" aria-label="当前项目">${state.projects.length ? state.projects.map(p => `<option value="${h(p.id)}" ${p.id === state.currentProjectId ? 'selected' : ''}>${h(p.name)}</option>`).join('') : '<option value="">还没有项目</option>'}</select>${btn('new-project', '', 'icon', 'plus', 'aria-label="新建项目" title="新建项目"')}</div><div class="top-actions"><span class="save-status">${storageError ? '尚未保存 · 请备份' : savedCount === saveCount ? '已保存在此设备' : '正在保存…'}</span>${btn('backup', '备份数据', '', 'download')}${btn('restore', '恢复备份', '', 'upload')}</div></header><div class="content">${body}</div></main></div>`;
  }
  function heading(title, subtitle, actions = '') { return `<div class="page-heading"><div><div class="eyebrow">MEP WORKSPACE / ${view.toUpperCase()}</div><h1>${title}</h1><p>${subtitle}</p></div><div class="actions">${actions}</div></div>`; }
  function demoBanner() { return current()?.demo ? `<div class="banner"><span>你正在体验示例项目，图纸、工程量和收支均为演示数据。</span>${btn('new-project', '新建我的项目', 'small')}</div>` : ''; }
  function empty(title, text, button = '', ico = 'folder') { return `<div class="empty">${icon(ico)}<h3>${title}</h3><p>${text}</p>${button}</div>`; }
  function welcome() {
    return `${heading('把图纸上的线，变成清楚的工程量。', '从第一个项目开始，不需要先学一堆专业操作。')}<div class="welcome"><section class="hero"><div class="hero-copy"><div class="eyebrow">为水电安装现场而做</div><h2>看得懂，点得准，<br>每一笔数量都有来处。</h2><p>放入图纸、标定一段已知长度，沿着管线点一点。小助手帮你计算长度、统计设备，再整理成材料清单。</p><div class="actions">${btn('new-project', '创建第一个项目', 'primary', 'plus')}${btn('demo', '先试一份示例', '', 'arrow')}</div></div><div class="hero-art">${art()}</div></section><div class="feature-grid"><div class="feature">${icon('ruler')}<h3>跟着提示，三步算量</h3><p>选图纸 → 设置比例 → 测量或点数。可以撤回上一步，边做边检查。</p></div><div class="feature">${icon('list')}<h3>怎么算的，一眼明白</h3><p>实际工程量与备料损耗分开列出。点击来源，回到图纸上的测量位置。</p></div><div class="feature">${icon('shield')}<h3>你的项目，留在本机</h3><p>无需注册账号。支持导出清单、完整备份和恢复，现场数据自己掌握。</p></div></div><p class="footer-note">支持 DWG（本机转换）、ASCII DXF，以及 PNG / JPG / WebP 图片。<br>CAD 先选区、再定比例。本版为辅助预览与人工测量，复杂对象和字体需与原图核对；暂不支持 PDF 或自动识图。</p></div>`;
  }
  function stat(label, value, unit, note, ico) { return `<div class="stat"><div class="stat-head">${label}${icon(ico)}</div><div class="stat-value">${value}<em>${unit}</em></div><p>${note}</p></div>`; }
  function overview() {
    const p = current(), total = p.items.reduce((sum, i) => sum + MEP.calculate(i).cost, 0);
    const measured = p.items.filter(i => i.source).length;
    return `${heading('让今天的工程，心里有数。', `${h(p.name)}${p.location ? ' · ' + h(p.location) : ''}`, btn('edit-project', '项目设置', '', 'edit'))}${demoBanner()}<section class="hero"><div class="hero-copy"><div class="eyebrow">从一张图纸开始</div><h2>少一些反复算，<br>多一份看得见的依据。</h2><p>沿管线测长度，按设备点数量。每一笔工程量都可以返回图纸核对，清单随做随汇总。</p><div class="actions">${btn('nav', '进入图纸算量', 'primary', 'arrow', 'data-view="drawings"')}${btn('manual', '直接录入工程量', '', 'plus')}</div></div><div class="hero-art">${art()}</div></section><div class="stats">${stat('已加入图纸', p.drawings.length, '张', '图纸图片，随时回看', 'plan')}${stat('工程量记录', p.items.length, '笔', `${measured} 笔可追溯至图纸`, 'list')}${stat('材料种类', MEP.summarize(p.items).length, '类', '按专业、规格和单位区分', 'folder')}${stat('备料估算金额', money(total), '元', '含自填损耗；仅计算已填单价', 'wallet')}</div><div class="grid-two"><section class="card"><div class="card-head"><h2>最近的工程量</h2>${btn('nav', '查看全部', 'small', 'arrow', 'data-view="quantities"')}</div><div class="card-body">${p.items.length ? p.items.slice(-4).reverse().map(i => `<div class="recent-item"><div>${tag(i.system)} <strong>${h(i.name)}</strong><p>${h(i.spec || '未填规格')} · ${h(i.location || '未填位置')} · ${i.source ? '图纸测量' : '手动录入'}</p></div><strong>${fmt(MEP.calculate(i).quantity)} <small>${unitLabel(i.unit)}</small></strong></div>`).join('') : empty('第一笔工程量，从这里开始', '上传图纸测量，也可以先把现场数量手动记下来。', btn('manual', '录入一笔', 'light', 'plus'), 'list')}</div></section><section class="card"><div class="card-head"><h2>新手也能上手</h2>${btn('help', '使用指南', 'small', 'help')}</div><div class="card-body steps"><div class="step"><span class="step-num">01</span><div><h3>放入一张清晰的图纸</h3><p>导出的图片或截图都可以，保留尺寸标注。</p></div></div><div class="step"><span class="step-num">02</span><div><h3>告诉小助手一段真实长度</h3><p>点击尺寸线的两端，输入实际长度，单位为米。</p></div></div><div class="step"><span class="step-num">03</span><div><h3>沿管线点选，或逐个点设备</h3><p>补充名称、规格与位置，保存后自动进入清单。</p></div></div></div></section></div><p class="footer-note">工程量 ≠ 备料量 · 损耗只用于备料估算，不增加实际工程量。</p>`;
  }
  function hint() {
    if (tool === 'calibrate') return points.length < 2 ? `标定比例：点击已知尺寸的两个端点（已选 ${points.length}/2），不要用屏幕尺估测。` : '两个端点已选好。请输入这段距离的实际米数。';
    if (tool === 'length') return '沿管线依次点击起点、转弯处和终点，再点“保存这笔”。按退格键可撤回，Esc 取消。';
    if (tool === 'count') return '每看到一个同类设备，就在图上点一下。点完后点击“保存这笔”。';
    return '选择“测长度”或“点设备”开始；点击已保存的彩色标记，可查看那一笔工程量。';
  }
  function drawingsView() {
    const p = current(), d = drawing();
    if (!d) return `${heading('图纸算量', '沿管线点选，每一笔都能回到图上核对。', btn('upload-drawing', '添加图纸', 'primary', 'upload'))}<section class="card">${empty('先放入你的第一张图纸', '支持 DWG（本机转换）、ASCII DXF 和 PNG / JPG / WebP。<br>打开 CAD 后，可按标题定位、放大并选取要算的区域。图片每张不超过 15 MB。', btn('upload-drawing', '选择 CAD 或图片', 'primary', 'upload'), 'plan')}</section><p class="footer-note">图片必须保持原始长宽比例。同一张图中的不同缩放详图，应分别截图、分别标定。</p>`;
    drawingId = d.id;
    return `${heading('图纸算量', '先定比例，再点管线。做过的测量，随时回看。', btn('manual', '手动录入', '', 'plus') + btn('upload-drawing', '添加图纸', 'primary', 'upload'))}${demoBanner()}<div class="drawing-layout"><section class="drawing-main"><div class="drawing-bar"><div class="actions">${icon('plan')}<select id="drawing-select" aria-label="选择图纸">${p.drawings.map(x => `<option value="${h(x.id)}" ${d.id === x.id ? 'selected' : ''}>${h(x.name)}</option>`).join('')}</select></div>${btn('delete-drawing', '', 'icon danger', 'trash', 'aria-label="删除当前图纸" title="删除当前图纸"')}</div><div class="toolbar"><label>本次算量 <select id="measure-category" aria-label="本次算量类别">${['电线','电缆','桥架','给水','排水','其他'].map(x=>`<option ${measureCategory===x?'selected':''}>${x}</option>`).join('')}</select></label>${[['select', 'pointer', '查看'], ['calibrate', 'ruler', d.scale ? '重新定比例' : '① 定比例'], ['length', 'line', '② 测长度 / 自绘'], ['count', 'count', '点设备']].map(([id, ico, label]) => btn('tool', label, tool === id ? 'selected' : '', ico, `data-tool="${id}" ${id === 'length' && !d.scale ? 'disabled title="请先标定图纸比例"' : ''}`)).join('')}${tool==='length'?btn('pick-mode',pickMode?'选线段：开':'选线段：关',pickMode?'selected':'')+btn('new-branch','增加支路')+btn('bridge-lines','连接两段断线'):''}${btn('undo-point', '撤回', '', 'undo', points.length ? '' : 'disabled')}${btn('cancel-points', '取消', '', 'close', points.length ? '' : 'disabled')}</div><div class="tool-hint" id="tool-hint">${hint()}</div><div id="snap-status" role="status" class="tool-hint">${snapIndex(d)?'端点 / 交点捕捉已启用；按住 Alt 可自由落点，Shift 水平/垂直辅助。':d.cad?'旧图缺少可靠线段数据，请重新导入原 CAD 后使用捕捉。':'图片无 CAD 端点，仅能手动落点。'}</div><div class="drawing-viewport" id="drawing-viewport"><div class="paper" id="paper" style="width:${zoom}%">${svgPlan(d)}</div></div><div class="drawing-footer"><span>${d.scale ? '比例已设置 · ' + fmt(d.scale * 1000, 4) + ' 米 / 1000 像素' : '尚未设置比例 · 点数不需要比例'}</span><label class="zoom">缩放<input id="zoom" type="range" min="100" max="3200" step="25" value="${zoom}" aria-label="图纸缩放"><span id="zoom-label">${zoom}%</span></label></div></section><aside class="card panel"><div class="panel-section"><div class="eyebrow">当前操作</div><h3 id="measure-title">${tool === 'count' ? '数一数设备' : tool === 'length' ? '量一段管线' : tool === 'calibrate' ? '设置图纸比例' : '准备好，开始算量'}</h3><div id="measure-value">${readout()}</div><div style="margin-top:16px">${btn('finish-measure', tool === 'calibrate' ? '输入实际长度' : '保存这笔', 'primary full', 'check', canFinish() ? '' : 'disabled')}</div><p style="margin-top:10px">${tool === 'length' ? '这里只测平面长度。立管、上下翻弯和预留长度，请在保存时填写补充数量。' : tool === 'count' ? '同一种规格放在一笔记录里，不同规格请分别点数。' : '图纸保持原始比例；实际尺寸优先于截图测量。'}</p></div><div class="steps panel-section"><div class="step"><span class="step-num">1</span><div><h3>找一段标注尺寸</h3><p>例如图上 3600 mm，输入 3.6 米。</p></div></div><div class="step"><span class="step-num">2</span><div><h3>沿管线依次点选</h3><p>转弯处加一个点，最后保存。</p></div></div><div class="step"><span class="step-num">3</span><div><h3>填写材料名称和规格</h3><p>下次回来，还能看到测量出处。</p></div></div></div><h3>本图记录 <small>${p.items.filter(i => i.source?.drawingId === d.id).length} 笔</small></h3><div class="drawing-list">${p.items.filter(i => i.source?.drawingId === d.id).map(i => `<div class="drawing-record"><span class="swatch" style="background:${colors[i.system]}"></span>${btn('edit-item', `${h(i.name)}<small>${h(i.spec)} · ${fmt(MEP.calculate(i).quantity)} ${unitLabel(i.unit)}</small>`, '', '', `data-id="${h(i.id)}"`)}</div>`).join('') || '<p>保存后，工程量会出现在这里。</p>'}</div></aside></div><p class="footer-note">本版为人工辅助测量，不会自动识别管线或设备。不要将同图不同缩放比例的区域混用。</p>`;
  }
  function canFinish() { return tool === 'calibrate' ? points.length === 2 : tool === 'length' ? points.length >= 2 && MEP.distance(points) > 0 : tool === 'count' ? points.length > 0 : false; }
  function readout() {
    if (tool === 'count') return `<div class="measurement-readout">${points.length}<small>个点</small></div><p>已点选的同类设备</p>`;
    if (tool === 'length') return `<div class="measurement-readout">${fmt(MEP.distance(points) * (drawing()?.scale || 0))}<small>米</small></div><p>${points.length} 个测量点 · 按当前图纸比例</p>`;
    if (tool === 'calibrate') return `<div class="measurement-readout">${points.length}<small>/ 2 个端点</small></div><p>选择一段有明确尺寸标注的距离</p>`;
    return '<p>点击上方工具，开始新的一笔。图纸可放大；放大后滚动查看其他位置。</p>';
  }
  function svgPlan(d) {
    const pixel=d.width/Math.max(1,($('#drawing-viewport')?.clientWidth||800)*zoom/100), radius=3*pixel, labelSize=11*pixel;
    const path = pts => pts.map(p => `${p.x},${p.y}`).join(' ');
    const saved = current().items.filter(i => i.source?.drawingId === d.id).map(i => {
      const src = i.source, color = colors[i.system], first = src.points[0];
      return `<g class="annotation ${selectedItem === i.id ? 'highlight' : ''}" data-item="${h(i.id)}" tabindex="0" role="button" aria-label="查看${h(i.name)}的测量记录"><title>${h(i.name)} ${h(i.spec)} · ${fmt(MEP.calculate(i).quantity)} ${unitLabel(i.unit)}</title>${src.kind === 'length' ? splitPaths(src.points).map(part=>`<polyline points="${path(part)}" fill="none" stroke="${color}" stroke-width="3" vector-effect="non-scaling-stroke"/><polyline points="${path(src.points)}" fill="none" stroke="transparent" stroke-width="15" vector-effect="non-scaling-stroke"/>`).join('') : ''}${src.points.map((pt, n) => `<circle cx="${pt.x}" cy="${pt.y}" r="${radius}" fill="${src.kind === 'count' ? color : '#fff'}" stroke="${color}" stroke-width="2" vector-effect="non-scaling-stroke"/>${src.kind === 'count' ? `<text x="${pt.x}" y="${pt.y + radius * .35}" font-size="${radius * 1.1}" fill="white" text-anchor="middle" pointer-events="none">${n + 1}</text>` : ''}`).join('')}<text x="${first.x + radius * 1.6}" y="${Math.max(labelSize, first.y - radius * 1.6)}" fill="${color}" font-size="${labelSize}" font-weight="600" stroke="white" stroke-width="${labelSize / 4}" paint-order="stroke" pointer-events="none">${h(i.name)}</text></g>`;
    }).join('');
    const active = `<g pointer-events="none">${points.length > 1 && tool !== 'count' ? splitPaths(points).map(part=>`<polyline points="${path(part)}" fill="none" stroke="${tool === 'calibrate' ? '#ce863f' : '#1f8d68'}" stroke-width="3" stroke-dasharray="${tool === 'calibrate' ? '7 5' : '0'}" vector-effect="non-scaling-stroke"/>`).join('') : ''}${points.map((p, i) => `<circle cx="${p.x}" cy="${p.y}" r="${radius * 1.1}" fill="#fff" stroke="#1f8d68" stroke-width="2.5" vector-effect="non-scaling-stroke"/><text x="${p.x + radius * 1.5}" y="${p.y - radius}" fill="#176b57" font-size="${labelSize}" font-weight="600" stroke="white" stroke-width="3" paint-order="stroke">${i + 1}</text>`).join('')}</g>`;
    return `<svg class="plan ${tool !== 'select' ? 'drawing' : ''}" id="plan" viewBox="0 0 ${d.width} ${d.height}" aria-label="${h(d.name)}，使用上方工具在图纸上测量"><image href="${d.data}" width="${d.width}" height="${d.height}"/>${saved}${active}</svg>`;
  }
  function updateCanvas() {
    const d = drawing(); if (!d || !$('#paper')) return;
    $('#paper').innerHTML = svgPlan(d); $('#tool-hint').textContent = hint(); $('#measure-value').innerHTML = readout();
    $('[data-action="finish-measure"]').disabled = !canFinish();
    $('[data-action="undo-point"]').disabled = !points.length; $('[data-action="cancel-points"]').disabled = !points.length;
  }
  function quantitiesView() {
    return `${heading('工程量清单', '实际做多少、备料要多少，分开算清楚。', btn('export-csv', '导出清单', '', 'download') + btn('manual', '录入工程量', 'primary', 'plus'))}${demoBanner()}<div class="table-tools"><div class="filters"><input id="search" type="search" placeholder="搜索材料、规格或楼层…" aria-label="搜索工程量" value="${h(filter)}"><select id="system-filter" aria-label="筛选专业"><option value="">全部专业</option>${MEP.SYSTEMS.map(s => `<option ${systemFilter === s ? 'selected' : ''}>${s}</option>`).join('')}</select></div><div class="segmented">${btn('table-mode', '逐笔明细', tableMode === 'detail' ? 'active' : '', '', 'data-mode="detail"')}${btn('table-mode', '材料汇总', tableMode === 'summary' ? 'active' : '', '', 'data-mode="summary"')}</div></div><div id="quantity-table">${quantityTable()}</div><p class="footer-note">计算规则：实际工程量 = 基础数量 × 重复份数 + 补充数量；备料量 = 实际工程量 ×（1 + 自填损耗率）。<br>显示保留最多 3 位小数，汇总使用未截断的数量。设备按实际采购包装取整，请另行核对。</p>`;
  }
  function quantityTable() {
    const items = filtered(), groups = MEP.summarize(materialLines(items)), total = items.reduce((sum, i) => sum + MEP.calculate(i).cost, 0);
    if (!items.length) return `<section class="card">${empty(current().items.length ? '没有找到匹配的记录' : '还没有工程量记录', current().items.length ? '换个关键词，或选择全部专业试试。' : '从图纸测量，或把已经算好的数量录入进来。', btn('manual', '录入工程量', 'light', 'plus'), 'list')}</section>`;
    const columns = tableMode === 'detail' ? '<th>材料 / 设备</th><th>专业</th><th>位置 / 来源</th><th class="numeric">实际工程量</th><th class="numeric">备料量</th><th class="numeric">单价 / 元</th><th class="numeric">估算金额 / 元</th><th>操作</th>' : '<th>材料 / 设备</th><th>专业</th><th>记录数</th><th class="numeric">实际工程量</th><th class="numeric">备料量</th><th class="numeric">估算金额 / 元</th>';
    const rows = tableMode === 'detail' ? items.map(i => { const c = MEP.calculate(i); return `<tr><td><strong>${h(i.name)}</strong><small>${h(i.spec || '未填规格')}</small>${(i.details?.materials||[]).map(a=>'<small>↳ '+h(a.name)+' '+h(a.spec)+' · '+fmt(a.quantity)+' '+h(a.unit)+'</small>').join('')}</td><td>${tag(i.system)}</td><td>${h(i.location || '未填位置')}<small>${i.source ? btn('locate', '查看图纸来源 ↗', 'inline-link', '', `data-id="${h(i.id)}"`) : '手动录入'}</small></td><td class="numeric"><strong>${fmt(c.quantity)} ${unitLabel(i.unit)}</strong><small>${fmt(i.base)} × ${fmt(i.copies)} + ${fmt(i.extra)}</small></td><td class="numeric">${fmt(c.purchase)} ${unitLabel(i.unit)}<small>损耗 ${fmt(i.allowance)}%</small></td><td class="numeric">${i.price ? money(i.price) : '未填'}</td><td class="numeric">${i.price ? money(c.cost) : '—'}</td><td>${btn('edit-item', '', 'icon', 'edit', `data-id="${h(i.id)}" aria-label="编辑${h(i.name)}"`)}${btn('delete-item', '', 'icon danger', 'trash', `data-id="${h(i.id)}" aria-label="删除${h(i.name)}"`)}</td></tr>`; }).join('') : groups.map(g => `<tr><td><strong>${h(g.name)}</strong><small>${h(g.spec || '未填规格')}</small></td><td>${tag(g.system)}</td><td>${g.count} 笔</td><td class="numeric"><strong>${fmt(g.quantity)} ${unitLabel(g.unit)}</strong></td><td class="numeric">${fmt(g.purchase)} ${unitLabel(g.unit)}</td><td class="numeric">${money(g.cost)}</td></tr>`).join('');
    return `<section class="card"><div class="table-wrap"><table><thead><tr>${columns}</tr></thead><tbody>${rows}</tbody></table></div><div class="table-note">当前筛选：${items.length} 笔记录，${groups.length} 类材料 · 备料估算 <strong>¥ ${money(total)}</strong> · ${items.filter(i => !i.price).length} 笔未填单价。${tableMode === 'summary' ? '不同单价的金额逐笔计算后相加。' : ''}</div></section>`;
  }

  const materialLines=items=>items.flatMap(i=>[i,...(i.details?.materials||[]).map((a,n)=>({id:i.id+':child:'+n,name:a.name,spec:a.spec,system:i.system,unit:a.unit,base:a.quantity,copies:1,extra:0,allowance:0,price:0,location:i.location,note:'附属于 '+i.name}))]);
  const managed=()=>{const p=current();for(const key of ['materials','movements','workers','attendance','payments'])p[key]??=[];return p;};
  const numField=(label,name,value=0)=>field(label,name,value,'type="number" min="0" max="1000000000" step="any" required');
  const selectField=(label,name,options,value)=>'<label class="field">'+label+'<select name="'+name+'">'+options.map(([v,t])=>'<option value="'+h(v)+'" '+(v===value?'selected':'')+'>'+h(t)+'</option>').join('')+'</select></label>';
  const simpleTable=(heads,rows)=>'<div class="table-wrap"><table><thead><tr>'+heads.map(x=>'<th>'+x+'</th>').join('')+'</tr></thead><tbody>'+rows.map(row=>'<tr>'+row.map(x=>'<td>'+x+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>';
  function materialsView(){
    const p=managed();return heading('材料库存','确认计划量后，逐笔登记实际进场、使用和退货。使用量以现场记录为准。',btn('material-from-list','从工程量清单建立材料')+btn('new-material','新建材料','primary'))+
    '<section class="card">'+simpleTable(['名称 / 规格','单位','计划总量','累计进场','实际使用','退供应商','剩余库存','待采购缺口','操作'],p.materials.map(m=>{const s=MEPManage.stock(m,p.movements);return [h(m.name)+'<small>'+h(m.spec)+'</small>',h(m.unit),fmt(m.plan),fmt(s.received),fmt(s.used),fmt(s.returned),fmt(s.remaining),fmt(s.gap),btn('edit-material','修改计划','','','data-id="'+h(m.id)+'"')+btn('movement','记进出','','','data-id="'+h(m.id)+'"')];}))+'</section><p>待采购缺口 = 计划总量 − 累计进场 + 退供应商。材料估算和进场本身不会自动记付款。</p><section class="card"><h3>材料流水</h3>'+simpleTable(['日期','材料','类型','数量','现场备注','操作'],p.movements.map(e=>[h(e.date),h(p.materials.find(m=>m.id===e.materialId)?.name),({in:'进场',use:'使用',return:'退供应商'})[e.type],fmt(e.quantity),h(e.note),btn('edit-movement','更正','','','data-id="'+h(e.id)+'"')]))+'</section>';
  }
  function materialDialog(m=null){m??={id:uid(),name:'',spec:'',system:'强电',unit:'m',plan:0};openDialog('确认材料计划量','<input type="hidden" name="id" value="'+h(m.id)+'"><div class="form-grid">'+field('材料名称','name',m.name,'required maxlength="120"')+field('规格','spec',m.spec,'maxlength="500"')+selectField('专业','system',MEP.SYSTEMS.map(x=>[x,x]),m.system)+selectField('单位','unit',MEP.UNITS.map(x=>[x,x]),m.unit)+numField('确认计划总量','plan',m.plan)+'</div>',cancel()+submit('保存材料'),'material');}
  function movementDialog(id,entry=null){const p=managed(),m=p.materials.find(x=>x.id===id);openDialog('登记 '+h(m.name),'库存 '+fmt(MEPManage.stock(m,p.movements).remaining)+' '+h(m.unit)+'<input type="hidden" name="id" value="'+h(entry?.id||'')+'"><input type="hidden" name="materialId" value="'+h(id)+'"><div class="form-grid">'+field('日期','date',entry?.date||dateNow(),'type="date" required')+selectField('操作','type',[['in','进场'],['use','现场使用'],['return','退给供应商']],entry?.type||'in')+numField('数量','quantity',entry?.quantity||0)+field('位置 / 使用部位 / 备注','note',entry?.note||'','maxlength="500"')+'</div>',cancel()+submit('记录'),'movement');}
  function workforcePeriods(p){const groups=new Map();for(const e of p.attendance){const key=e.date+' '+e.period;if(!groups.has(key))groups.set(key,new Set());groups.get(key).add(e.workerId);}return [...groups].sort((a,b)=>a[0].localeCompare(b[0])).map(([key,ids])=>[h(key),ids.size]);}
  function workersView(){
    const p=managed();return heading('工人和工资','花名册仅保存在本机。出勤确定应发工资，实际付款同步登记项目支出。',btn('new-worker','添加工人','primary'))+
    '<section class="card">'+simpleTable(['姓名 / 工种','联系方式','工日','应发工资','已付（含借支）','未付 / 多付','操作'],p.workers.map(w=>{const s=MEPManage.wages(w.id,p.attendance,p.payments);return [h(w.name)+'<small>'+h(w.trade)+'</small>',h(w.phone),fmt(s.days),money(s.due),money(s.paid),money(s.balance),btn('edit-worker','花名册','','','data-id="'+h(w.id)+'"')+btn('attendance','记出勤','','','data-id="'+h(w.id)+'"')+btn('payment','记付款/借支','','','data-id="'+h(w.id)+'"')];}))+'</section><section class="card"><h3>各时段人数</h3>'+simpleTable(['日期 / 时段','人数'],workforcePeriods(p))+'</section><section class="card"><h3>出勤记录（每行一人，同日同一时段不可重复）</h3>'+simpleTable(['日期','时段','工人','工日','日工资','应发','备注','操作'],p.attendance.map(e=>[h(e.date),h(e.period),h(p.workers.find(w=>w.id===e.workerId)?.name),fmt(e.days),money(e.rate),money(e.days*e.rate),h(e.note),btn('edit-attendance','更正','','','data-id="'+h(e.id)+'"')]))+'</section><section class="card"><h3>实际付款</h3>'+simpleTable(['日期','工人','金额','说明','操作'],p.payments.map(e=>[h(e.date),h(p.workers.find(w=>w.id===e.workerId)?.name),money(e.amount),h(e.note),btn('edit-payment','更正','','','data-id="'+h(e.id)+'"')]))+'</section>';
  }
  function workerDialog(w=null){w??={id:uid()};openDialog('人员花名册','<p>身份证和银行卡仅在此编辑窗口显示；备份必须设置密码。请保管好密码。</p><input type="hidden" name="id" value="'+h(w.id)+'"><div class="form-grid">'+[['姓名','name'],['工种','trade'],['电话','phone'],['身份证号码','identity'],['身份证地址','address'],['开户行','bank'],['银行卡号','account']].map(([label,k])=>field(label,k,w[k]||'',(k==='name'?'required ':'')+'maxlength="500" autocomplete="off"')).join('')+'</div>',cancel()+submit('保存花名册'),'worker');}
  function laborDialog(id,kind,entry=null){const w=managed().workers.find(x=>x.id===id);openDialog(h(w.name)+(kind==='attendance'?' · 出勤':' · 实际付款 / 借支'),'<input type="hidden" name="id" value="'+h(entry?.id||'')+'"><input type="hidden" name="workerId" value="'+h(id)+'"><div class="form-grid">'+field('日期','date',entry?.date||dateNow(),'type="date" required')+(kind==='attendance'?field('时段','period',entry?.period||'全天','required maxlength="120" placeholder="如上午 / 下午 / 夜班"')+numField('工日（半天填0.5）','days',entry?.days??1)+numField('本次日工资 / 元','rate',entry?.rate??0):numField('实际付出 / 元','amount',entry?.amount??0))+field('备注','note',entry?.note||'','maxlength="500"')+'</div>',cancel()+submit('保存记录'),kind);}
  let encryptedIncoming=null;
  function passwordDialog(restore=false){openDialog(restore?'输入备份密码':'设置本次备份密码','<p>密码不会上传或保存，忘记密码无法恢复这份文件。</p><div class="form-grid">'+field('密码（至少8位）','password','','type="password" minlength="8" required autocomplete="new-password"')+(restore?'':field('再次输入密码','confirm','','type="password" minlength="8" required autocomplete="new-password"'))+'</div>',cancel()+submit(restore?'解密并恢复':'下载加密备份'),restore?'decrypt-backup':'encrypt-backup');}

  function cashTotals(p) { return p.cash.reduce((s, e) => { s[e.type] = Math.round((s[e.type] + e.amount) * 100) / 100; return s; }, { income: 0, expense: 0 }); }
  function cashView() {
    const p = current(), totals = cashTotals(p);
    return `${heading('项目收支', '收到多少、花了多少，把现场的每一笔记清楚。', btn('export-cash', '导出收支', '', 'download') + btn('new-cash', '记一笔收支', 'primary', 'plus'))}${demoBanner()}<div class="stats">${stat('累计收入', money(totals.income), '元', '已登记的实际收入', 'wallet')}${stat('累计支出', money(totals.expense), '元', '已登记的实际支出', 'wallet')}${stat('收支结余', money(totals.income - totals.expense), '元', '收入减支出，不代表项目利润', 'list')}${stat('收支记录', p.cash.length, '笔', '与材料估算分开记录', 'folder')}</div><section class="card">${p.cash.length ? `<div class="table-wrap"><table><thead><tr><th>日期</th><th>收支说明</th><th>类型</th><th class="numeric">金额 / 元</th><th>操作</th></tr></thead><tbody>${[...p.cash].sort((a, b) => b.date.localeCompare(a.date)).map(e => `<tr><td>${h(e.date)}</td><td><strong>${h(e.name)}</strong></td><td><span class="tag ${e.type === 'income' ? '' : 'electric'}">${e.type === 'income' ? '收入' : '支出'}</span></td><td class="numeric ${e.type === 'income' ? 'amount-in' : 'amount-out'}">${e.type === 'income' ? '+' : '−'} ${money(e.amount)}</td><td>${btn('edit-cash', '', 'icon', 'edit', `data-id="${h(e.id)}" aria-label="编辑收支"`)}${btn('delete-cash', '', 'icon danger', 'trash', `data-id="${h(e.id)}" aria-label="删除收支"`)}</td></tr>`).join('')}</tbody></table></div>` : empty('收款、买材料、付工资，都可以记在这里', '这里只记录实际发生的收支，不会自动把工程量估算记成支出。', btn('new-cash', '记第一笔', 'light', 'plus'), 'wallet')}</section><p class="footer-note">这里只提供简易项目收支台账。工人工日、借支结算和材料库存将在后续版本逐步加入。</p>`;
  }
  function render() {
    $('#app').innerHTML = shell(!current() ? welcome() : ({ overview, drawings: drawingsView, quantities: quantitiesView, cash: cashView, materials: materialsView, workers: workersView })[view]());
    if(view==='drawings'&&drawing()?.cad) $('.drawing-layout')?.insertAdjacentHTML('beforebegin','<div class="banner warn">CAD 试读底图：字体、自定义对象和部分曲线可能缺失或简化。请先核对原 CAD 和尺寸标注，再练习测量；这不是完整的 CAD 还原。</div>');
  }
  function openDialog(title, body, actions, formType = '') {
    const dialog = $('#dialog');
    dialog.innerHTML = `<form id="dialog-form" data-form="${formType}"><div class="dialog-head"><h2>${title}</h2>${btn('close-dialog', '', 'icon', 'close', 'aria-label="关闭弹窗"')}</div><div class="dialog-body"><div id="form-error" class="error" role="alert"></div>${body}</div><div class="dialog-actions">${actions}</div></form>`;
    if (!dialog.open) dialog.showModal();
    setTimeout(() => dialog.querySelector('input:not([readonly]),select,textarea')?.focus(), 50);
  }
  const submit = text => `<button type="submit" class="primary">${text}</button>`;
  const cancel = () => btn('close-dialog', '取消');
  function field(label, name, value = '', options = '') { return `<label class="field">${label}<input name="${name}" value="${h(value)}" ${options}></label>`; }
  function projectDialog(edit = false) {
    const p = edit ? current() : null;
    openDialog(edit ? '项目设置' : '创建你的项目', `<p>先给项目起个容易辨认的名字，后面可以随时修改。</p><div class="form-grid">${field('项目名称', 'name', p?.name || '', 'required maxlength="120" placeholder="例如：云颂花园 1 号楼水电"')}${field('项目位置 / 备注', 'location', p?.location || '', 'maxlength="500" placeholder="例如：一期 · 地下室至 18 层"')}</div>${p ? `<div style="margin-top:25px">${btn('delete-project', '删除此项目及全部记录', 'small danger', 'trash')}</div>` : ''}`, cancel() + submit(edit ? '保存设置' : '创建项目'), edit ? 'edit-project' : 'new-project');
  }
  function confirmDialog(title, message, callback, label = '确认删除') {
    confirmAction = callback;
    openDialog(title, `<p>${h(message)}</p>`, cancel() + btn('confirm', label, 'primary'), 'confirm');
  }
  function itemDialog(item = null, source = null) {
    const i = item ? structuredClone(item) : { id: uid(), name: source?.kind === 'count' ? '插座' : measureCategory, spec: '', system: source?.kind === 'count' ? '强电' : ['给水','排水'].includes(measureCategory)?measureCategory:'强电', unit: source?.kind === 'length' ? 'm' : source?.kind === 'count' ? '个' : 'm', base: source ? source.kind === 'length' ? MEP.distance(source.points) * source.scale : source.points.length : '', copies: 1, extra: 0, allowance: 0, price: 0, location: '', note: '', source };
    if(i.details)i.extra=i.details.manualExtra??i.extra;
    pendingSource = i.source;
    const templates = [['给水管', 'PPR DN25', '给水', 'm'], ['排水管', 'PVC-U DN110', '排水', 'm'], ['电线', 'BV 2.5 mm²', '强电', 'm'], ['线管', 'PVC Φ20', '强电', 'm'], ['插座', '五孔插座', '强电', '个'], ['灯具', 'LED 灯', '强电', '套']];
    openDialog(item ? '查看 / 编辑工程量' : '把这笔工程量记下来', `<input type="hidden" name="id" value="${h(i.id)}"><input type="hidden" name="editing" value="${item ? 'yes' : ''}"><p>${i.source ? '基础数量来自图纸测量。补充立管、预留或重复份数后再保存。' : '已经算好的数量，也可以直接录入。所有计算过程都会保留。'}</p>${!item ? `<div class="actions" style="margin-bottom:20px">${templates.filter(t => !source || source.kind === 'length' ? !source || t[3] === 'm' : t[3] !== 'm').map(t => btn('template', t[0], 'small', '', `data-template="${h(JSON.stringify(t))}"`)).join('')}</div>` : ''}<div class="form-grid">${field('材料 / 设备名称', 'name', i.name, 'required maxlength="120"')}${field('规格型号', 'spec', i.spec, 'maxlength="500" placeholder="例如：PPR DN25"')}<label class="field">所属专业<select name="system">${MEP.SYSTEMS.map(s => `<option ${i.system === s ? 'selected' : ''}>${s}</option>`).join('')}</select></label><label class="field">数量单位<select name="unit" ${i.source?.kind === 'length' ? 'disabled' : ''}>${MEP.UNITS.map(u => `<option value="${u}" ${i.unit === u ? 'selected' : ''}>${unitLabel(u)}</option>`).join('')}</select></label>${field(i.source ? '图纸测得的基础数量' : '基础数量', 'base', i.base, `type="number" step="any" min="0" max="1000000000" required ${i.source ? 'readonly' : ''}`)}${field('重复份数', 'copies', i.copies, 'type="number" step="1" min="1" max="100000" required')}<label class="field">补充数量<input type="number" name="extra" value="${i.extra}" step="any" min="0" max="1000000000" required><small>与上方单位一致，如立管 / 预留的米数。</small></label><label class="field">备料损耗率 %<input type="number" name="allowance" value="${i.allowance}" step="any" min="0" max="100" required><small>默认 0，由你按项目填写；不增加实际工程量。</small></label>${field('单价（元 / 单位，可留 0）', 'price', i.price, 'type="number" step="0.01" min="0" max="100000000" required')}${field('楼栋 / 楼层 / 回路', 'location', i.location, 'maxlength="500" placeholder="例如：1 号楼 · 3 层 · AL1"')}<label class="field wide">备注<textarea name="note" maxlength="500" placeholder="例如：另加上翻 0.6 米；待现场复核">${h(i.note)}</textarea></label></div><div id="formula-preview" class="formula-preview"></div>${i.source ? `<p style="margin:13px 0 0;font-size:11px">来源：${h(current().drawings.find(d => d.id === i.source.drawingId)?.name || '')} · ${i.source.points.length} 个点${i.source.kind === 'length' ? ' · 保留测量时的原始比例' : ''}</p>` : ''}`, cancel() + submit(item ? '保存修改' : '加入工程量清单'), 'item');
    const known=MEP.summarize(current().items).filter(g=>!i.source||i.source.kind==='length'?g.unit==='m':g.unit!=='m');
    const container=document.createElement('div');container.className='form-grid';container.innerHTML=selectField('使用已有材料（可选）','knownMaterial',[['','自行填写'],...known.map((g,n)=>[String(n),g.name+' / '+g.spec+' / '+g.unit])],'')+
      selectField('算量类别','category',[['电线','电线'],['电缆','电缆'],['桥架','桥架'],['给水','给水'],['排水','排水'],['其他','其他']],i.details?.category||measureCategory)+
      selectField('敷设方式','route',[['待确认','待确认'],['走天','走天'],['走地','走地'],['其他','其他']],i.details?.route||'待确认')+
      '<label class="field wide">竖向 / 引下明细（每行：说明,起点高度米,终点高度米,点数,每点根数）<textarea name="vertical" rows="3" placeholder="灯具引下,3.2,2.8,6,2">'+h(i.details?.vertical||'')+'</textarea></label>'+
      '<label class="field wide">附属材料总量（每行：材料名称,规格,数量,单位；不随主材重复份数放大）<textarea name="accessories" rows="3" placeholder="弯头,DN25,4,个">'+h(i.details?.accessories||'')+'</textarea></label>'+
      '<p class="wide">竖向明细自动加到补充数量之外，避免重复填入补充数量。桥架/管道交叉处需现场确认标高和避让；接头数量需按实际定尺、分段和连接方式确认，本版不把“每6米一个”作为通用规则。</p>';
    $('#formula-preview').before(container);
    container.querySelector('[name="knownMaterial"]').onchange=e=>{const g=known[Number(e.target.value)];if(e.target.value===''||!g)return;const form=$('#dialog-form');for(const k of ['name','spec','system','unit'])form.elements[k].value=g[k];updateFormula();};
    updateFormula();
  }
  function parseVertical(value){if(!value.trim())return [];return value.trim().split(/\r?\n/).map(line=>{const parts=line.split(/[,，]/);if(parts.length!==5||!parts[0].trim()||parts.slice(1).some(v=>!v.trim()))throw Error('竖向明细每行需填：说明,起点高度,终点高度,点数,根数');const row={label:parts[0].trim(),from:Number(parts[1]),to:Number(parts[2]),count:Number(parts[3]),wires:Number(parts[4])};MEPManage.vertical([row]);if(!Number.isInteger(row.count)||!Number.isInteger(row.wires))throw Error('引下点数和根数需为整数');return row;});}
  function parseAccessories(value){if(!value.trim())return [];return value.trim().split(/\r?\n/).map(line=>{const parts=line.split(/[,，]/);if(parts.length!==4)throw Error('附属材料每行需填：名称,规格,数量,单位');return {name:MEP.required(parts[0],'材料名称'),spec:parts[1].trim(),quantity:MEP.number(parts[2],'附材数量'),unit:MEP.required(parts[3],'单位')};});}
  function updateFormula() {
    const form = $('#dialog-form'); if (form?.dataset.form !== 'item') return;
    try {
      const values = Object.fromEntries(new FormData(form)); const vertical=MEPManage.vertical(parseVertical(values.vertical||''));values.extra=Number(values.extra)+vertical;const c = MEP.calculate(values);
      const u = unitLabel(form.elements.unit.value);
      $('#formula-preview').innerHTML = `实际工程量：${fmt(values.base)} × ${fmt(values.copies)} + ${fmt(values.extra)} = <strong>${fmt(c.quantity)} ${u}</strong><br>备料量：${fmt(c.purchase)} ${u}（含 ${fmt(values.allowance)}% 损耗） · 估算金额：¥ ${money(c.cost)}`;
    } catch (e) { $('#formula-preview').textContent = e.message; }
  }
  function cashDialog(entry = null) {
    openDialog(entry ? '修改收支记录' : '记一笔实际收支', `<input type="hidden" name="id" value="${entry?.id || uid()}"><p>按实际发生的金额记录。材料估算不会自动计入收支。</p><div class="form-grid"><label class="field">收支类型<select name="type"><option value="expense" ${entry?.type !== 'income' ? 'selected' : ''}>支出 · 钱付出去</option><option value="income" ${entry?.type === 'income' ? 'selected' : ''}>收入 · 钱收进来</option></select></label>${field('日期', 'date', entry?.date || dateNow(), 'type="date" required')}${field('说明', 'name', entry?.name || '', 'required maxlength="120" placeholder="例如：采购 PPR 管材"')}${field('实际金额 / 元', 'amount', entry?.amount || '', 'type="number" min="0.01" max="1000000000" step="0.01" required')}</div>`, cancel() + submit('保存记录'), 'cash');
  }
  function finishMeasure() {
    if (!canFinish()) return;
    if (tool === 'calibrate') openDialog('这段距离实际有多长？', `<p>输入图纸标注的实际长度，单位是<strong>米</strong>。例如 3600 mm 应填写 3.6。${drawing().scale ? '本次修改只影响后续新测量，已保存记录保留各自原比例。' : ''}</p><div class="form-grid">${field('实际长度 / 米', 'meters', '', 'type="number" min="0.001" max="1000000" step="any" required placeholder="例如 3.6"')}</div>`, cancel() + submit('设置比例'), 'calibrate');
    else itemDialog(null, { drawingId: drawing().id, kind: tool, scale: tool === 'length' ? drawing().scale : null, points: structuredClone(points) });
  }
  function download(name, text, mime = 'application/json') {
    const url = URL.createObjectURL(new Blob([text], { type: mime })), a = document.createElement('a'); a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 30000);
  }
  function safeName(name) { return name.replace(/[<>:"/\\|?*\x00-\x1f]/g, '_').slice(0, 80); }
  function exportCSV() {
    const p = current(), items = materialLines(filtered()); if (!items.length) return toast('当前筛选下没有可导出的工程量');
    const rows = tableMode === 'summary' ? [['项目', '专业', '材料名称', '规格', '单位', '实际工程量', '备料量', '估算金额(元)', '记录数'], ...MEP.summarize(items).map(g => [p.name, g.system, g.name, g.spec, g.unit, g.quantity, g.purchase, g.cost.toFixed(2), g.count])] : [['项目', '专业', '材料名称', '规格', '位置', '单位', '基础数量', '重复份数', '补充数量', '实际工程量', '损耗率(%)', '备料量', '单价(元)', '估算金额(元)', '来源', '图纸', '记录编号', '备注'], ...items.map(i => { const c = MEP.calculate(i); return [p.name, i.system, i.name, i.spec, i.location, i.unit, i.base, i.copies, i.extra, c.quantity, i.allowance, c.purchase, i.price, c.cost.toFixed(2), i.source ? '图纸' + (i.source.kind === 'length' ? '测长度' : '点数') : '手动录入', p.drawings.find(d => d.id === i.source?.drawingId)?.name || '', i.id, i.note]; })];
    download(`${safeName(p.name)}-${tableMode === 'summary' ? '材料汇总' : '工程量明细'}-${dateNow()}.csv`, MEP.csv(rows), 'text/csv;charset=utf-8'); toast('已导出当前筛选结果，可用 Excel 打开');
  }
  async function importDrawing(file) {
    if (!current()) return projectDialog();
    if (/\.(dwg|dxf)$/i.test(file.name)) return importCad(file);
    if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) return toast('请使用 PNG、JPG 或 WebP 图片；PDF / DWG 请先导出或截图');
    if (file.size > 15 * 1024 * 1024) return toast('图片超过 15 MB，请先压缩或裁剪到所需区域');
    const projectId = current().id;
    try {
      const data = await new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = reject; reader.readAsDataURL(file); });
      const image = await new Promise((resolve, reject) => { const img = new Image(); img.onload = () => resolve(img); img.onerror = reject; img.src = data; });
      if (image.naturalWidth > 16000 || image.naturalHeight > 16000 || image.naturalWidth * image.naturalHeight > 50000000) throw new Error('图纸尺寸过大，请裁剪到所需区域再加入');
      const p = state.projects.find(x => x.id === projectId); if (!p) return;
      if (p.drawings.length >= 100) throw new Error('单项目最多 100 张图纸，请分项目管理');
      const d = { id: uid(), name: file.name.slice(0, 120), data, width: image.naturalWidth, height: image.naturalHeight, scale: null };
      p.drawings.push(d); state.currentProjectId = projectId; drawingId = d.id; resetDrawing(); view = 'drawings'; await persist(); render(); toast('图纸已加入，先点击“① 定比例”');
    } catch (e) { toast(e.message || '无法读取图片，请检查文件是否损坏'); }
  }
  async function importCad(file) {
    const projectId=current().id;
    if(file.size>100*1024*1024)return toast('CAD 文件过大，请先拆分为单张图纸');
    try {
      let bytes=await file.arrayBuffer();
      if(/\.dwg$/i.test(file.name)) {
        if(!/^https?:$/.test(location.protocol)){openDialog('请从本机服务导入 DWG','<p>当前是单文件版。DWG 转换需要本机服务，请打开下面的入口。两个入口的项目数据不会自动互通，需要备份恢复。</p><p><a href="http://127.0.0.1:4173/" target="_blank" rel="noopener">打开支持 DWG 的水电小助手</a></p>',btn('close-dialog','关闭'));return;}
        toast('正在本机读取 DWG，较大的图纸可能需要约一分钟…');
        const status=await fetch('/api/cad/status').then(r=>{if(!r.ok)throw new Error('请重启新版小助手本地服务后导入 DWG');return r.json();});
        if(!status.available)throw new Error('本地 DWG 转换工具尚未配置，可先在 CAD 中另存为 ASCII DXF 再导入');
        const response=await fetch('/api/cad/convert',{method:'POST',headers:{'Content-Type':'application/octet-stream','X-MEP-Token':status.token},body:bytes});
        if(!response.ok)throw new Error((await response.json()).error||'DWG 转换失败');
        bytes=await response.arrayBuffer();
      }
      toast('正在整理图层和图中标题，请稍候…');
      await new Promise(resolve=>setTimeout(resolve,40));
      let text;
      try{text=new TextDecoder('utf-8',{fatal:true}).decode(bytes);}catch{text=new TextDecoder('gb18030').decode(bytes);}
      const scene=MEPCAD.parse(text);
      MEPCAD.picker(scene,file.name,async result=>{
        const p=state.projects.find(x=>x.id===projectId);if(!p)return;
        if(p.drawings.length>=100)return toast('单项目最多 100 张图纸，请分项目管理');
        const d={...result,id:uid(),name:result.name.slice(0,120)};p.drawings.push(d);state.currentProjectId=p.id;drawingId=d.id;resetDrawing();view='drawings';await persist();render();toast('CAD 选区已加入，请先按图上的标注尺寸定比例');
      });
    }catch(error){openDialog('这份 CAD 暂时没有导入',`<p>${h(error.message)}</p>`,btn('close-dialog','知道了','primary'));}
  }
  async function restoreBackup(file,decoded=null) {
    if (file.size > 210 * 1024 * 1024) return toast('备份超过 210 MB，暂不支持导入');
    try {
      const raw=decoded||JSON.parse(await file.text());
      if(raw.format==='mep-encrypted'){encryptedIncoming=raw;passwordDialog(true);return;}
      const incoming = MEP.validateBackup(raw);incoming.projects.forEach(MEPManage.validate);
      if (!incoming.projects.length) return toast('这份备份没有项目');
      if (state.projects.length + incoming.projects.length > 200) return toast('合并后超过 200 个项目，请先整理旧项目');
      confirmDialog('恢复这份备份？', `将加入 ${incoming.projects.length} 个项目，包含图纸、工程量和收支。当前项目不会被覆盖；重名项目会作为副本加入。`, async () => {
        const copies = structuredClone(incoming.projects);
        for (const p of copies) {
          const map = new Map(); p.id = uid();
          if (state.projects.some(x => x.name === p.name)) p.name = p.name.slice(0, 110) + '（恢复副本）';
          for (const d of p.drawings) { const old = d.id; d.id = uid(); map.set(old, d.id); }
          for (const i of p.items) { i.id = uid(); if (i.source) i.source.drawingId = map.get(i.source.drawingId); }
          for (const e of p.cash) {const old=e.id;e.id=uid();map.set(old,e.id);}
          for(const group of ['materials','workers'])for(const e of p[group]||[]){const old=e.id;e.id=uid();map.set(old,e.id);}
          for(const group of ['movements','attendance','payments'])for(const e of p[group]||[]){e.id=uid();if(e.materialId)e.materialId=map.get(e.materialId);if(e.workerId)e.workerId=map.get(e.workerId);if(e.cashId)e.cashId=map.get(e.cashId);}
        }
        state.projects.push(...copies); state.currentProjectId = copies[0].id; resetDrawing(); drawingId = null; view = 'overview'; await persist(); render(); toast(`已恢复 ${copies.length} 个项目`);
      }, '恢复并加入');
    } catch (e) { toast('无法恢复：' + (e.message || '备份文件格式不正确')); }
  }
  function makeDemo() {
    const existing = state.projects.find(p => p.demo); if (existing) { state.currentProjectId = existing.id; render(); persist(); return; }
    const canvas = document.createElement('canvas'); canvas.width = 1200; canvas.height = 840;
    const c = canvas.getContext('2d'); c.fillStyle = '#fffefa'; c.fillRect(0, 0, 1200, 840);
    c.fillStyle = '#394b48'; c.font = 'bold 25px Microsoft YaHei, sans-serif'; c.fillText('示例住宅 · 一层水电平面图', 70, 58); c.font = '15px Microsoft YaHei, sans-serif'; c.fillStyle = '#8b958b'; c.fillText('演示图纸 / 非施工图    单位：mm', 70, 87);
    c.strokeStyle = '#9ca69c'; c.lineWidth = 8; c.strokeRect(130, 180, 930, 500);
    c.beginPath(); c.moveTo(480, 180); c.lineTo(480, 430); c.moveTo(480, 510); c.lineTo(480, 680); c.moveTo(480, 430); c.lineTo(650, 430); c.moveTo(735, 430); c.lineTo(1060, 430); c.moveTo(780, 180); c.lineTo(780, 430); c.moveTo(800, 430); c.lineTo(800, 680); c.stroke();
    c.lineWidth = 1; c.strokeStyle = '#c5cdc2'; c.beginPath(); c.arc(480, 510, 80, -Math.PI / 2, -Math.PI, true); c.moveTo(480, 510); c.lineTo(400, 510); c.moveTo(735, 430); c.arc(735, 430, 85, Math.PI, Math.PI / 2, true); c.stroke();
    c.font = '22px Microsoft YaHei, sans-serif'; c.textAlign = 'center'; c.fillStyle = '#a3ab9d'; [['客厅', 300, 400], ['厨房', 625, 310], ['卫生间', 920, 310], ['卧室 A', 635, 575], ['卧室 B', 935, 575]].forEach(([t, x, y]) => c.fillText(t, x, y));
    c.lineWidth = 2; c.strokeStyle = '#aab7a4'; c.strokeRect(155, 480, 65, 145); c.strokeRect(260, 540, 100, 55); c.strokeRect(820, 200, 70, 80); c.strokeRect(950, 210, 70, 45); c.strokeRect(510, 200, 210, 50); c.strokeRect(525, 510, 100, 135); c.strokeRect(855, 510, 100, 135);
    c.strokeStyle = '#acb7a5'; c.lineWidth = 1; c.beginPath(); c.moveTo(130, 128); c.lineTo(1060, 128); c.moveTo(130, 113); c.lineTo(130, 159); c.moveTo(1060, 113); c.lineTo(1060, 159); c.moveTo(130, 716); c.lineTo(1060, 716); c.moveTo(130, 700); c.lineTo(130, 733); c.moveTo(480, 700); c.lineTo(480, 733); c.moveTo(800, 700); c.lineTo(800, 733); c.moveTo(1060, 700); c.lineTo(1060, 733); c.stroke();
    c.font = '16px Microsoft YaHei, sans-serif'; c.fillStyle = '#81917c'; c.fillText('9300', 595, 118); c.fillText('3500', 305, 739); c.fillText('3200', 640, 739); c.fillText('2600', 930, 739); c.font = '13px Microsoft YaHei, sans-serif'; c.fillText('练习标定：上方整段尺寸为 9300 mm，请输入 9.3 米', 595, 795);
    const d = { id: uid(), name: '一层水电平面图 · 示例', width: 1200, height: 840, data: canvas.toDataURL('image/png'), scale: .01 };
    const make = (name, spec, system, pts, kind, price, extra, allowance) => ({ id: uid(), name, spec, system, unit: kind === 'length' ? 'm' : '个', base: kind === 'length' ? MEP.distance(pts) * .01 : pts.length, copies: 1, extra, allowance, price, location: '示例楼栋 · 1 层', note: '仅供体验，非实际施工数据', source: { drawingId: d.id, kind, scale: kind === 'length' ? .01 : null, points: pts } });
    const p = { id: uid(), name: '青禾家园 · 水电安装（示例）', location: '演示项目 · 1 号楼', demo: true, drawings: [d], items: [make('给水管', 'PPR DN25', '给水', [{ x: 170, y: 640 }, { x: 170, y: 465 }, { x: 755, y: 465 }, { x: 755, y: 280 }, { x: 980, y: 280 }], 'length', 12.5, 2.4, 3), make('线管', 'PVC Φ20', '强电', [{ x: 235, y: 615 }, { x: 430, y: 615 }, { x: 430, y: 370 }, { x: 730, y: 370 }], 'length', 3.8, 1.8, 5), make('插座', '五孔插座', '强电', [{ x: 200, y: 225 }, { x: 420, y: 225 }, { x: 690, y: 225 }, { x: 580, y: 645 }, { x: 740, y: 645 }, { x: 985, y: 645 }], 'count', 18, 0, 0)], cash: [{ id: uid(), name: '示例：收到工程预付款', date: dateNow(), type: 'income', amount: 20000 }, { id: uid(), name: '示例：首批管材采购', date: dateNow(), type: 'expense', amount: 3600 }] };
    state.projects.push(p); state.currentProjectId = p.id; drawingId = d.id; view = 'overview'; persist(); render(); toast('示例已准备好，可以放心练习');
  }
  function helpDialog() {
    openDialog('第一次用？跟着这几步就好', `<div class="help-block"><h3>1 · 放图纸，先定比例</h3><p>进入“图纸算量”，加入 PNG / JPG / WebP 图片。点击“定比例”，选中一段标注尺寸的两端，再输入实际米数。3600 mm = 3.6 米。</p></div><div class="help-block"><h3>2 · 点管线，或点设备</h3><p>“测长度”沿起点、转弯、终点逐个点击；“点设备”每个设备点一次。点错用“撤回”，放大后可滚动查看。点完点击“保存这笔”。</p></div><div class="help-block"><h3>3 · 补齐信息，再看清单</h3><p>填名称、规格、楼层。重复份数可用于相同楼层或相同回路；立管和预留填入补充数量。电线根数需要自行核对后填写份数，不会自动从线管推算。</p></div><div class="help-block"><h3>4 · 导出清单，记得备份</h3><p>工程量清单可查看明细或材料汇总，再导出 CSV，用 Excel 打开。完整备份包含图纸、测量点、工程量和收支。数据只存在当前浏览器，清理浏览器或换地址不会自动带走数据。</p></div><p>CAD 试读支持本机转换 DWG、直接读取 ASCII DXF，并将选区转换为测量底图。复杂对象与字体可能缺失，请核对原图。本版不支持 PDF、自动识图、云端同步或正式计价定额。倾斜照片、拉伸截图和同图不同缩放详图会影响长度测量，请先校正或分别截图标定。</p>`, btn('close-dialog', '知道了，开始做', 'primary'));
  }
  document.addEventListener('click', async e => {
    const actionEl = e.target.closest('[data-action]');
    if (actionEl) {
      const action = actionEl.dataset.action, p = current();
      const item = p?.items.find(i => i.id === actionEl.dataset.id);
      if (actionEl.disabled) return;
      try {
        switch (action) {
          case 'nav': return go(actionEl.dataset.view);
          case 'new-project': return projectDialog();
          case 'edit-project': return projectDialog(true);
          case 'demo': return makeDemo();
          case 'help': return helpDialog();
          case 'close-dialog': $('#dialog').close(); return;
          case 'confirm': { const callback = confirmAction; confirmAction = null; $('#dialog').close(); if (callback) await callback(); return; }
          case 'backup': return passwordDialog();
          case 'new-material': return materialDialog();
          case 'edit-material': return materialDialog(managed().materials.find(x=>x.id===actionEl.dataset.id));
          case 'movement': return movementDialog(actionEl.dataset.id);
          case 'edit-movement': {const e=managed().movements.find(x=>x.id===actionEl.dataset.id);return movementDialog(e.materialId,e);}
          case 'material-from-list': {
            const p=managed(),groups=MEP.summarize(materialLines(p.items)),same=(a,b)=>a.name===b.name&&a.spec===b.spec&&a.unit===b.unit&&a.system===b.system;
            const fresh=groups.filter(g=>!p.materials.some(m=>same(m,g)));
            if(!fresh.length)return toast('清单材料已建立；计划量需在材料库存中确认修改');
            confirmDialog('建立材料计划？','将新增 '+fresh.length+' 类材料，以当前备料量作为计划总量，已有计划不覆盖。',()=>{p.materials.push(...fresh.map(g=>({id:uid(),name:g.name,spec:g.spec,system:g.system,unit:g.unit,plan:g.purchase})));persist();render();},'确认计划');return;
          }
          case 'new-worker': return workerDialog();
          case 'edit-worker': return workerDialog(managed().workers.find(x=>x.id===actionEl.dataset.id));
          case 'edit-attendance': case 'edit-payment': {const kind=actionEl.dataset.action.slice(5),list=kind==='attendance'?'attendance':'payments',entry=managed()[list].find(x=>x.id===actionEl.dataset.id);return laborDialog(entry.workerId,kind,entry);}
          case 'attendance': case 'payment': return laborDialog(actionEl.dataset.id,actionEl.dataset.action);
          case 'restore': $('#backup-file').click(); return;
          case 'upload-drawing': if (points.length) return toast('请先保存或取消当前测量'); $('#drawing-file').click(); return;
          case 'manual': return itemDialog();
          case 'edit-item': if (item) { selectedItem = item.id; itemDialog(item); } return;
          case 'locate': if (item?.source) { drawingId = item.source.drawingId; resetDrawing(); selectedItem = item.id; view = 'drawings'; render(); } return;
          case 'delete-item': return confirmDialog('删除这笔工程量？', `${item.name}（${item.spec || '未填规格'}）及图上的对应标记会被删除。建议先备份，删除后不能直接撤销。`, () => { p.items = p.items.filter(i => i.id !== item.id); persist(); render(); toast('已删除工程量记录'); });
          case 'delete-project': return confirmDialog('删除整个项目？', `“${p.name}”的图纸、工程量与收支都会删除，无法直接撤销。请先备份需要保留的数据。`, () => { state.projects = state.projects.filter(x => x.id !== p.id); state.currentProjectId = state.projects[0]?.id || null; drawingId = null; resetDrawing(); persist(); render(); toast('已删除项目'); });
          case 'delete-drawing': {
            const d = drawing(); if (p.items.some(i => i.source?.drawingId === d.id)) return toast('此图已有工程量来源，请先删除对应记录再删除图纸');
            return confirmDialog('删除这张图纸？', '图纸将从本项目移除，未保存的测量点也会清除。', () => { p.drawings = p.drawings.filter(x => x.id !== d.id); drawingId = null; resetDrawing(); persist(); render(); });
          }
          case 'tool': {
            const next = actionEl.dataset.tool;
            if (next === tool) return;
            const change = () => { tool = next; points = []; selectedItem = null; render(); };
            if (points.length) return confirmDialog('切换测量工具？', '当前未保存的测量点会被清除。', change, '切换工具');
            change(); return;
          }
          case 'bridge-lines': {
            const parts=splitPaths(points);if(parts.length!==2||parts.some(p=>p.length<2))return toast('先用选线段模式选择两条独立线段');
            const bridge=MEPSnap.bridge(parts[0],parts[1]),meters=MEP.distance(bridge)*drawing().scale;
            confirmDialog('确认补上断线？','将在两段最近端点间补画 '+fmt(meters)+' 米直线，并计入本笔工程量。请确认这处空隙确实需要连续敷设。',()=>{points.push({...bridge[0],breakBefore:true},bridge[1]);updateCanvas();},'确认补线');return;
          }
          case 'pick-mode': pickMode=!pickMode;render();return;
          case 'new-branch': nextBranch=true;toast('下一点作为新支路起点，支路间不计连接长度');return;
          case 'undo-point': points.pop(); updateCanvas(); return;
          case 'cancel-points': points = []; updateCanvas(); return;
          case 'finish-measure': return finishMeasure();
          case 'template': { const [name, spec, system, unit] = JSON.parse(actionEl.dataset.template), form = $('#dialog-form'); for (const [key, val] of Object.entries({ name, spec, system, unit })) form.elements[key].value = val; updateFormula(); return; }
          case 'table-mode': tableMode = actionEl.dataset.mode; render(); return;
          case 'export-csv': return exportCSV();
          case 'new-cash': return cashDialog();
          case 'edit-cash': if((current().payments||[]).some(x=>x.cashId===actionEl.dataset.id))return toast('这是工资付款关联记录，不能单独改金额'); return cashDialog(p.cash.find(x => x.id === actionEl.dataset.id));
          case 'delete-cash': if((current().payments||[]).some(x=>x.cashId===actionEl.dataset.id))return toast('这是工资付款关联记录，不能单独删除'); return confirmDialog('删除这笔收支？', '删除后，项目的收支汇总也会相应更新。', () => { p.cash = p.cash.filter(x => x.id !== actionEl.dataset.id); persist(); render(); toast('已删除收支记录'); });
          case 'export-cash': if (!p.cash.length) return toast('暂时没有收支记录'); download(`${safeName(p.name)}-收支-${dateNow()}.csv`, MEP.csv([['项目', '日期', '说明', '类型', '金额(元)'], ...p.cash.map(x => [p.name, x.date, x.name, x.type === 'income' ? '收入' : '支出', x.amount.toFixed(2)])]), 'text/csv;charset=utf-8'); return;
        }
      } catch (err) { toast(err.message || '操作未完成，请重试'); }
    }
    const plan = e.target.closest('#plan');
    if (plan) {
      if (tool === 'select') { const annotation = e.target.closest('[data-item]'); if (annotation) { selectedItem = annotation.dataset.item; itemDialog(current().items.find(i => i.id === selectedItem)); updateCanvas(); } return; }
      if (tool === 'calibrate' && points.length >= 2) return toast('两个端点已选好，请点击“输入实际长度”');
      const pt = plan.createSVGPoint(); pt.x = e.clientX; pt.y = e.clientY;
      const mapped = pt.matrixTransform(plan.getScreenCTM().inverse()), d = drawing();
      let next = { x: Math.max(0, Math.min(d.width, mapped.x)), y: Math.max(0, Math.min(d.height, mapped.y)) };
      const {idx,t,hit}=capture(plan,e);
      if(tool==='length'&&pickMode){
        if(!idx)return toast('请重新导入 CAD，取得可靠线段数据');
        const line=MEPSnap.pick(idx,next,t);if(!line)return toast('请靠近完整可见的直线段；裁剪边界处请用端点测量');
        const a={x:line.a[0],y:line.a[1],breakBefore:true},b={x:line.b[0],y:line.b[1]},key=MEPSnap.edgeKey(a,b);
        if(splitPaths(points).some(path=>path.slice(1).some((p,i)=>MEPSnap.edgeKey(path[i],p)===key)))return toast('本笔已包含这条线段');
        points.push(a,b);updateCanvas();return;
      }
      if(hit&&!e.altKey)next={x:hit.x,y:hit.y};
      else if(idx&&tool==='calibrate'&&!e.altKey)return toast('尚未捕捉到端点或交点，请靠近目标点');
      else if(e.shiftKey&&points.length&&!nextBranch){const a=points.at(-1);if(Math.abs(next.x-a.x)>Math.abs(next.y-a.y))next.y=a.y;else next.x=a.x;}
      if(nextBranch){next.breakBefore=true;nextBranch=false;}
      if (points.length && tool !== 'count' && Math.hypot(next.x - points.at(-1).x, next.y - points.at(-1).y) < .1) return;
      points.push(next); updateCanvas();
    }
  });
  document.addEventListener('pointermove',e=>{
    const plan=e.target.closest('#plan');if(!plan||!['length','calibrate','count'].includes(tool))return;
    const {hit,t}=capture(plan,e);let marker=plan.querySelector('#snap-marker');
    if(!marker){marker=document.createElementNS('http://www.w3.org/2000/svg','rect');marker.id='snap-marker';marker.setAttribute('fill','none');marker.setAttribute('stroke','#d100b5');marker.setAttribute('stroke-width','2');marker.setAttribute('vector-effect','non-scaling-stroke');marker.style.pointerEvents='none';plan.append(marker);}
    const show=hit&&!e.altKey;marker.style.display=show?'':'none';
    if(show){marker.setAttribute('x',hit.x-t/3);marker.setAttribute('y',hit.y-t/3);marker.setAttribute('width',t*2/3);marker.setAttribute('height',t*2/3);}
    if($('#snap-status'))$('#snap-status').textContent=show?'已捕捉：'+hit.kind+' · 点击确认':snapIndex(drawing())?'靠近端点或交点；Alt 自由落点，Shift 水平/垂直辅助。':'旧 CAD 请重新导入以启用可靠捕捉；图片仅支持手动测量。';
  });
  document.addEventListener('submit', async e => {
    if (e.target.getAttribute('id') !== 'dialog-form') return; e.preventDefault();
    const form = e.target, values = Object.fromEntries(new FormData(form)), p = current();
    try {
      switch (form.dataset.form) {
        case 'encrypt-backup': {
          if(values.password!==values.confirm)throw Error('两次密码不一致');
          const payload=await MEPManage.encrypt({...state,exportedAt:new Date().toISOString()},values.password);
          download('水电小助手-加密备份-'+dateNow()+'.json',JSON.stringify(payload));dialog.close();toast('已导出密码保护的完整备份');return;
        }
        case 'decrypt-backup': {
          const decoded=await MEPManage.decrypt(encryptedIncoming,values.password);encryptedIncoming=null;dialog.close();await restoreBackup({size:0},decoded);return;
        }
        case 'material': {
          const p=managed(),m={id:values.id,name:MEP.required(values.name,'材料名称'),spec:values.spec.trim(),unit:values.unit,system:values.system,plan:MEP.number(values.plan,'计划量')};
          if(p.materials.some(x=>x.id!==m.id&&x.name===m.name&&x.spec===m.spec&&x.unit===m.unit&&x.system===m.system))throw Error('已有同类材料，请使用已有材料登记');
          const old=p.materials.findIndex(x=>x.id===m.id);if(old>=0)p.materials[old]=m;else p.materials.push(m);break;
        }
        case 'movement': {
          const p=managed(),e={id:values.id||uid(),materialId:values.materialId,type:values.type,quantity:MEP.number(values.quantity,'数量',.000001),date:values.date,note:values.note};
          const rest=p.movements.filter(x=>x.id!==e.id),m=p.materials.find(m=>m.id===e.materialId);MEPManage.validateMovement(e,m,rest);if(MEPManage.stock(m,[...rest,e]).remaining<0)throw Error('更正后库存不足，请先核对使用记录');p.movements=p.movements.map(x=>x.id===e.id?e:x);if(!p.movements.some(x=>x.id===e.id))p.movements.push(e);break;
        }
        case 'worker': {
          const p=managed(),w={id:values.id};for(const k of ['name','trade','phone','identity','address','bank','account'])w[k]=values[k].trim();MEP.required(w.name,'姓名');
          const old=p.workers.findIndex(x=>x.id===w.id);if(old>=0)p.workers[old]=w;else p.workers.push(w);break;
        }
        case 'attendance': {
          const p=managed();if(p.attendance.some(x=>x.id!==values.id&&x.workerId===values.workerId&&x.date===values.date&&x.period===values.period.trim()))throw Error('该工人当天同一时段已有记录，请核对');
          const entry={id:values.id||uid(),workerId:values.workerId,date:values.date,period:MEP.required(values.period,'时段'),days:MEP.number(values.days,'工日',.001,31),rate:MEP.number(values.rate,'日工资',0,1e6),note:values.note};const old=p.attendance.findIndex(x=>x.id===entry.id);if(old<0)p.attendance.push(entry);else p.attendance[old]=entry;break;
        }
        case 'payment': {
          const p=managed(),amount=Math.round(MEP.number(values.amount,'实际支付',.01)*100)/100,old=p.payments.find(x=>x.id===values.id),cashId=old?.cashId||uid(),worker=p.workers.find(w=>w.id===values.workerId);
          const entry={id:old?.id||uid(),workerId:worker.id,date:values.date,amount,note:values.note,cashId},cash={id:cashId,date:values.date,name:('工资/借支 · '+worker.name).slice(0,120),type:'expense',amount};if(old){p.payments[p.payments.indexOf(old)]=entry;const ci=p.cash.findIndex(x=>x.id===cashId);if(ci<0)throw Error('关联付款不存在');p.cash[ci]=cash;}else{p.payments.push(entry);p.cash.push(cash);}break;
        }
        case 'new-project': case 'edit-project': {
          const name = MEP.required(values.name, '项目名称'), location = values.location.trim();
          if (form.dataset.form === 'edit-project') Object.assign(p, { name, location });
          else { if (state.projects.length >= 200) throw new Error('最多支持 200 个项目，请先整理旧项目'); const project = { id: uid(), name, location, demo: false, drawings: [], items: [], cash: [] }; state.projects.push(project); state.currentProjectId = project.id; view = 'overview'; drawingId = null; resetDrawing(); }
          break;
        }
        case 'calibrate': { const d = drawing(); d.scale = MEP.calibrate(points, values.meters); d.calibration={points:structuredClone(points),meters:Number(values.meters),at:new Date().toISOString()}; points = []; tool = 'length'; toast('比例已设置，可以沿管线测长度了'); break; }
        case 'item': {
          const old = p.items.find(i => i.id === values.id), source = old?.source || pendingSource;
          const item = { id: values.id, name: MEP.required(values.name, '名称'), spec: values.spec.trim(), system: values.system, unit: source?.kind === 'length' ? 'm' : values.unit, location: values.location.trim(), note: values.note.trim(), source };
          for (const key of ['base', 'copies', 'extra', 'allowance', 'price']) item[key] = Number(values[key]);
          if (source) item.base = source.kind === 'length' ? MEP.distance(source.points) * source.scale : source.points.length;
          const rows=parseVertical(values.vertical||''),accessories=parseAccessories(values.accessories||'');
          if(item.unit!=='m'&&rows.length)throw Error('竖向长度只能加入以米计量的材料');
          item.details={category:values.category,route:values.route,vertical:values.vertical||'',accessories:values.accessories||'',manualExtra:item.extra,rows,materials:accessories};
          item.extra+=MEPManage.vertical(rows);
          MEP.validateItem(item);
          if(source?.kind==='length'){
            const keys=splitPaths(source.points).flatMap(path=>path.slice(1).map((pt,j)=>MEPSnap.edgeKey(path[j],pt)));
            if(new Set(keys).size!==keys.length||source.points.slice(1).some((pt,j)=>!pt.breakBefore&&MEPSnap.overlaps(source.points.slice(0,j+1),[source.points[j],pt])))throw Error('本笔包含重复线段，请撤回重复段后保存');
            const clashes=p.items.filter(x=>x.id!==item.id&&x.source?.drawingId===source.drawingId&&x.source.kind==='length'&&MEPSnap.overlaps(source.points,x.source.points));
            if(clashes.some(x=>x.name===item.name))throw Error('相同名称已有重叠线段：'+clashes.map(x=>x.name).join('、')+'。请核对，确需独立计量时另建名称');
          }
          if (old) p.items[p.items.indexOf(old)] = item;
          else { p.items.push(item); if (source) points = []; }
          pendingSource = null; selectedItem = item.id; toast(old ? '工程量已更新' : '已加入工程量清单'); break;
        }
        case 'cash': {
          const entry = { id: values.id, name: MEP.required(values.name, '收支说明'), date: values.date, type: values.type, amount: Math.round(MEP.number(values.amount, '金额', .01, 1e9) * 100) / 100 };
          if (!/^\d{4}-\d{2}-\d{2}$/.test(entry.date) || Number.isNaN(Date.parse(entry.date))) throw new Error('请填写有效日期');
          const old = p.cash.find(x => x.id === entry.id); if (old) p.cash[p.cash.indexOf(old)] = entry; else p.cash.push(entry); toast('收支记录已保存'); break;
        }
        default: return;
      }
      $('#dialog').close(); persist(); render();
    } catch (err) { $('#form-error').textContent = err.message; }
  });
  document.addEventListener('input', e => {
    if (e.target.id === 'zoom') { zoom = Number(e.target.value); $('#paper').style.width = zoom + '%'; $('#zoom-label').textContent = zoom + '%'; updateCanvas(); }
    if (e.target.id === 'search') { filter = e.target.value; $('#quantity-table').innerHTML = quantityTable(); }
    if (e.target.closest('#dialog-form')) updateFormula();
  });
  document.addEventListener('change', e => {
    if (e.target.id === 'project-select') {
      const nextId = e.target.value, previousId = state.currentProjectId;
      const change = () => { state.currentProjectId = nextId; drawingId = null; resetDrawing(); filter = ''; systemFilter = ''; persist(); render(); };
      if (points.length) { e.target.value = previousId; return confirmDialog('切换项目？', '当前未保存的测量点会被清除。', change, '切换项目'); }
      change();
    }
    if (e.target.id === 'drawing-select') {
      const nextId = e.target.value, oldId = drawingId;
      const change = () => { drawingId = nextId; resetDrawing(); render(); };
      if (points.length) { e.target.value = oldId; return confirmDialog('切换图纸？', '当前未保存的测量点会被清除。', change, '切换图纸'); }
      change();
    }
    if (e.target.id === 'system-filter') { systemFilter = e.target.value; $('#quantity-table').innerHTML = quantityTable(); }
    if (e.target.id === 'measure-category') {measureCategory=e.target.value;return;}
    if (e.target.id === 'drawing-file') { const file = e.target.files[0]; e.target.value = ''; if (file) importDrawing(file); }
    if (e.target.id === 'backup-file') { const file = e.target.files[0]; e.target.value = ''; if (file) restoreBackup(file); }
  });
  document.addEventListener('keydown', e => {
    if (e.target.closest('input,select,textarea,dialog')) return;
    if ((e.key === 'Enter' || e.key === ' ') && e.target.matches('[data-item]')) { e.preventDefault(); itemDialog(current().items.find(i => i.id === e.target.dataset.item)); return; }
    if (view !== 'drawings') return;
    if (e.key === 'Backspace' && points.length) { e.preventDefault(); points.pop(); updateCanvas(); }
    if (e.key === 'Escape') { points = []; updateCanvas(); }
    if (e.key === 'Enter' && canFinish()) { e.preventDefault(); finishMeasure(); }
  });
  window.addEventListener('beforeunload', e => { if (points.length || savedCount !== saveCount || storageError) { e.preventDefault(); e.returnValue = ''; } });
  async function start() {
    try { db = await connectDB(); const loaded = await dbRead(); if (loaded) { MEP.validateBackup(loaded); loaded.projects.forEach(MEPManage.validate); state = loaded; diskRevision = loaded.revision || 0; } }
    catch { db?.close(); db = null; storageError = '无法读取本地数据，请保留已有备份。当前操作无法保存，使用后请立即导出备份。'; }
    if (!current()) state.currentProjectId = state.projects[0]?.id || null;
    render();
  }
  start();
})();
