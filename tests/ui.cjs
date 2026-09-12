/* Optional browser integration checks. Install playwright or set PLAYWRIGHT_MODULE. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const MEP = require('../core.js');
const output = path.resolve(__dirname, '../test-results');
const url = process.env.MEP_TEST_URL || 'http://127.0.0.1:4173';
const checks = [];
const check = name => { checks.push(name); console.log('PASS ' + name); };
async function readState(page) {
  return page.evaluate(() => new Promise((resolve, reject) => { const open = indexedDB.open('mep-manager-v1', 1); open.onsuccess = () => { const db = open.result; const req = db.transaction('workspace').objectStore('workspace').get('state'); req.onsuccess = () => { db.close(); resolve(req.result); }; req.onerror = () => reject(req.error); }; }));
}
async function waitSaved(page) { await page.waitForFunction(() => document.querySelector('.save-status')?.textContent === '已保存在此设备'); }
async function fill(page, name, value) { await page.locator(`#dialog-form [name="${name}"]`).fill(String(value)); }
async function submit(page) { await page.locator('#dialog-form button[type="submit"]').click(); await page.waitForFunction(() => !document.querySelector('#dialog').open); await waitSaved(page); }
async function point(page, x, y) { const b = await page.locator('#plan').boundingBox(); await page.mouse.click(b.x + x / 1000 * b.width, b.y + y / 700 * b.height); }
(async () => {
  await fs.mkdir(output, { recursive: true });
  const browser = await chromium.launch({ headless: true, ...(process.env.MEP_BROWSER_EXECUTABLE ? { executablePath: process.env.MEP_BROWSER_EXECUTABLE } : {}) });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1040 }, acceptDownloads: true });
  const page = await context.newPage(), errors = [];
  page.on('pageerror', err => errors.push(err.message));
  page.on('dialog', d => d.accept());
  try {
    await page.goto(url); await page.getByRole('button', { name: '创建第一个项目' }).waitFor();
    await page.screenshot({ path: path.join(output, 'welcome.png'), fullPage: true });
    check('首次打开为空项目，未混入示例数据');
    await page.getByRole('button', { name: '创建第一个项目' }).click(); await fill(page, 'name', '验收项目'); await fill(page, 'location', '1 号楼'); await submit(page);
    assert.equal((await readState(page)).projects[0].name, '验收项目');
    await page.locator('.nav [data-view="drawings"]').click();
    const png = await page.evaluate(() => { const c = document.createElement('canvas'); c.width = 1000; c.height = 700; const x = c.getContext('2d'); x.fillStyle = 'white'; x.fillRect(0, 0, 1000, 700); x.strokeStyle = '#888'; x.strokeRect(100, 100, 800, 500); x.fillStyle = '#555'; x.font = '22px sans-serif'; x.fillText('TEST PLAN / 4000 mm', 110, 80); return c.toDataURL('image/png').split(',')[1]; });
    await page.locator('#drawing-file').setInputFiles({ name: '验收图纸.png', mimeType: 'image/png', buffer: Buffer.from(png, 'base64') });
    await page.locator('#plan').waitFor(); await waitSaved(page);
    assert.equal(await page.locator('[data-tool="length"]').isDisabled(), true);
    await page.locator('[data-tool="calibrate"]').click(); await point(page, 100, 100); await point(page, 500, 100);
    await page.locator('[data-action="finish-measure"]').click(); await fill(page, 'meters', '4'); await submit(page);
    // Real mouse coordinates are rounded to screen pixels; allow two pixels of input tolerance.
    assert.ok(Math.abs((await readState(page)).projects[0].drawings[0].scale - .01) < .00005);
    check('图片上传与真实尺寸标定');
    await point(page, 100, 200); await point(page, 500, 200); await point(page, 500, 500);
    await page.locator('[data-action="finish-measure"]').click(); await fill(page, 'name', '测试给水管'); await fill(page, 'spec', 'PPR DN25'); await fill(page, 'copies', 2); await fill(page, 'extra', 1); await fill(page, 'allowance', 5); await fill(page, 'price', 10); await fill(page, 'location', '1 层'); await submit(page);
    let saved = await readState(page), first = saved.projects[0].items[0];
    assert.ok(Math.abs(first.base - 7) < .04); assert.ok(Math.abs(MEP.calculate(first).quantity - 15) < .08); assert.ok(Math.abs(MEP.calculate(first).cost - 157.5) < .85);
    check('折线测量、重复份数、预留及损耗计算');
    await page.locator('[data-tool="count"]').click(); await point(page, 200, 300); await point(page, 300, 300); await point(page, 400, 300); await point(page, 600, 300); await page.locator('[data-action="undo-point"]').click();
    await page.locator('[data-action="finish-measure"]').click(); await fill(page, 'name', '测试插座'); await fill(page, 'spec', '五孔'); await submit(page);
    assert.equal((await readState(page)).projects[0].items[1].base, 3); check('设备点数与撤回');
    await page.locator('.nav [data-view="quantities"]').click(); await page.locator('#search').fill('DN25'); assert.equal(await page.locator('tbody tr').count(), 1);
    await page.locator('tbody [data-action="edit-item"]').click(); assert.equal(await page.locator('[name="base"]').getAttribute('readonly'), ''); await fill(page, 'price', 20); await submit(page);
    const csvEvent = page.waitForEvent('download'); await page.locator('[data-action="export-csv"]').click(); const csvFile = await csvEvent; await csvFile.saveAs(path.join(output, 'takeoff.csv')); const csv = await fs.readFile(path.join(output, 'takeoff.csv'), 'utf8'); assert.ok(csv.includes('测试给水管')); assert.ok(!csv.includes('测试插座')); check('筛选、编辑及按当前筛选导出 CSV');
    await page.locator('[data-action="locate"]').click(); assert.equal(await page.locator('.highlight').count(), 1); check('清单记录定位回图纸');
    await page.locator('[data-tool="calibrate"]').click(); await point(page, 100, 100); await point(page, 500, 100); await page.locator('[data-action="finish-measure"]').click(); await fill(page, 'meters', 8); await submit(page);
    saved = await readState(page); assert.ok(Math.abs(saved.projects[0].drawings[0].scale - .02) < .0001); assert.equal(saved.projects[0].items[0].source.scale, first.source.scale); check('重新标定保留历史工程量及测量比例');
    await page.locator('[data-action="delete-drawing"]').click(); assert.ok((await page.locator('#toast').textContent()).includes('已有工程量来源')); check('禁止删除仍被工程量引用的图纸');
    await page.locator('.nav [data-view="cash"]').click(); await page.locator('[data-action="new-cash"]').first().click(); await fill(page, 'name', '首批采购'); await fill(page, 'amount', '1250.50'); await submit(page);
    await page.locator('tbody [data-action="edit-cash"]').click(); await fill(page, 'amount', '1300'); await submit(page); assert.equal((await readState(page)).projects[0].cash[0].amount, 1300); check('实际收支新增与编辑');
    await page.reload(); await page.locator('h1').waitFor(); saved = await readState(page); assert.equal(saved.projects[0].items.length, 2); assert.equal(saved.projects[0].drawings.length, 1); check('刷新后图纸、测量点与收支完整保留');
    const backupEvent = page.waitForEvent('download'); await page.locator('[data-action="backup"]').click(); const backupFile = await backupEvent; const backupPath = path.join(output, 'backup.json'); await backupFile.saveAs(backupPath); const backup = MEP.validateBackup(JSON.parse(await fs.readFile(backupPath, 'utf8'))); assert.equal(backup.projects[0].items.length, 2);
    const restoredContext = await browser.newContext({ viewport: { width: 1440, height: 1040 } }), restored = await restoredContext.newPage(); restored.on('dialog', d => d.accept()); await restored.goto(url); await restored.locator('[data-action="restore"]').waitFor(); await restored.locator('#backup-file').setInputFiles(backupPath); await restored.locator('[data-action="confirm"]').click(); await waitSaved(restored); const restoredState = await readState(restored); assert.equal(restoredState.projects[0].items.length, 2); assert.notEqual(restoredState.projects[0].id, backup.projects[0].id); assert.equal(restoredState.projects[0].items[0].source.drawingId, restoredState.projects[0].drawings[0].id); check('完整备份在全新浏览器环境恢复');
    await restored.locator('#backup-file').setInputFiles(backupPath); await restored.locator('[data-action="confirm"]').click(); await waitSaved(restored); assert.equal((await readState(restored)).projects.length, 2); check('重复恢复保留原项目并创建副本');
    await page.locator('.nav [data-view="quantities"]').click(); await page.locator('#search').fill(''); await page.locator('tbody [data-action="delete-item"]').first().click(); await page.locator('[data-action="close-dialog"]').filter({ hasText: '取消' }).click(); assert.equal((await readState(page)).projects[0].items.length, 2); check('删除确认可以取消');
    const demoContext = await browser.newContext({ viewport: { width: 1440, height: 1040 } }), demo = await demoContext.newPage(); demo.on('pageerror', err => errors.push(err.message)); await demo.goto(url); await demo.locator('[data-action="demo"]').click(); await waitSaved(demo); MEP.validateBackup(await readState(demo)); await demo.waitForFunction(() => !document.querySelector('#toast').classList.contains('show')); await demo.screenshot({ path: path.join(output, 'overview.png'), fullPage: true });
    await demo.locator('.nav [data-view="drawings"]').click(); await demo.screenshot({ path: path.join(output, 'drawings.png'), fullPage: true }); await demo.locator('.nav [data-view="quantities"]').click(); await demo.screenshot({ path: path.join(output, 'quantities.png'), fullPage: true });
    await demo.setViewportSize({ width: 390, height: 844 }); await demo.locator('.nav [data-view="overview"]').click(); await demo.screenshot({ path: path.join(output, 'mobile.png'), fullPage: true }); assert.equal(await demo.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), true); check('示例数据有效，桌面与手机布局无页面横向溢出');
    const second = await context.newPage(); second.on('dialog', d => d.accept()); await second.goto(url); await second.locator('h1').waitFor(); await page.locator('.nav [data-view="overview"]').click(); await page.locator('[data-action="edit-project"]').click(); await fill(page, 'name', '验收项目已更新'); await submit(page); await second.locator('[data-action="edit-project"]').click(); await fill(second, 'name', '旧窗口冲突修改'); await second.locator('button[type="submit"]').click(); await second.locator('#storage-alert').waitFor(); assert.ok((await second.locator('#storage-alert').textContent()).includes('其他窗口')); assert.equal((await readState(page)).projects[0].name, '验收项目已更新'); check('多个窗口写入冲突不会覆盖已保存数据');
    const fileContext = await browser.newContext(), filePage = await fileContext.newPage(); filePage.on('pageerror', err => errors.push(err.message)); await filePage.goto(pathToFileURL(path.resolve(__dirname, '../index.html')).href); await filePage.getByRole('button', { name: '创建第一个项目' }).waitFor(); check('直接双击 HTML 的离线入口可以加载');
    await filePage.getByRole('button', { name: '创建第一个项目' }).click(); await fill(filePage, 'name', '离线项目'); await submit(filePage); await filePage.reload(); await filePage.locator('h1').waitFor(); assert.equal((await readState(filePage)).projects[0].name, '离线项目'); check('离线 HTML 入口支持保存并重新打开');
    const failPage = await restoredContext.newPage(); failPage.on('dialog', d => d.accept()); await failPage.goto(url); await failPage.locator('h1').waitFor(); await failPage.evaluate(() => { const original = IDBDatabase.prototype.transaction; IDBDatabase.prototype.transaction = function (stores, mode, ...rest) { if (mode === 'readwrite') throw new DOMException('Full', 'QuotaExceededError'); return original.call(this, stores, mode, ...rest); }; }); await failPage.locator('[data-action="edit-project"]').click(); await fill(failPage, 'name', '容量不足未保存'); await failPage.locator('button[type="submit"]').click(); await failPage.locator('#storage-alert').waitFor(); assert.ok((await failPage.locator('#storage-alert').textContent()).includes('保存失败')); check('存储失败时明确提示备份，不虚报保存成功');
    assert.deepEqual(errors, []); check('浏览器未出现未捕获的脚本错误');
    await fs.writeFile(path.join(output, 'ui-report.json'), JSON.stringify({ passed: checks.length, checks, errors }, null, 2));
    console.log('All ' + checks.length + ' browser checks passed.');
  } catch (error) { await page.screenshot({ path: path.join(output, 'failure.png'), fullPage: true }); throw error; }
  finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
