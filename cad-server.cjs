'use strict';
const fs=require('node:fs/promises');
const path=require('node:path');
const crypto=require('node:crypto');
const {spawn}=require('node:child_process');
const token=crypto.randomBytes(24).toString('hex');
let busy=false;
function reply(res,status,data){res.writeHead(status,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'});res.end(JSON.stringify(data));}
function createHandler(root){
  const jobRoot=path.resolve(root,'.cad-jobs');
  const converter=process.env.MEP_ODA_PATH;
  return async function handle(req,res){
    if(!req.url.startsWith('/api/cad/'))return false;
    const validHost=/^(127\.0\.0\.1|localhost):\d+$/.test(req.headers.host||'');
    if(!validHost){reply(res,403,{error:'仅允许本机访问'});return true;}
    if(req.url==='/api/cad/status'&&req.method==='GET'){reply(res,200,{available:!!converter,token});return true;}
    if(req.url!=='/api/cad/convert'||req.method!=='POST'){reply(res,404,{error:'接口不存在'});return true;}
    if(req.headers['x-mep-token']!==token||req.headers.origin!==`http://${req.headers.host}`){reply(res,403,{error:'请从本机小助手界面导入'});return true;}
    if(!converter){reply(res,503,{error:'本地 DWG 转换工具尚未配置。可先在 CAD 中另存为 ASCII DXF，再导入。'});return true;}
    if(busy){reply(res,409,{error:'正在处理另一张 CAD 图纸，请稍后再试'});return true;}
    busy=true;let dir;
    try{
      const chunks=[];let size=0;
      for await(const chunk of req){size+=chunk.length;if(size>30*1024*1024)throw new Error('DWG 超过 30 MB，请先拆分所需图纸');chunks.push(chunk);}
      const bytes=Buffer.concat(chunks);if(!/^AC10\d{2}$/.test(bytes.subarray(0,6).toString('ascii')))throw new Error('文件不是本版支持的 DWG');
      await fs.mkdir(jobRoot,{recursive:true});dir=await fs.mkdtemp(path.join(jobRoot,'job-'));
      const input=path.join(dir,'in'),output=path.join(dir,'out');await fs.mkdir(input);await fs.mkdir(output);await fs.writeFile(path.join(input,'drawing.dwg'),bytes);
      await new Promise((resolve,reject)=>{
        const child=spawn(converter,[input,output,'ACAD2018','DXF','0','0','drawing.dwg'],{windowsHide:true,stdio:'ignore'});
        const timer=setTimeout(()=>{child.kill();reject(new Error('转换超过 90 秒，请拆成单张图纸重试'));},90000);
        child.on('error',()=>{clearTimeout(timer);reject(new Error('无法启动本地 DWG 转换工具，请检查配置'));});
        child.on('close',()=>{clearTimeout(timer);resolve();});
      });
      const converted=path.join(output,'drawing.dxf'),stat=await fs.stat(converted).catch(()=>null);
      if(!stat?.size)throw new Error('没有生成有效 DXF，请先用 CAD 检查图纸能否打开');
      if(stat.size>100*1024*1024)throw new Error('转换结果超过 100 MB，请先拆分所需图纸');
      res.writeHead(200,{'Content-Type':'application/octet-stream','Content-Length':stat.size,'Cache-Control':'no-store'});res.end(await fs.readFile(converted));
    }catch(error){if(!res.headersSent)reply(res,400,{error:error.message});}
    finally{busy=false;if(dir&&path.resolve(dir).startsWith(jobRoot+path.sep))await fs.rm(dir,{recursive:true,force:true}).catch(()=>{});}
    return true;
  };
}
module.exports={createHandler};
