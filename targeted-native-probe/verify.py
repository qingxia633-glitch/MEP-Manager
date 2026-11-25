"""Verify acquisition bytes and provenance; never approve engineering relations."""
import argparse, hashlib, json, ntpath
from pathlib import Path

def owner(raw):
    stack=[]; owners=[]; before_subclass=True
    for code,kind,value in raw:
        if code==102:
            if value=='}':
                if not stack:return None
                stack.pop()
            elif isinstance(value,str) and value.startswith('{'):stack.append(value)
            else:return None
        elif not stack:
            if code==100:before_subclass=False
            elif code==330 and before_subclass:owners.append(value)
    return owners[0] if not stack and len(owners)==1 else None

def reference_role(typ,code,section):
    if section=='{ACAD_REACTORS':return 'reactor_reference'
    if section=='{ACAD_XDICTIONARY' and code==360:return 'extension_dictionary'
    if section:return 'uninterpreted_reference'
    if typ=='GROUP' and code==340:return 'group_member'
    if typ=='LEADER' and code==340:return 'annotation_reference'
    if typ=='DICTIONARY' and code in (350,360):return 'dictionary_entry'
    return 'uninterpreted_reference'

def extension_dictionary(raw):
    stack=[];refs=[];seen=False
    for code,kind,value in raw:
        if code==102:
            if value=='}':
                if not stack:return 'unavailable',None
                stack.pop()
            elif isinstance(value,str) and value.startswith('{'):
                stack.append(value)
                seen |= value=='{ACAD_XDICTIONARY'
            else:return 'unavailable',None
        elif code==360 and stack and stack[-1]=='{ACAD_XDICTIONARY':refs.append(value)
    if stack:return 'unavailable',None
    if not seen:return 'absent',None
    return ('read',refs[0]) if len(refs)==1 and isinstance(refs[0],str) and refs[0] else ('unavailable',None)

def validate_trace(text):
    rows=[line.split('|') for line in text.splitlines() if line.strip()]
    required={'idle_control_before','idle_control_after','load_before','load_after','helpers_before','helpers_after','report_closed','report_output'}
    if not rows or any(len(row)!=4 or row[1]!='0' or row[2]!='0' for row in rows):
        raise ValueError('DBMOD trace dirty/malformed')
    if not required<={row[0] for row in rows}:raise ValueError('DBMOD trace incomplete')
    return rows

