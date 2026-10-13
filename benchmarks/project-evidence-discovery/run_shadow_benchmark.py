"""Two-phase regression replay; no expected labels enter the Prediction process."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys
from prediction import freeze, sha256, validate_request
import scoring


def prediction_request(case, inputs):
    # Explicit field projection, never pass the ledger case or previous results.
    return {**{k:copy.deepcopy(case[k]) for k in ('case_id','project_id','drawing',
        'target_identity','report_sha256','acquisition_scope')},
        'report_path':inputs['report_path'],'manifest_path':inputs['manifest_path']}


def validate_inputs(ledger, input_map):
    if ledger.get('version')!='0.2' or not isinstance(ledger.get('cases'),list) or not ledger['cases']:
        raise ValueError('Ledger v0.2 cases required')
    ids=[c['case_id'] for c in ledger['cases']]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate ledger case_id')
    entries=input_map.get('cases')
    if not isinstance(entries,list):raise ValueError('input-map cases list required')
    mapped=[e['case_id'] for e in entries]
    if len(mapped)!=len(set(mapped)) or set(mapped)-set(ids):raise ValueError('Duplicate or unknown input-map case_id')
    for e in entries:
        if set(e)!={'case_id','report_path','manifest_path'}:raise ValueError('Unexpected input-map fields')
    for c in ledger['cases']:
        validate_request(prediction_request(c,{'report_path':'not-provided','manifest_path':'not-provided'}))
    return {e['case_id']:e for e in entries}


def run(ledger_path, input_map_path, output_dir):
    ledger_path,input_map_path,output_dir=map(Path,(ledger_path,input_map_path,output_dir))
    ledger_bytes=ledger_path.read_bytes();map_bytes=input_map_path.read_bytes()
    ledger=json.loads(ledger_bytes.decode('utf-8-sig'));inputs=validate_inputs(ledger,json.loads(map_bytes.decode('utf-8-sig')))
    output_dir.mkdir(parents=True,exist_ok=False)
    predictions=[]
    # Phase A: no calls to expectation()/score_file(), no adjudication fields passed.
    for case in ledger['cases']:
        cid=case['case_id'];pred=output_dir/(cid+'.prediction.json')
        if cid not in inputs:
            freeze(pred,{'case_id':cid,'target_identity':case['target_identity'],
                'case_status':'input_unavailable','input_report_sha256':None,'reason':'case missing from input-map'})
        else:
            paths={k:str((input_map_path.parent/inputs[cid][k]).resolve()) for k in ('report_path','manifest_path')}
            request=prediction_request(case,paths);rp=output_dir/(cid+'.request.json');freeze(rp,request)
            proc=subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('prediction.py')),
                '--request',str(rp),'--output',str(pred)],capture_output=True)
            if proc.returncode:
                # Never replace a partial/existing result with a fabricated success.
                if pred.exists():raise RuntimeError('Worker failed after output creation: '+cid)
                freeze(pred,{'case_id':cid,'target_identity':case['target_identity'],
                    'case_status':'execution_error','input_report_sha256':None,
                    'reason':proc.stderr.decode('utf-8',errors='replace')})
        predictions.append({'case_id':cid,'path':str(pred),'sha256':sha256(pred)})
    freeze(output_dir/'prediction-index.json',{'phase':'prediction_complete','predictions':predictions})
    # Phase B reads expectations only after ALL machine result files are frozen.
    if ledger_path.read_bytes()!=ledger_bytes:raise ValueError('Ledger changed during prediction')
    ledger_for_scoring=json.loads(ledger_path.read_text(encoding='utf-8-sig'))
    for case in ledger_for_scoring['cases']:scoring.expectation(case)
    scored=[scoring.score_file(p['path'],p['sha256'],c) for p,c in zip(predictions,ledger_for_scoring['cases'])]
    summary={'total_cases':len(scored),'executed_cases':sum(c['case_status']=='executed' for c in scored),
        'passed':sum(c['pass_fail']=='PASS' for c in scored),'failed':sum(c['pass_fail']=='FAIL' for c in scored)}
    counters={'skipped_input_unavailable':'input_unavailable','input_integrity_failures':'input_integrity_failure',
        'false_positives':'false_positive','false_negatives':'false_negative',
        'semantic_overreach_failures':'semantic_overreach','conflict_mismatches':'conflict_mismatch','execution_errors':'execution_error'}
    summary.update({key:sum(label in c['failure_class'] for c in scored) for key,label in counters.items()})
    result={'object_type':'BatchShadowBenchmarkSummary','version':'0.1','mode':'regression_replay',
        'ledger_sha256':sha256(ledger_path),'summary':summary,'cases':scored,
        'scope_limitation':'Discovery semantic boundary only; full CandidateSemantic / ProjectRule / Gate pipeline not validated by this batch.'}
    for p in predictions:
        if sha256(p['path'])!=p['sha256']:raise ValueError('Scoring changed prediction')
    if input_map_path.read_bytes()!=map_bytes:raise ValueError('Input map changed')
    freeze(output_dir/'summary.json',result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--ledger',required=True);p.add_argument('--input-map',required=True);p.add_argument('--output-dir',required=True)
    args=p.parse_args()
    try:result=run(args.ledger,args.input_map,args.output_dir)
    except (ValueError,KeyError,TypeError,OSError,RuntimeError) as exc:
        print(type(exc).__name__+': '+str(exc),file=sys.stderr);sys.exit(2)
    print(json.dumps(result['summary']))
    sys.exit(1 if result['summary']['failed'] else 3 if result['summary']['skipped_input_unavailable'] else 0)
