"""Project evidence export and numeric precheck only; never issue quantities."""
import hashlib
import json
import re
import sys
from pathlib import Path
from decimal import Decimal, localcontext, Inexact, Rounded, ROUND_HALF_EVEN

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'quantity-eligibility'))
from plan_v02 import export_plan, seal

def write_new(path,obj):
    data=json.dumps(obj,ensure_ascii=False,indent=2).encode('utf-8')
    if path.exists():
        if json.loads(path.read_text(encoding='utf-8-sig'))!=obj:raise ValueError('Refusing to replace existing artifact: '+str(path))
    else:path.write_bytes(data)

def main():
    out=ROOT/'outputs/quantity-build-plan-v02';out.mkdir(exist_ok=True)
    source=ROOT/'outputs/quantity-eligibility-v01/golden-results.json'
    source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    decisions=json.loads(source.read_text(encoding='utf-8-sig'))
    report=ROOT/'local_test_data/fire-alarm-full-snapshot-20260923/MEP-full-entity-report.txt'
    text=report.read_text(encoding='utf-8-sig')
    raw=re.search(r'^DWG=(.+)$',text,re.M)[1].strip().strip('"')
    corrected=raw.replace('\\','/').split('/')[-1]
    assert '?' not in corrected
    old=decisions[0]['quantity_formula_plan']['binding']['drawing_ref']
    correction=seal({'model_type':'CorrectionEvidence','correction_id':'drawing-ref:golden-v02',
        'historical_value':old,'corrected_value':corrected,'status':'approved',
        'source_artifact':str(source.relative_to(ROOT)).replace('\\','/'),'source_artifact_sha256':source_hash,
        'target_object_ids':[d['object_id'] for d in decisions],'edge_handle':'13CF5',
        'field_selector':'drawing_ref equal to historical_value within copied Golden plan only',
        'basis':'Exact DWG basename read from original fire-alarm snapshot; current user authorizes additive correction',
        'provenance':[{'evidence_type':'DrawingFact','source':str(report.relative_to(ROOT)).replace('\\','/'),
                       'field':'DWG','raw_value':raw,'sha256':hashlib.sha256(report.read_bytes()).hexdigest()},
                      {'evidence_type':'HumanConfirmation','source':'current instruction: add CorrectionEvidence without rewriting historical JSON'}],
        'historical_objects_modified':False})
    policy=seal({'model_type':'project_numeric_reporting_policy','policy_id':'project-numeric-reporting-policy:golden-v02',
        'status':'approved','scope':{'project_id':decisions[0]['quantity_formula_plan']['binding']['project_id']},
        'decimal_places':9,'rounding_mode':'ROUND_HALF_EVEN','intermediate_rounding':'none',
        'evidence_type':'ProjectRule / HumanConfirmation','is_drawing_fact':False,'is_national_standard':False,
        'provenance':[{'source':'current user instruction approving software numeric reporting policy'}]})
    write_new(out/'correction-evidence.json',correction)
    write_new(out/'project-numeric-reporting-policy.json',policy)
    checks=[]
    for d in decisions:
        p=export_plan(d,source_hash,correction,policy)
        write_new(out/('golden-'+p['quantity_type']+'-v02.json'),p)
        with localcontext() as c:
            c.prec=p['arithmetic_policy']['precision'];c.traps[Inexact]=True;c.traps[Rounded]=True
            values=[Decimal(t['original_value'])*Decimal(t['conversion']['factor']) for t in p['unit_execution_contract']['components']]
            exact=sum(values,Decimal(0))*Decimal(str(p['multiplier']['value']))
            c.traps[Inexact]=False;c.traps[Rounded]=False
            reported=exact.quantize(Decimal('0.000000001'),rounding=ROUND_HALF_EVEN)
        assert str(exact)=='7.77128331912231535912969050917979628'
        assert str(reported)=='7.771283319'
        checks.append({'object_id':p['object_id'],'plan_hash':p['content_hash'],'exact_value':str(exact),
                       'reported_value':str(reported),'unit':'m','multiplier':p['multiplier']['value'],
                       'precheck_status':'passed','DesignNetQuantity_created':False})
    write_new(out/'numeric-precheck.json',{'model_type':'BuildPlanNumericPrecheck','results':checks,
        'note':'Test-only arithmetic, not Builder execution or formal quantity issuance'})
    print(json.dumps(checks,ensure_ascii=True))

if __name__=='__main__':main()
