"""Adapt frozen project evidence; do not calculate or rewrite the formal net value."""
import copy
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PATHS={'gate':'outputs/project-evidence-gate-v01/fixture-results.json',
       'route':'outputs/golden-3d-route-20261004/evidence.json',
       'rules':'outputs/golden-project-measurement-rules-20261004/project-rules.json',
       'formal':'outputs/golden-project-measurement-rules-20261004/design-net-quantities.json',
       'units':'outputs/drawing-unit-audit/results.json',
       'geometry':'outputs/golden-special-elevation-boundary-20261004/evidence.json'}

def main():
    docs={k:json.loads((ROOT/p).read_text(encoding='utf-8-sig')) for k,p in PATHS.items()}
    gate=docs['gate'][0];route=docs['route'];units=docs['units'];rules=docs['rules']['rules']
    binding=dict(gate['provenance']['context'],edge_handle='13CF5')
    def prov(s,pointer=''):return [{'source_id':s,'pointer':pointer}]
    def record(s,pointer='',**kw):return dict(status='supported',binding=copy.deepcopy(binding),provenance=prov(s,pointer),**kw)
    raw=docs['geometry']['RouteElevationSegmentation']['segments'][0]['lengthDrawingUnits']
    assumptions=[]
    for a in route['assumptions']:
        assumptions.append({'id':a['id'],'value':copy.deepcopy(a),'status':'approved','isDrawingFact':False,
           'scope':{'binding':copy.deepcopy(binding),'conditions':copy.deepcopy(rules[0]['conditions'])},
           'provenance':prov('route','/assumptions')+prov('rules','/rules/0')})
    aids=[a['id'] for a in assumptions]
    objects=[]
    for i,kind in enumerate(('conduit','wire')):
        formal=docs['formal']['quantities'][i]
        transitions=[]
        for j,t in enumerate(route['endpointTransitions']):
            ownership=formal['transitionOwnership'][j]
            assert ownership['routeEdgeRef']=='13CF5' and ownership['deviceRef']==t['deviceRef']
            transitions.append(record('route','/endpointTransitions/'+str(j),adjustment_id=ownership['key']+':box_entry',
                owner=copy.deepcopy(binding),device=t['deviceRef'],transition_type='box_entry',length=t['lengthMeters'],unit='m',
                assumption_refs=[t['calculationAssumptionRef']],assumptions_required=True,purpose='design_net'))
        x={'object_id':'eligibility:13CF5:'+kind,'quantity_type_candidate':kind,'semantic_gate':copy.deepcopy(gate),
           'measurement_scope':record('formal','/quantities/'+str(i)+'/scope',kind='edge'),
           'geometry':record('geometry','/RouteElevationSegmentation/segments/0/lengthDrawingUnits',
                 base_length=raw,source_entity='13CF5',source_unit=units['candidateUnit'],engineering_unit='m',
                 conversion=record('units','',from_unit=units['candidateUnit'],to_unit='m',factor=units['metersPerDrawingUnit'],converted_length='7.471249602')),
           'specification':dict(value=formal['spec'],installation=formal['installation'],binding_status='supported',
                 binding=copy.deepcopy(binding),evidence_type='reviewed_project_rule',provenance=prov('formal','/quantities/'+str(i))),
           'multiplier':record('formal','/quantities/'+str(i)+'/countMultiplier',value=formal['countMultiplier'],
                 interpretation=rules[1]['measurementBasis'] if kind=='wire' else 'one conduit route path; no procurement/price factors'),
           'base_path':record('route','/slabFollowingLengthMeters',value=route['slabFollowingLengthMeters'],unit='m',mode='approved_3d',assumption_refs=aids,assumptions_required=True),
           'height':record('route','/slabFollowingSegments',conditions=copy.deepcopy(rules[0]['conditions']),assumption_refs=aids,assumptions_required=True),
           'adjustments':{'transition':record('formal','/quantities/'+str(i)+'/transitionOwnership',inventory_complete=True,items=transitions,
                 expected_connections=[{'device':t['device'],'transition_type':t['transition_type']} for t in transitions]),
                 'vertical':dict(status='not_applicable',binding=copy.deepcopy(binding),items=[],reason='Slope already included in approved base_path; endpoint drops are transition items',provenance=prov('route','/slabFollowingSegments')),
                 'other':dict(status='not_applicable',binding=copy.deepcopy(binding),items=[],reason='No additional design adjustment approved; no loss/reserve/symbol offset',provenance=prov('formal','/quantities/'+str(i)))},
           'deduplication':record('rules','/rules/2',rule=copy.deepcopy(rules[2]),key_fields=['edge_handle','segment_id','device','transition_type']),
           'assumptions':copy.deepcopy(assumptions),'procurement':{'ConduitMaterialRequirement':formal.get('ConduitMaterialRequirement')},
           'measurement_claims':[{'key':'multiplier','value':formal['countMultiplier'],'unit':'factor','status':'supported','provenance':prov('formal','/quantities/'+str(i)+'/countMultiplier')}]+[
                 {'key':'transition:13CF5:'+t['device']+':box_entry','value':t['length'],'unit':'m','status':'supported','provenance':prov('formal','/quantities/'+str(i)+'/transitionOwnership')} for t in transitions]}
        x['geometry']['conversion']['status']=units['drawingUnitStatus']
        objects.append(x)
    out=ROOT/'quantity-eligibility/fixtures';out.mkdir(exist_ok=True)
    bundle={'sources':[{'source_id':k,'path':'../../'+p,'sha256':hashlib.sha256((ROOT/p).read_bytes()).hexdigest()} for k,p in PATHS.items()],
            'objects':objects,'adapter_note':'Frozen project evidence projection only; no final length evaluation'}
    (out/'golden.json').write_text(json.dumps(bundle,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
