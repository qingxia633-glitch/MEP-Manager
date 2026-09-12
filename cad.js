/* Limited DXF 2D preview. All measurements remain user-calibrated raster takeoffs. */
(function(root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.MEPCAD = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function() {
  'use strict';
  const identity = [1,0,0,1,0,0];
  const point = (m,x,y) => [m[0]*x+m[2]*y+m[4],m[1]*x+m[3]*y+m[5]];
  const multiply = (a,b) => [a[0]*b[0]+a[2]*b[1],a[1]*b[0]+a[3]*b[1],a[0]*b[2]+a[2]*b[3],a[1]*b[2]+a[3]*b[3],a[0]*b[4]+a[2]*b[5]+a[4],a[1]*b[4]+a[3]*b[5]+a[5]];
  function cleanText(s) { return s.replace(/\\U\+([0-9a-f]{4})/gi,(_,n)=>String.fromCharCode(parseInt(n,16))).replace(/%%[dD]/g,'°').replace(/%%[pP]/g,'±').replace(/%%[cC]/g,'Ø').replace(/\\P/g,'\n').replace(/\\[ACFHQSTWacfhqstw][^;]*;/g,'').replace(/\\[LOKlonk]/g,'').replace(/[{}]/g,''); }
  function bulgePoints(a,b,bulge=0) {
    if (Math.abs(bulge)<1e-10) return [b];
    const dx=b[0]-a[0],dy=b[1]-a[1],chord=Math.hypot(dx,dy);
    if (!chord) return [];
    const offset=(1-bulge*bulge)/(4*bulge),cx=(a[0]+b[0])/2-dy*offset,cy=(a[1]+b[1])/2+dx*offset;
    const start=Math.atan2(a[1]-cy,a[0]-cx),sweep=4*Math.atan(bulge),r=Math.hypot(a[0]-cx,a[1]-cy),n=Math.max(2,Math.ceil(Math.abs(sweep)/(Math.PI/32)));
    return Array.from({length:n},(_,i)=>{const t=start+sweep*(i+1)/n;return [cx+r*Math.cos(t),cy+r*Math.sin(t)];});
  }
  function parse(text) {
    if (text.length>100*1024*1024) throw new Error('DXF 超过 100 MB，请先把所需图纸另存为单独文件');
    if (text.startsWith('AutoCAD Binary DXF')) throw new Error('请另存为 ASCII 文本 DXF 后再导入');
    const blocks=new Map(),layers=new Map(),objects=new Map(),model=[],papers=new Map(),skipped={},warnings=[];
    let section='',block=null,record=[],at=0,units=0,version='',headerKey='';const extmin={},extmax={};
    function accept(g) {
      if (!g.length) return;
      const type=g[0][1];
      if(type==='SECTION') {section=g.find(p=>p[0]===2)?.[1]||'';}
      if(section==='HEADER') for(const [code,value] of g){if(code===9)headerKey=value;else if(headerKey==='$INSUNITS'&&code===70)units=Number(value);else if(headerKey==='$ACADVER'&&code===1)version=value;else if(headerKey==='$EXTMIN')extmin[code]=Number(value);else if(headerKey==='$EXTMAX')extmax[code]=Number(value);}
      if(type==='ENDSEC'){section='';block=null;return;}
      if(section==='TABLES'&&type==='LAYER'){const d=Object.fromEntries(g);layers.set(d[2],{name:d[2],color:Number(d[62]||7),hidden:Number(d[62])<0||!!(Number(d[70]||0)&1)});}
      if(section==='OBJECTS'&&['DICTIONARY','SPATIAL_FILTER','XRECORD'].includes(type)){const handle=g.find(p=>p[0]===5)?.[1];if(handle)objects.set(handle,g);}
      if(section==='BLOCKS') {
        if(type==='BLOCK'){const d=Object.fromEntries(g);block={name:d[2],x:Number(d[10]||0),y:Number(d[20]||0),xref:!!(Number(d[70]||0)&4),records:[]};blocks.set(block.name,block);}
        else if(type==='ENDBLK')block=null;
        else if(block)block.records.push(g);
      }
      if(section==='ENTITIES'&&!['SECTION','ENDSEC'].includes(type)) {
        const d=Object.fromEntries(g),layout=d[410]||(d[67]==='1'?'布局':'Model');
        if(layout==='Model')model.push(g);else {if(!papers.has(layout))papers.set(layout,[]);papers.get(layout).push(g);}
      }
    }
    function line() { if(at>=text.length)return null; let end=text.indexOf('\n',at);if(end<0)end=text.length;const s=text.slice(at,end).replace(/\r$/,'');at=end+1;return s; }
    while(at<text.length){const a=line(),v=line();if(v===null)break;const code=Number(a.trim());if(!Number.isInteger(code))throw new Error('DXF 组码格式不正确');if(code===0&&record.length){accept(record);record=[];}record.push([code,v]);}accept(record);
    if(!version||!model.length)throw new Error('没有读到可用的模型空间图元；请另存为包含模型空间的 ASCII DXF');
    const primitives=[],bounds=[Infinity,Infinity,-Infinity,-Infinity];let truncated=false,currentClips=[],clipCount=0;
    function skip(type){skipped[type]=(skipped[type]||0)+1;}
    function dictionary(handle,name){let key='';for(const [code,v]of objects.get(handle)||[]){if(code===3)key=v;else if((code===350||code===360)&&key===name)return v;}return null;}
    function clipping(g,world){
      const ext=g.find(p=>p[0]===360)?.[1],filter=dictionary(ext,'ACAD_FILTER'),spatial=dictionary(filter,'SPATIAL'),record=objects.get(spatial);
      if(!record)return null;const d=Object.fromEntries(record);if(Number(d[71])!==1)return null;
      const roundtrip=dictionary(d[360],'ACAD_XREC_ROUNDTRIP'),xrec=objects.get(roundtrip)||[];
      if(xrec.some(p=>String(p[1]).includes('ACAD_INVERTEDCLIP'))||Number(d[72])||Number(d[73])||Number(d[210])||Number(d[220])){skip('不支持的裁剪块');return false;}
      const matrix=record.filter(p=>p[0]===40).map(p=>Number(p[1]));if(matrix.length<24){skip('裁剪矩阵缺失');return false;}
      const inverse=[matrix[0],matrix[4],matrix[1],matrix[5],matrix[3],matrix[7]],transform=multiply(world,inverse);let pts=[];
      for(const [code,v]of record){if(code===10)pts.push([Number(v),0]);else if(code===20&&pts.length)pts.at(-1)[1]=Number(v);}
      if(pts.length===2){const [a,b]=pts;pts=[a,[b[0],a[1]],b,[a[0],b[1]]];}
      if(pts.length<3)return false;pts=pts.map(p=>point(transform,...p));const xs=pts.map(p=>p[0]),ys=pts.map(p=>p[1]);clipCount++;return {points:pts,bounds:[Math.min(...xs),Math.min(...ys),Math.max(...xs),Math.max(...ys)]};
    }
    function add(p){if(primitives.length>=1000000){truncated=true;return;}if(!p.bounds.every(Number.isFinite))return;for(const clip of currentClips){const b=clip.bounds;if(p.bounds[2]<b[0]||p.bounds[0]>b[2]||p.bounds[3]<b[1]||p.bounds[1]>b[3])return;p.bounds=[Math.max(p.bounds[0],b[0]),Math.max(p.bounds[1],b[1]),Math.min(p.bounds[2],b[2]),Math.min(p.bounds[3],b[3])];}if(currentClips.length)p.clips=currentClips;primitives.push(p);bounds[0]=Math.min(bounds[0],p.bounds[0]);bounds[1]=Math.min(bounds[1],p.bounds[1]);bounds[2]=Math.max(bounds[2],p.bounds[2]);bounds[3]=Math.max(bounds[3],p.bounds[3]);}
    function geometry(pts,m,layer,color,closed=false,exact=false){const ps=pts.map(p=>point(m,...p));if(ps.length<2)return;let b=[Infinity,Infinity,-Infinity,-Infinity];for(const [x,y]of ps){b[0]=Math.min(b[0],x);b[1]=Math.min(b[1],y);b[2]=Math.max(b[2],x);b[3]=Math.max(b[3],y);}add({kind:'path',points:ps,layer,color,closed,bounds:b,exact});}
    function expand(records,m=identity,parentLayer='0',parentColor=7,depth=0,chain=new Set(),clips=[]) {
      if(depth>20){skip('嵌套层级过深');return;}
      for(let index=0;index<records.length;index++) {
        currentClips=clips;
        if(truncated)return;
        const g=records[index],d=Object.fromEntries(g),type=d[0];
        const n=(code,fallback=0)=>d[code]===undefined?fallback:Number(d[code]);
        const layer=d[8]==='0'?parentLayer:(d[8]||parentLayer),ld=layers.get(layer);
        if(ld?.hidden||n(60)===1)continue;
        const c=n(62,256),color=c===0?parentColor:c===256?Math.abs(ld?.color||7):Math.abs(c);
        if(['SEQEND','VERTEX','ATTDEF'].includes(type))continue;
        // An arbitrarily tilted OCS cannot be treated as a flat floor plan.
        if((Math.abs(n(210))>1e-8||Math.abs(n(220))>1e-8)&&type!=='LINE'){skip(type+' 非平面坐标');continue;}
        const ocs=n(230,1)<0?multiply(m,[-1,0,0,1,0,0]):m;
        if(type==='INSERT'||type==='DIMENSION') {
          const b=blocks.get(d[2]);if(!b){skip('缺少块定义');continue;}if(b.xref){skip('外部参照');continue;}if(chain.has(b.name)){skip('循环块');continue;}
          const rotation=n(50)*Math.PI/180,cos=Math.cos(rotation),sin=Math.sin(rotation),sx=n(41,1),sy=n(42,1);
          const columns=type==='DIMENSION'?1:Math.max(1,n(70,1)),rows=type==='DIMENSION'?1:Math.max(1,n(71,1));if(columns*rows>10000){skip('过大阵列');continue;}
          for(let r=0;r<rows;r++)for(let col=0;col<columns;col++) {
            const local=type==='DIMENSION'?identity:[cos*sx,sin*sx,-sin*sy,cos*sy,n(10)+cos*(col*n(44))-sin*(r*n(45))-cos*sx*b.x+sin*sy*b.y,n(20)+sin*(col*n(44))+cos*(r*n(45))-sin*sx*b.x-cos*sy*b.y];
            const world=multiply(type==='DIMENSION'?m:ocs,local),clip=type==='INSERT'?clipping(g,world):null;if(clip===false)continue;
            expand(b.records,world,layer,color,depth+1,new Set([...chain,b.name]),clip?[...clips,clip]:clips);
          }
        } else if(type==='LINE') geometry([[n(10),n(20)],[n(11),n(21)]],m,layer,color,false,true);
        else if(type==='LWPOLYLINE'||type==='POLYLINE') {
          let vertices=[];
          if(type==='LWPOLYLINE'){for(const [code,val]of g){if(code===10)vertices.push([Number(val),0,0]);else if(code===20&&vertices.length)vertices.at(-1)[1]=Number(val);else if(code===42&&vertices.length)vertices.at(-1)[2]=Number(val);}}
          else {if(n(70)&(16|64)){skip('POLYMESH');continue;}while(index+1<records.length&&records[index+1][0][1]==='VERTEX'){const v=Object.fromEntries(records[++index]);vertices.push([Number(v[10]||0),Number(v[20]||0),Number(v[42]||0)]);}}
          if(!vertices.length)continue;const closed=!!(n(70)&1),pts=[vertices[0].slice(0,2)],total=vertices.length-(closed?0:1);
          for(let j=0;j<total;j++)pts.push(...bulgePoints(vertices[j],vertices[(j+1)%vertices.length],vertices[j][2]));geometry(pts,ocs,layer,color,closed,vertices.every(v=>Math.abs(v[2])<1e-12));
        } else if(type==='CIRCLE'||type==='ARC'||type==='ELLIPSE') {
          let start=type==='ARC'?n(50)*Math.PI/180:type==='ELLIPSE'?n(41):0,end=type==='ARC'?n(51)*Math.PI/180:type==='ELLIPSE'?n(42,Math.PI*2):Math.PI*2;
          while(end<=start)end+=Math.PI*2;const count=Math.min(512,Math.max(8,Math.ceil((end-start)/(Math.PI/32)))),pts=[];
          for(let j=0;j<=count;j++){const a=start+(end-start)*j/count,co=Math.cos(a),si=Math.sin(a);pts.push(type==='ELLIPSE'?[n(10)+n(11)*co-n(21)*n(40,1)*si,n(20)+n(21)*co+n(11)*n(40,1)*si]:[n(10)+n(40)*co,n(20)+n(40)*si]);}geometry(pts,ocs,layer,color,type==='CIRCLE');
        } else if(['TEXT','MTEXT','ATTRIB'].includes(type)) {
          const value=cleanText(g.filter(p=>p[0]===1||p[0]===3).map(p=>p[1]).join(''));if(!value.trim())continue;
          if(type==='ATTRIB'&&(n(70)&1))continue;
          const base=point(ocs,n(10),n(20)),height=Math.abs(n(40,1))*Math.hypot(ocs[0],ocs[1]),rotation=Math.atan2(ocs[1],ocs[0])+n(50)*(type==='MTEXT'?1:Math.PI/180);
          const width=height*Math.max(...value.split('\n').map(s=>s.length))*(type==='MTEXT'?1:Math.max(.1,n(41,1)));
          add({kind:'text',text:value,x:base[0],y:base[1],height,rotation,layer,color,align:n(72)===1?'center':n(72)===2?'right':'left',bounds:[base[0]-height,base[1]-height,base[0]+width,base[1]+height*value.split('\n').length*1.3]});
        } else if(['SOLID','TRACE','3DFACE'].includes(type))geometry([[n(10),n(20)],[n(11),n(21)],[n(13,n(12)),n(23,n(22))],[n(12),n(22)]],ocs,layer,color,true);
        else if(type==='POINT')continue;
        else skip(type);
      }
    }
    expand(model);
    if(!primitives.length||!bounds.every(Number.isFinite))throw new Error('未读到本版可显示的二维图元');
    if(truncated)warnings.push('图元超过 100 万条，本次预览已截断；请先拆成单张图纸再导入');
    const unsupported=Object.entries(skipped).map(([type,count])=>`${type} ${count} 项`);
    if(unsupported.length)warnings.push('未显示或简化的对象：'+unsupported.join('、'));
    if(papers.size)warnings.push(`文件另有 ${papers.size} 个布局，本版仅显示模型空间`);
    const candidates=primitives.filter(p=>p.kind==='text'&&/(平面图|系统图|设计说明|图纸目录)\s*$/.test(p.text)&&p.text.length<=35&&p.height>0).sort((a,b)=>Number(/SYMB|图名/i.test(b.layer))-Number(/SYMB|图名/i.test(a.layer))||b.height-a.height);
    const names=new Set(),titles=[];for(const p of candidates){if(names.has(p.text))continue;names.add(p.text);titles.push(p);}
    titles.sort((a,b)=>Number(/平面图/.test(b.text))-Number(/平面图/.test(a.text))||a.text.localeCompare(b.text,'zh-CN'));
    const ext=[extmin[10],extmin[20],extmax[10],extmax[20]];
    if(ext.every(Number.isFinite)&&ext[2]>ext[0]&&ext[3]>ext[1]&&Math.max(...ext.map(Math.abs))<1e12)bounds.splice(0,4,...ext);
    return {version,units,primitives,bounds,titles,layers:[...new Set(primitives.map(p=>p.layer))].sort(),warnings,skipped,clipCount};
  }
  const palette=['#536374','#c55650','#ae8637','#44846c','#3b8995','#527daf','#946b9b','#51616a','#8b949b','#acb4b9'];
  function render(ctx,scene,box,width,height,selectedLayer='') {
    ctx.clearRect(0,0,width,height);ctx.fillStyle='#fff';ctx.fillRect(0,0,width,height);
    const scale=Math.min(width/(box[2]-box[0]),height/(box[3]-box[1])),ox=(width-(box[2]-box[0])*scale)/2,oy=(height-(box[3]-box[1])*scale)/2;
    ctx.save();ctx.translate(ox,oy);ctx.scale(scale,-scale);ctx.translate(-box[0],-box[3]);ctx.lineWidth=.8/scale;
    for(const p of scene.primitives){if(selectedLayer&&(selectedLayer.startsWith('@')?!p.layer.includes(selectedLayer.slice(1)):p.layer!==selectedLayer))continue;const b=p.bounds;if(b[2]<box[0]||b[0]>box[2]||b[3]<box[1]||b[1]>box[3])continue;ctx.strokeStyle=ctx.fillStyle=palette[p.color%palette.length];
      if(p.clips){ctx.save();for(const clip of p.clips){ctx.beginPath();ctx.moveTo(...clip.points[0]);for(let j=1;j<clip.points.length;j++)ctx.lineTo(...clip.points[j]);ctx.closePath();ctx.clip();}}
      if(p.kind==='path'){ctx.beginPath();ctx.moveTo(...p.points[0]);for(let j=1;j<p.points.length;j++)ctx.lineTo(...p.points[j]);if(p.closed)ctx.closePath();ctx.stroke();}
      else if(p.height*scale>1){ctx.save();ctx.translate(p.x,p.y);ctx.rotate(p.rotation);ctx.scale(1,-1);ctx.font=`${p.height}px "Microsoft YaHei","Segoe UI",sans-serif`;ctx.textAlign=p.align;ctx.textBaseline='alphabetic';p.text.split('\n').forEach((s,j)=>ctx.fillText(s,0,j*p.height*1.3));ctx.restore();}if(p.clips)ctx.restore();
    }ctx.restore();return {scale,ox,oy};
  }
  function expandedBox(b,padding=.025){const w=Math.max(1,b[2]-b[0]),h=Math.max(1,b[3]-b[1]);return [b[0]-w*padding,b[1]-h*padding,b[2]+w*padding,b[3]+h*padding];}
  function picker(scene,name,onSelect) {
    const overlay=document.createElement('dialog');overlay.className='cad-picker';
    overlay.innerHTML='<div class="cad-head"><div><h2>选出这次要算的图纸</h2><p>滚轮放大 · 拖动平移 · 放大到一张平面图后，点击“使用当前区域”</p></div><button type="button" data-cad="close">关闭</button></div><div class="cad-tools"><button type="button" data-cad="fit">查看整份图</button><button type="button" data-cad="in">放大 +</button><button type="button" data-cad="out">缩小 −</button><select aria-label="CAD 图层"><option value="">全部可见图层</option></select><button class="primary" type="button" data-cad="use">使用当前区域</button></div><div class="cad-grid"><div class="cad-canvas-wrap"><canvas></canvas></div><aside><h3>图中找到的标题</h3><p>点击标题附近查看。系统示意图不可按线长直接算量，请选择平面图。</p><div class="cad-titles"></div></aside></div><div class="cad-notice"></div>';
    document.body.append(overlay);overlay.showModal();
    overlay.querySelector('.cad-notice').textContent=`已读取 ${scene.primitives.length.toLocaleString()} 个可显示图元。${scene.units===0?'文件未指定长度单位，选区后请按尺寸标注定比例。':'CAD 单位仅供参考，选区后仍需按标注定比例。'} 字体及复杂对象为辅助预览，请与原 CAD 核对。${scene.warnings.join('；')}`;
    const select=overlay.querySelector('select');['照明','插座','动力','应急','消防','通讯'].forEach(s=>select.add(new Option('按名称筛选：'+s,'@'+s)));scene.layers.forEach(layer=>select.add(new Option(layer,layer)));
    const titles=overlay.querySelector('.cad-titles');scene.titles.forEach(p=>{const b=document.createElement('button');b.type='button';b.textContent=p.text.slice(0,90);b.onclick=()=>{chosenTitle=p.text;const size=Math.max(p.height*120,1000);box=[p.x-size*.65,p.y-size*.10,p.x+size*.65,p.y+size*.82];draw();};titles.append(b);});
    const canvas=overlay.querySelector('canvas'),ctx=canvas.getContext('2d');let box=expandedBox(scene.bounds),mapping,drag=null,chosenTitle='';
    function draw(){const rect=canvas.parentElement.getBoundingClientRect();canvas.width=Math.max(100,Math.floor(rect.width));canvas.height=Math.max(100,Math.floor(rect.height));mapping=render(ctx,scene,box,canvas.width,canvas.height,select.value);}
    function viewBounds(){return [box[0]-mapping.ox/mapping.scale,box[3]-(canvas.height-mapping.oy)/mapping.scale,box[0]+(canvas.width-mapping.ox)/mapping.scale,box[3]+mapping.oy/mapping.scale];}
    function zoom(factor,cx=(box[0]+box[2])/2,cy=(box[1]+box[3])/2){box=[cx+(box[0]-cx)*factor,cy+(box[1]-cy)*factor,cx+(box[2]-cx)*factor,cy+(box[3]-cy)*factor];draw();}
    function close(){observer.disconnect();overlay.close();overlay.remove();}
    const observer=new ResizeObserver(draw);observer.observe(canvas.parentElement);
    select.onchange=draw;
    overlay.addEventListener('cancel',e=>{e.preventDefault();close();});
    overlay.querySelectorAll('[data-cad]').forEach(b=>b.onclick=()=>{switch(b.dataset.cad){case'close':close();break;case'fit':box=expandedBox(scene.bounds);draw();break;case'in':zoom(.6);break;case'out':zoom(1/.6);break;case'use':{
      const crop=viewBounds(),out=document.createElement('canvas'),aspect=canvas.width/canvas.height;out.width=aspect>=1?4800:Math.round(4800*aspect);out.height=aspect>=1?Math.round(4800/aspect):4800;
      const map=render(out.getContext('2d'),scene,crop,out.width,out.height,select.value);
      const toPixel=q=>[(q[0]-crop[0])*map.scale+map.ox,(crop[3]-q[1])*map.scale+map.oy];
      const frame=[[0,0],[out.width,0],[out.width,out.height],[0,out.height]],segments=[];
      scene.primitives.forEach((p,k)=>{if(!p.exact||p.kind!=='path'||(select.value&&(select.value.startsWith('@')?!p.layer.includes(select.value.slice(1)):p.layer!==select.value)))return;
       if(p.bounds[2]<crop[0]||p.bounds[0]>crop[2]||p.bounds[3]<crop[1]||p.bounds[1]>crop[3])return;
       for(let j=1;j<p.points.length;j++)segments.push({id:k+':'+j,a:toPixel(p.points[j-1]),b:toPixel(p.points[j]),layer:p.layer,clips:[frame,...(p.clips||[]).map(c=>c.points.map(toPixel))]});
      });
      const result={name:(chosenTitle||name.replace(/\.(dwg|dxf)$/i,''))+' · CAD选区',data:out.toDataURL('image/png'),width:out.width,height:out.height,scale:null,cad:{originalName:name,title:chosenTitle,units:scene.units,bounds:crop,layer:select.value,warnings:scene.warnings,previewOnly:true,segments,geometryVersion:1}};
      close();onSelect(result);break;}}});
    canvas.addEventListener('wheel',e=>{e.preventDefault();const r=canvas.getBoundingClientRect(),x=box[0]+(e.clientX-r.left-mapping.ox)/mapping.scale,y=box[3]-(e.clientY-r.top-mapping.oy)/mapping.scale;zoom(e.deltaY>0?1.2:1/1.2,x,y);},{passive:false});
    canvas.addEventListener('pointerdown',e=>{drag={x:e.clientX,y:e.clientY,box:[...box],scale:mapping.scale};canvas.setPointerCapture(e.pointerId);});
    canvas.addEventListener('pointermove',e=>{if(!drag)return;const dx=(e.clientX-drag.x)/drag.scale,dy=(e.clientY-drag.y)/drag.scale;box=[drag.box[0]-dx,drag.box[1]+dy,drag.box[2]-dx,drag.box[3]+dy];draw();});
    canvas.addEventListener('pointerup',()=>drag=null);canvas.addEventListener('pointercancel',()=>drag=null);draw();
  }
  return {parse,render,picker,bulgePoints,multiply,point,cleanText};
});
