"""Runtime private input-map entry; source inputs are never rewritten."""
import argparse,json,hashlib
from pathlib import Path
from references import scan,validate_registry
from annotations import load_report
from report_manifest import verify_manifest

def run(mapping):
    registry_path=Path(mapping['registry_path']);rb=registry_path.read_bytes()
    if hashlib.sha256(rb).hexdigest()!=mapping.get('registry_sha256'):raise ValueError('Registry hash mismatch')
    registry=json.loads(rb.decode('utf-8-sig'));validate_registry(registry)
    if mapping.get('project_id')!=registry['project_id']:raise ValueError('Project mismatch')
    if not isinstance(mapping.get('inputs'),list) or not mapping['inputs']:raise ValueError('Nonempty input list required')
    contexts=[];originals=[(registry_path,rb)]
    for item in mapping['inputs']:
        p=Path(item['report_path']);mp=Path(item['manifest_path']);data=p.read_bytes();mb=mp.read_bytes()
        manifest=json.loads(mb.decode('utf-8-sig'));enc=manifest['encoding']
        verify_manifest(data,p,enc,manifest)
        raw=data.decode(enc)
        import re
        if re.findall(r'^ReadErrorCount=(.*?)\r?$',raw,re.M)!=['0'] or not raw.rstrip().endswith('END_OF_REPORT: scan finished. Inspect errors and scope limitations before interpreting results.'):
            raise ValueError('Incomplete/error-bearing report')
        contexts.append(load_report(p,mapping['project_id'],encoding=enc,manifest=manifest))
        originals.extend([(p,data),(mp,mb)])
    result=scan(registry,contexts)
    if any(p.read_bytes()!=data for p,data in originals):raise ValueError('Input changed during scan')
    result['registry_sha256']=mapping['registry_sha256']
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input-map',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();result=run(json.loads(Path(a.input_map).read_text(encoding='utf-8-sig')))
    with Path(a.output).open('x',encoding='utf-8',newline='\n') as f:
        json.dump(result,f,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
