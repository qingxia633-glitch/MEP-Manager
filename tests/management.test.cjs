const test=require('node:test'),assert=require('node:assert/strict'),M=require('../management.js'),C=require('../core.js');
test('支路不计跨支路的空白连接',()=>assert.equal(C.distance([{x:0,y:0},{x:3,y:0},{x:10,y:10,breakBefore:true},{x:10,y:14}]),7));
test('材料进场、使用、退料和缺口使用同一个材料编号',()=>{
 const m={id:'m',plan:100},logs=[{materialId:'m',type:'in',quantity:80},{materialId:'m',type:'use',quantity:30},{materialId:'m',type:'return',quantity:5}];
 assert.deepEqual(M.stock(m,logs),{received:80,used:30,returned:5,remaining:45,gap:25});
 assert.throws(()=>M.validateMovement({materialId:'m',type:'use',quantity:46},m,logs),/库存/);
});
test('工资按每次出勤的单价计算；已支付和应发分别记录',()=>{
 assert.deepEqual(M.wages('w',[{workerId:'w',days:1.5,rate:300},{workerId:'w',days:1,rate:400}],[{workerId:'w',amount:200}]),{days:2.5,due:850,paid:200,balance:650});
});
test('密码备份随机加密、可以恢复、密码错误拒绝',async()=>{
 const data={name:'测试工人',card:'6222000011112222'},a=await M.encrypt(data,'test-password'),b=await M.encrypt(data,'test-password');
 assert.notEqual(a.data,b.data);assert.equal(JSON.stringify(a).includes(data.card),false);assert.deepEqual(await M.decrypt(a,'test-password'),data);await assert.rejects(()=>M.decrypt(a,'wrong-password'));
});
test('竖向补量保留高度差、点数和每点根数',()=>assert.equal(M.vertical([{from:3.2,to:1.2,count:4,wires:3}]),24));
test('工资付款必须与项目实际支出一致',()=>{
 const p={workers:[{id:'w',name:'测试'}],payments:[{id:'p',workerId:'w',date:'2026-09-12',amount:200,cashId:'c'}],cash:[{id:'c',amount:100,type:'expense'}]};assert.throws(()=>M.validate(p),/付款/);
});
