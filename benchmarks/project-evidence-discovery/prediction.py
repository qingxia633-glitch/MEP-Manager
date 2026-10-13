"""Label-free Prediction worker. No ledger/scorer imports or historical answers."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'project-evidence-discovery'))
from report_manifest import verify_manifest

REQUEST_KEYS = {'case_id', 'project_id', 'drawing', 'target_identity',
                'report_sha256', 'acquisition_scope', 'report_path', 'manifest_path'}
IDENTITY_KEYS = {'project_id', 'drawing', 'snapshot_id', 'handle', 'parent_path', 'entity_type', 'child'}
SCOPE = {'mode':'ModelSpaceTopLevelAllLayers', 'model_space_top_level':'included',
         'nested_blocks':'not expanded', 'xref_contents':'not expanded', 'layouts':'not included'}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def freeze(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def validate_request(r):
    if not isinstance(r, dict) or set(r) != REQUEST_KEYS:
        raise ValueError('Prediction accepts only label-free request fields')
    if not re.fullmatch(r'[A-Za-z0-9_-]+', r['case_id']):
        raise ValueError('Invalid case_id')
    for k in ('project_id','drawing','report_path','manifest_path'):
        if not isinstance(r[k],str) or not r[k].strip():raise ValueError('Missing '+k)
    if not re.fullmatch('[0-9a-f]{64}',r['report_sha256']):raise ValueError('Invalid report hash')
    t=r['target_identity']
    if not isinstance(t,dict) or set(t)-IDENTITY_KEYS or not IDENTITY_KEYS-{'child'} <= set(t):
        raise ValueError('Invalid target identity fields')
    if t['project_id']!=r['project_id'] or t['drawing']!=r['drawing'] or t['snapshot_id']!=r['report_sha256']:
        raise ValueError('Identity disagreement')
    if t['parent_path'] != []:raise ValueError('Only top-level targets supported')
    if not isinstance(t['handle'],str) or not t['handle'] or t['entity_type'] not in ('INSERT','LINE','LWPOLYLINE'):
        raise ValueError('Invalid target')
    if 'child' in t:
        c=t['child']
        if not isinstance(c,dict) or set(c)!={'handle','entity_type','parent_path'}:
            raise ValueError('Invalid child identity fields')
        if c['entity_type']!='ATTRIB' or not isinstance(c['handle'],str) or not c['handle'] or not isinstance(c['parent_path'],list) or not all(isinstance(x,str) and x for x in c['parent_path']):
            raise ValueError('Invalid child identity')
    if r['acquisition_scope']!=SCOPE:raise ValueError('Unsupported acquisition scope')


def predict(request, discover_fn=None):
    validate_request(request)
    r=request
    result={'case_id':r['case_id'], 'target_identity':r['target_identity'],
            'input_report_sha256':None, 'fresh_machine_result':None}
    report,manifest=Path(r['report_path']),Path(r['manifest_path'])
    if not report.is_file() or not manifest.is_file():
        return dict(result,case_status='input_unavailable',reason='report or manifest missing')
    try:
        data=report.read_bytes(); manifest_data=manifest.read_bytes()
        actual=hashlib.sha256(data).hexdigest();result['input_report_sha256']=actual
        if actual!=r['report_sha256']:raise ValueError('Report hash differs from pinned input')
        m=json.loads(manifest_data.decode('utf-8-sig'));encoding=m['encoding']
        verified=verify_manifest(data,report,encoding,m);identity=verified['report_identity']
        drawing=re.split(r'[\\/]+',identity['drawing'])[-1]
        if drawing!=r['drawing']:raise ValueError('Drawing identity mismatch')
        if identity['extractor_version']!='2.4-leader-evidence-v1':raise ValueError('Unsupported exporter')
        if (identity['acquisition_mode']!=SCOPE['mode'] or
            identity['model_space_top_level']!=SCOPE['model_space_top_level'] or
            identity['nested_blocks']!=SCOPE['nested_blocks']):raise ValueError('Incompatible acquisition scope')
        text=data.decode(encoding)
        header=text.split('EntityHandle=',1)[0]
        for field,value in [('AllLayers','included; including off/frozen'),
                            ('XrefContents','not expanded'),('PaperSpaceLayouts','not included')]:
            if not re.search(r'^'+field+'="'+re.escape(value)+r'"\s*$',header,re.M):
                raise ValueError('Incompatible acquisition field: '+field)
        if not re.search(r'^ReadErrorCount=0\s*$',text,re.M) or not text.rstrip().endswith(
            'END_OF_REPORT: scan finished. Inspect errors and scope limitations before interpreting results.'):
            raise ValueError('Incomplete/error-bearing report')
        result['verified_input']={'report_identity':identity,'encoding':encoding,
            'manifest_sha256':hashlib.sha256(manifest_data).hexdigest(),
            'project_id':r['project_id'],'project_identity_basis':'explicit ledger metadata; report format does not independently authenticate project'}
    except (ValueError,KeyError,TypeError,OSError) as exc:
        return dict(result,case_status='input_integrity_failure',reason=str(exc))
    try:
        if discover_fn is None:
            from resolve import discover_shadow
            discover_fn=discover_shadow
        machine=discover_fn(report,manifest=manifest,project_id=r['project_id'],
                            encoding=encoding,xy_tolerance=.001,nearby_distance=1000)
        # A post-call byte check detects changes during the execution window.
        if report.read_bytes()!=data or manifest.read_bytes()!=manifest_data:
            return dict(result,case_status='input_integrity_failure',reason='input changed during prediction')
        return dict(result,case_status='executed',fresh_machine_result=machine)
    except Exception as exc:
        return dict(result,case_status='execution_error',reason=type(exc).__name__+': '+str(exc))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--request',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args()
    request=json.loads(Path(args.request).read_text(encoding='utf-8'))
    freeze(args.output,predict(request))
