const test=require('node:test'),assert=require('node:assert/strict'),S=require('../snap.js');
const seg=(id,a,b,clips=[])=>({id,a,b,clips});
test('大图超过12000端点仍可捕捉内部交点',()=>{
 const lines=Array.from({length:13000},(_,i)=>seg('far'+i,[10000+i,10000],[10000+i,11000]));
 lines.push(seg('h',[0,5],[10,5]),seg('v',[5,0],[5,10]));
 assert.deepEqual(S.find(S.index(lines),{x:5.2,y:5.1},.5),{x:5,y:5,kind:'交点'});
});
test('捕捉容差按屏幕像素换算，不随缩放误差漂移',()=>{
 const idx=S.index([seg('a',[10,10],[100,10])]);
 assert.equal(S.find(idx,{x:12,y:11},3).kind,'端点');assert.equal(S.find(idx,{x:14,y:10},3),null);
});
test('裁剪外端点和交点不能捕捉',()=>{
 const clip=[[0,0],[5,0],[5,5],[0,5]];
 const idx=S.index([seg('a',[-10,2],[10,2],[clip]),seg('b',[8,0],[8,4])]);
 assert.equal(S.find(idx,{x:8,y:2},.1),null);assert.equal(S.find(idx,{x:10,y:2},.1),null);
});
test('多支路线长度不包含支路之间的连接，公共边仅计一次',()=>{
 assert.equal(S.networkLength([[{x:0,y:0},{x:3,y:0}],[{x:3,y:0},{x:3,y:4}],[{x:3,y:0},{x:0,y:0}]]),7);
});
test('重叠检查发现部分覆盖，端点相接不算重复',()=>{
 assert.equal(S.overlaps([{x:0,y:0},{x:10,y:0}],[{x:5,y:0},{x:15,y:0}]),true);
 assert.equal(S.overlaps([{x:0,y:0},{x:10,y:0}],[{x:10,y:0},{x:15,y:0}]),false);
});
test('断线连接取最近端点，重叠段拒绝补线',()=>{
 assert.deepEqual(S.bridge([{x:0,y:0},{x:2,y:0}],[{x:4,y:0},{x:7,y:0}]),[{x:2,y:0},{x:4,y:0}]);
 assert.throws(()=>S.bridge([{x:0,y:0},{x:5,y:0}],[{x:4,y:0},{x:7,y:0}]),/重叠/);
});