def validate(records,request,dwg_hash):
    def require(ok,msg):
        if not ok:raise ValueError(msg)
    require(isinstance(records,list) and len(records)>=2,'truncated report')
    head,tail=records[0],records[-1]
    require(head.get('kind')=='header' and head.get('contract')=='TargetedNativeProbe/1','contract')
    require(bool(request.get('project_id')) and head.get('project_id')==request['project_id'],'project')
    require(ntpath.normcase(ntpath.normpath(head.get('drawing_path','')))==ntpath.normcase(ntpath.normpath(request['drawing_path'])),'drawing')
    seeds=request.get('seed_handles')
    require(isinstance(seeds,list) and seeds and len(set(seeds))==len(seeds) and head.get('seeds')==seeds,'seeds')
    require(dwg_hash==request.get('dwg_sha256_before') and len(dwg_hash)==64,'DWG bytes changed')
    require(tail.get('kind')=='footer' and tail.get('completed') is True,'completion')
    require(type(head.get('dbmod')) is int and head['dbmod']==tail.get('dbmod')==0,'dirty/changed DBMOD')
    nodes=[r for r in records if r.get('kind')=='node'];handles=[r.get('handle') for r in nodes]
    require(len(handles)==len(set(handles)) and all(isinstance(h,str) and h for h in handles),'node identity duplicate/missing')
    require(set(seeds)<=set(handles),'missing seed record')
    require(len(nodes)==tail.get('node_count'),'node count')
    for record in records:
        if record.get('kind')=='dbmod_stage':
            require(type(record.get('before')) is int and record['before']==record.get('after')==0,'stage DBMOD changed')
        if record.get('kind')=='insert_definition':
            require(record.get('identity_status') in ('read','unresolved'),'BTR identity qualification missing')
        if record.get('kind')=='insert_definition' and record.get('identity_status')=='unresolved':
            require(record.get('block_record_handle') is None,'unresolved BTR must not substitute BLOCK')
        if record.get('kind')=='insert_definition' and record.get('identity_status')=='read':
            begin=record.get('block_begin_raw',[]);btr=record.get('block_record_raw',[])
            def values(raw,code):return [x[2] for x in raw if x[0]==code]
            require(values(begin,0)==['BLOCK'] and values(btr,0)==['BLOCK_RECORD'],'BLOCK/BTR type')
            require(values(begin,5)==[record.get('block_begin_handle')] and values(btr,5)==[record.get('block_record_handle')],'BLOCK/BTR handle')
            require(record.get('block_begin_handle')!=record.get('block_record_handle') and owner(begin)==record.get('block_record_handle'),'BLOCK/BTR owner')
            require(values(btr,2)==[record.get('block_name')],'BTR name')
    for n in nodes:
        require(n.get('read_status') in ('read','unavailable','missing'),'read status')
        if n['read_status']=='read':
            raw=n.get('raw');require(isinstance(raw,list) and raw,'raw DXF missing')
            require(all(isinstance(p,list) and len(p)==3 and type(p[0]) is int for p in raw),'raw DXF shape')
            require([p[2] for p in raw if p[0]==5]==[n['handle']],'native handle mismatch')
            require([p[2] for p in raw if p[0]==0]==[n.get('entity_type')],'native type mismatch')
            require(n.get('owner')==owner(raw),'owner/reactor mismatch')
            require(n.get('xdata_status')==('read' if any(p[0]==-3 for p in raw) else 'absent'),'XData status')
            if 'extension_dictionary_status' in n:
                require((n['extension_dictionary_status'],n.get('extension_dictionary_handle'))==extension_dictionary(raw),'extension dictionary evidence')
        else:require(n.get('xdata_status') in ('unavailable','not_acquired'),'unread XData cannot be absent')
    # Complete writing is not complete reverse-association coverage.
    return {'contract':'TargetedNativeProbe/1','input_integrity':'verified','node_count':len(nodes),
      'native_association_status':'acquisition_incomplete','semantic_approval':False,
      'reason':'Raw structural observations require review; arbitrary incoming references are not exhaustively indexed.',
      'coverage':tail.get('coverage','incomplete'),'records':records}

def main():
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);p.add_argument('--request',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();request=json.loads(Path(a.request).read_text(encoding='utf-8-sig'))
    data=Path(a.report).read_bytes();records=[json.loads(l) for l in data.decode('utf-8-sig').splitlines() if l.strip()]
    dwg=Path(request['drawing_path'])
    with dwg.open('rb') as f:dh=hashlib.file_digest(f,'sha256').hexdigest()
    result=validate(records,request,dh)
    trace=None
    if request.get('collector_revision') in (2,3):
        if records[0].get('collector_revision')!=request['collector_revision']:raise ValueError('collector revision mismatch')
        trace=Path(request['dbmod_trace_path']).read_bytes()
        validate_trace(trace.decode('utf-8-sig'))
    out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
    manifest={'manifest_version':'2','report_format':'TargetedNativeProbe/1','encoding':'utf-8-sig',
      'hash_scope':'exact completed report bytes','report_sha256':hashlib.sha256(data).hexdigest(),'report_bytes':len(data),
      'report_identity':records[0],'request_sha256':hashlib.sha256(Path(a.request).read_bytes()).hexdigest(),
      'dwg_sha256_before':request['dwg_sha256_before'],'dwg_sha256_after':dh}
    if trace is not None:manifest['dbmod_trace_sha256']=hashlib.sha256(trace).hexdigest()
    for n,v in [('manifest-v2.json',manifest),('native-evidence.json',result)]:
        with (out/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)

if __name__=='__main__':main()
