const test=require('node:test'),assert=require('node:assert/strict');
const CAD=require('../cad.js');
const rec=(...pairs)=>pairs.flat().join('\n')+'\n';
const line=(x1,y1,x2,y2,layer='0')=>rec(0,'LINE',8,layer,10,x1,20,y1,11,x2,21,y2);
function dxf(entities,blocks='',objects=''){return rec(0,'SECTION',2,'HEADER',9,'$ACADVER',1,'AC1032',9,'$INSUNITS',70,0,0,'ENDSEC')+rec(0,'SECTION',2,'BLOCKS')+blocks+rec(0,'ENDSEC',0,'SECTION',2,'ENTITIES')+entities+rec(0,'ENDSEC',0,'SECTION',2,'OBJECTS')+objects+rec(0,'ENDSEC',0,'EOF');}
test('DXF 读取真实坐标，并保留未指定单位状态',()=>{const s=CAD.parse(dxf(line(0,0,3,4)));assert.equal(s.units,0);assert.deepEqual(s.primitives[0].points,[[0,0],[3,4]]);});
test('块插入应用基点、旋转与缩放',()=>{const b=rec(0,'BLOCK',2,'B',10,1,20,1)+line(1,1,2,1)+rec(0,'ENDBLK');const s=CAD.parse(dxf(rec(0,'INSERT',2,'B',10,10,20,20,41,2,42,2,50,90),b));assert.ok(Math.abs(s.primitives[0].points[1][0]-10)<1e-9);assert.ok(Math.abs(s.primitives[0].points[1][1]-22)<1e-9);});
test('标注类型码不误当阵列数量，避免重复渲染',()=>{const b=rec(0,'BLOCK',2,'D',10,0,20,0)+line(0,0,1,1)+rec(0,'ENDBLK');const s=CAD.parse(dxf(rec(0,'DIMENSION',2,'D',70,32,71,5),b));assert.equal(s.primitives.length,1);});
test('半圆 bulge 保持端点和曲线，非直线近似',()=>{const pts=CAD.bulgePoints([0,0],[10,0],1);assert.ok(Math.abs(pts.at(-1)[0]-10)<1e-8);assert.ok(Math.abs(pts.at(-1)[1])<1e-8);assert.ok(pts.some(p=>Math.abs(p[1])>4.9));});
test('不支持的对象显式报告，不伪装为完整图纸',()=>{const s=CAD.parse(dxf(line(0,0,1,1)+rec(0,'ACAD_PROXY_ENTITY',8,'0')));assert.equal(s.skipped.ACAD_PROXY_ENTITY,1);assert.ok(s.warnings.length);});
test('显示文字清理常见 CAD 格式与 Unicode 标记',()=>assert.equal(CAD.cleanText('{\\C1;照明\\P\\U+706F}'),'照明\n灯'));
test('裁剪块保留裁剪多边形并剔除边界外图元',()=>{
 const b=rec(0,'BLOCK',2,'B',10,0,20,0)+line(0,0,20,20)+line(100,100,200,200)+rec(0,'ENDBLK');
 const insert=rec(0,'INSERT',2,'B',360,'E',10,0,20,0);
 const matrix=[1,0,0,0,0,1,0,0,0,0,1,0];
 const o=rec(0,'DICTIONARY',5,'E',3,'ACAD_FILTER',360,'F',0,'DICTIONARY',5,'F',3,'SPATIAL',360,'S',0,'SPATIAL_FILTER',5,'S',70,2,10,0,20,0,10,10,20,10,71,1,72,0,73,0)+[...matrix,...matrix].map(v=>rec(40,v)).join('');
 const s=CAD.parse(dxf(insert,b,o));assert.equal(s.primitives.length,1);assert.equal(s.clipCount,1);assert.deepEqual(s.primitives[0].bounds,[0,0,10,10]);assert.equal(s.primitives[0].clips[0].points.length,4);
});
test('服务拒绝未授权的本地转换请求',async()=>{
 const handler=require('../cad-server.cjs').createHandler(__dirname),res={writeHead(s){this.status=s;},end(v){this.body=JSON.parse(v);}};
 await handler({url:'/api/cad/convert',method:'POST',headers:{host:'127.0.0.1:4173',origin:'http://evil.example'}},res);assert.equal(res.status,403);
});
