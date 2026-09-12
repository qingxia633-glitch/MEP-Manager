(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.MEPManage=api;})(globalThis,function(){
 'use strict';
 function num(n,max=1e9){if(typeof n!=='number'||!Number.isFinite(n)||n<0||n>max)throw Error('数量或金额格式不正确');return n;}
 const money=n=>Math.round(n*100)/100;
 function stock(m,logs){let received=0,used=0,returned=0;for(const e of logs.filter(x=>x.materialId===m.id)){if(e.type==='in')received+=num(e.quantity);else if(e.type==='use')used+=num(e.quantity);else if(e.type==='return')returned+=num(e.quantity);else throw Error('材料流水类型不正确');}return {received,used,returned,remaining:received-used-returned,gap:Math.max(0,num(m.plan)-received+returned)};}
 function validateMovement(e,m,logs){num(e.quantity);if(!e.quantity)throw Error('数量需要大于零');if(!['in','use','return'].includes(e.type))throw Error('材料流水类型不正确');if(e.type!=='in'&&e.quantity>stock(m,logs).remaining+1e-9)throw Error('数量超过当前库存，请先核对进场记录');return e;}
 function wages(id,attendance,payments){const list=attendance.filter(x=>x.workerId===id),days=list.reduce((s,x)=>s+num(x.days,31),0),due=money(list.reduce((s,x)=>s+num(x.days,31)*num(x.rate,1e6),0)),paid=money(payments.filter(x=>x.workerId===id).reduce((s,x)=>s+num(x.amount),0));return {days,due,paid,balance:money(due-paid)};}
 function vertical(rows){return rows.reduce((sum,r)=>{for(const k of ['from','to','count','wires'])num(r[k]);return sum+Math.abs(r.from-r.to)*r.count*r.wires;},0);}
 function validate(p){for(const k of ['materials','movements','workers','attendance','payments']){if(p[k]===undefined)continue;if(!Array.isArray(p[k])||p[k].length>50000)throw Error('台账记录格式不正确');}
  for(const i of p.items||[])if(i.details){const d=i.details;if(!Array.isArray(d.rows)||!Array.isArray(d.materials)||d.rows.length>1000||d.materials.length>1000)throw Error('补充明细格式不正确');num(d.manualExtra);if(Math.abs(d.manualExtra+vertical(d.rows)-i.extra)>1e-7)throw Error('竖向明细与补充数量不一致');for(const a of d.materials){num(a.quantity);if(typeof a.name!=='string'||typeof a.spec!=='string'||typeof a.unit!=='string')throw Error('附属材料格式不正确');}}
  const mats=p.materials||[],workers=p.workers||[];for(const m of mats){num(m.plan);if(!m.id||typeof m.name!=='string'||!m.name.trim()||typeof m.spec!=='string'||typeof m.unit!=='string'||typeof m.system!=='string')throw Error('材料资料不完整');}
  for(const w of workers){if(!w.id||typeof w.name!=='string'||!w.name.trim())throw Error('人员资料不完整');for(const k of ['name','trade','phone','identity','address','bank','account'])if(w[k]!==undefined&&(typeof w[k]!=='string'||w[k].length>500))throw Error('人员资料格式不正确');}
  for(const list of [mats,workers,p.movements||[],p.attendance||[],p.payments||[]])if(new Set(list.map(x=>x.id)).size!==list.length)throw Error('台账编号重复');
  for(const e of p.movements||[]){if(!mats.some(m=>m.id===e.materialId))throw Error('材料来源丢失');num(e.quantity);if(!['in','use','return'].includes(e.type))throw Error('材料流水类型不正确');}
  for(const e of [...(p.attendance||[]),...(p.payments||[])]){if(!workers.some(w=>w.id===e.workerId))throw Error('人员来源丢失');if(e.days!==undefined){num(e.days,31);num(e.rate,1e6);}else num(e.amount);}
  for(const e of p.payments||[]){const cash=(p.cash||[]).find(c=>c.id===e.cashId);if(!cash||cash.type!=='expense'||cash.amount!==e.amount)throw Error('工资付款与收支记录不一致');}
  for(const m of mats)if(stock(m,p.movements||[]).remaining<-.000001)throw Error('材料库存不能小于零');
  for(const e of [...(p.movements||[]),...(p.attendance||[]),...(p.payments||[])])if(!/^\d{4}-\d{2}-\d{2}$/.test(e.date)||!Number.isFinite(Date.parse(e.date)))throw Error('台账日期不正确');return p;
 }
 const encode=a=>{let s='';for(let i=0;i<a.length;i+=16384)s+=String.fromCharCode(...a.subarray(i,i+16384));return btoa(s);};
 const decode=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
 async function key(password,salt){const c=globalThis.crypto;if(!c?.subtle)throw Error('此浏览器不能加密，请从本机服务打开');const raw=await c.subtle.importKey('raw',new TextEncoder().encode(password),'PBKDF2',false,['deriveKey']);return c.subtle.deriveKey({name:'PBKDF2',salt,iterations:210000,hash:'SHA-256'},raw,{name:'AES-GCM',length:256},false,['encrypt','decrypt']);}
 async function encrypt(data,password){if(typeof password!=='string'||password.length<8)throw Error('备份密码至少8位');const salt=crypto.getRandomValues(new Uint8Array(16)),iv=crypto.getRandomValues(new Uint8Array(12)),k=await key(password,salt);const bytes=await crypto.subtle.encrypt({name:'AES-GCM',iv},k,new TextEncoder().encode(JSON.stringify(data)));return {format:'mep-encrypted',version:1,salt:encode(salt),iv:encode(iv),data:encode(new Uint8Array(bytes))};}
 async function decrypt(envelope,password){if(envelope.format!=='mep-encrypted'||envelope.version!==1||typeof envelope.data!=='string'||envelope.data.length>210e6)throw Error('不支持的加密备份');try{const salt=decode(envelope.salt),iv=decode(envelope.iv);if(salt.length!==16||iv.length!==12)throw Error();const k=await key(password,salt),bytes=await crypto.subtle.decrypt({name:'AES-GCM',iv},k,decode(envelope.data));return JSON.parse(new TextDecoder().decode(bytes));}catch{throw Error('密码不正确，或备份文件已损坏');}}
 return {stock,validateMovement,wages,vertical,validate,encrypt,decrypt};
});
