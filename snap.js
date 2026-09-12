(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.MEPSnap=api;})(globalThis,function(){
 'use strict';
 const cross=(a,b)=>a[0]*b[1]-a[1]*b[0],sub=(a,b)=>[a[0]-b[0],a[1]-b[1]];
 function inside(q,polygon){let yes=false;for(let i=0,j=polygon.length-1;i<polygon.length;j=i++){
  const a=polygon[j],b=polygon[i],d=sub(b,a),v=sub(q,a);
  if(Math.abs(cross(d,v))<1e-7&&q[0]>=Math.min(a[0],b[0])-1e-8&&q[0]<=Math.max(a[0],b[0])+1e-8&&q[1]>=Math.min(a[1],b[1])-1e-8&&q[1]<=Math.max(a[1],b[1])+1e-8)return true;
  if((a[1]>q[1])!==(b[1]>q[1])&&q[0]<(b[0]-a[0])*(q[1]-a[1])/(b[1]-a[1])+a[0])yes=!yes;
 }return yes;}
 const visible=(s,p)=>(s.clips||[]).every(c=>inside(p,c));
 function intersection(s,t){const d=sub(s.b,s.a),e=sub(t.b,t.a),den=cross(d,e);if(Math.abs(den)<1e-12)return null;
 const v=sub(t.a,s.a),u=cross(v,e)/den,w=cross(v,d)/den;
 if(u<0||u>1||w<0||w>1)return null;const p=[s.a[0]+u*d[0],s.a[1]+u*d[1]];return visible(s,p)&&visible(t,p)?p:null;}
 function index(segments){const cells=new Map(),long=[],size=64;
  segments.forEach(s=>{const x0=Math.floor(Math.min(s.a[0],s.b[0])/size),x1=Math.floor(Math.max(s.a[0],s.b[0])/size),y0=Math.floor(Math.min(s.a[1],s.b[1])/size),y1=Math.floor(Math.max(s.a[1],s.b[1])/size);
   if((x1-x0+1)*(y1-y0+1)>256){long.push(s);return;}
   for(let x=x0;x<=x1;x++)for(let y=y0;y<=y1;y++){const k=x+','+y;if(!cells.has(k))cells.set(k,[]);cells.get(k).push(s);}
  });return {cells,long,size};
 }
 function nearby(idx,p,r){const out=new Set(idx.long);for(let x=Math.floor((p.x-r)/idx.size);x<=Math.floor((p.x+r)/idx.size);x++)for(let y=Math.floor((p.y-r)/idx.size);y<=Math.floor((p.y+r)/idx.size);y++)for(const s of idx.cells.get(x+','+y)||[])out.add(s);
  return [...out].filter(s=>Math.max(s.a[0],s.b[0])>=p.x-r&&Math.min(s.a[0],s.b[0])<=p.x+r&&Math.max(s.a[1],s.b[1])>=p.y-r&&Math.min(s.a[1],s.b[1])<=p.y+r);
 }
 function find(idx,p,r){const near=nearby(idx,p,r);let best=null,dist=r;function offer(q,kind){const d=Math.hypot(q[0]-p.x,q[1]-p.y);if(d<=dist&&(!best||d<dist-1e-10)){best={x:q[0],y:q[1],kind};dist=d;}}
  for(const s of near)for(const q of [s.a,s.b])if(visible(s,q))offer(q,'端点');
  for(let i=0;i<near.length;i++)for(let j=i+1;j<near.length;j++){const q=intersection(near[i],near[j]);if(q)offer(q,'交点');}
  return best;
 }
 function pick(idx,p,r){let best=null,dist=r;for(const s of nearby(idx,p,r)){const d=sub(s.b,s.a),l=d[0]**2+d[1]**2;if(!l)continue;const u=Math.max(0,Math.min(1,((p.x-s.a[0])*d[0]+(p.y-s.a[1])*d[1])/l)),q=[s.a[0]+u*d[0],s.a[1]+u*d[1]],dd=Math.hypot(q[0]-p.x,q[1]-p.y);if(dd<dist&&visible(s,q)&&visible(s,s.a)&&visible(s,s.b)){best=s;dist=dd;}}return best;}
 const edgeKey=(a,b)=>{const aa=[a.x,a.y].map(n=>n.toFixed(7)).join(','),bb=[b.x,b.y].map(n=>n.toFixed(7)).join(',');return aa<bb?aa+';'+bb:bb+';'+aa;};
 function networkLength(paths){const seen=new Set();let sum=0;for(const path of paths)for(let i=1;i<path.length;i++){const a=path[i-1],b=path[i],key=edgeKey(a,b);if(!seen.has(key)){sum+=Math.hypot(b.x-a.x,b.y-a.y);seen.add(key);}}return sum;}
 function overlaps(first,second){for(let i=1;i<first.length;i++)for(let j=1;j<second.length;j++){
  if(first[i].breakBefore||second[j].breakBefore)continue;
  const a=first[i-1],b=first[i],c=second[j-1],d=second[j],v=[b.x-a.x,b.y-a.y],len=Math.hypot(...v);if(len<1e-8)continue;
  if(Math.abs(cross(v,[c.x-a.x,c.y-a.y]))/len>1e-7||Math.abs(cross(v,[d.x-a.x,d.y-a.y]))/len>1e-7)continue;
  const u=((c.x-a.x)*v[0]+(c.y-a.y)*v[1])/len,w=((d.x-a.x)*v[0]+(d.y-a.y)*v[1])/len;
  if(Math.min(len,Math.max(u,w))-Math.max(0,Math.min(u,w))>1e-7)return true;
 }return false;}
 function bridge(a,b){if(overlaps(a,b))throw Error('线段已重叠，不需要补线');let best=null,dist=Infinity;for(const p of [a[0],a.at(-1)])for(const q of [b[0],b.at(-1)]){const d=Math.hypot(p.x-q.x,p.y-q.y);if(d<dist){best=[{x:p.x,y:p.y},{x:q.x,y:q.y}];dist=d;}}if(dist<1e-7)throw Error('线段已相连');return best;}
 return {inside,visible,intersection,index,find,pick,edgeKey,networkLength,overlaps,bridge};
});
