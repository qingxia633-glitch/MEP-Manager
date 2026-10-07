"""DeviceRoleResolver v0.1: attribute/definition evidence only, no geometry import."""
import hashlib
import re
from pathlib import Path

LEGEND_SOURCE = 'EC-4#-P+TBD_t8_t3.dwg'
DISPLAY_CODES = {'I', 'I/O', 'M1', 'M2'}
ROLE_ALIASES = {
    'smoke_detector': {'感烟探测器','点型感烟探测器','感烟探测器（点型）'},
    'heat_detector': {'感温探测器','点型感温探测器','感温探测器（点型）'},
    'manual_call_point': {'手动报警按钮','手动火灾报警按钮','带电话插孔手动报警按钮','手动报警按钮（带电话插孔）'},
    'input_module': {'输入模块','单输入模块'},
    'input_output_module': {'单输入单输出模块','单输入输出模块','输入输出模块','输入/输出模块','输入出模块'},
    'module_box': {'模块箱'},
    'fire_damper': {'防火阀'},
    'smoke_exhaust_outlet': {'排烟口'},
}


def _field(text,key):
    m=re.search(r'^'+re.escape(key)+r'=(.*?)\r?$',text,re.M)
    return m[1].strip().strip('"') if m else None


def _basename(s):
    return (s or '').replace('\\','/').rstrip('/').split('/')[-1]


def canonicalize(raw):
    """Return a separate normalized role and properties; never rewrite raw_value."""
    value=raw.strip().replace('(', '（').replace(')', '）').replace('%%D','℃').replace('%%d','℃').replace('°C','℃')
    for role,aliases in ROLE_ALIASES.items():
        if value in aliases:return role,{}
    m=re.fullmatch(r'(70|280)℃动作的?(常开|常闭)防火阀',value)
    if m:
        return 'fire_damper',dict(action_temperature=int(m[1]),temperature_unit='℃',
                                 normal_state='normally_open' if m[2]=='常开' else 'normally_closed')
    return 'unknown',{}


def _attrs_from_snapshot(rec):
    out=[]
    for a in re.split(r'(?m)(?=^AttributeTag=)',rec)[1:]:
        h=re.search(r'\(5 \. "([^"]+)"\)',a)
        out.append(dict(tag=_field(a,'AttributeTag'),raw_value=_field(a,'AttributeText_RAW') or '',
                        handle=h[1] if h else None))
    return out


def _dxf_attr(rec,handle=None):
    return dict(tag=_field(rec,'DXF:2'),raw_value=_field(rec,'DXF:1') or '',
                handle=handle or _field(rec,'DXF:5'))


class RoleContext:
    """Read-only input context; explicit legend bindings are separate reviewed evidence.

    Priority 5 uses independent explicit ATTRIB donors from the same drawing and
    exact definition name. No effective-name alias or geometry-based inheritance.
    """
    def __init__(self,drawing,instances,definitions,legends=None,provenance=None,role_tags=('A',)):
        self.drawing=drawing
        self.instances=instances
        self.definitions=definitions
        self.legends=legends or []
        self.provenance=provenance or []
        self.role_tags=tuple(role_tags)

    @classmethod
    def from_reports(cls,snapshot,probes,legends=None,role_tags=('A',)):
        provenance=[]
        def read(path):
            b=Path(path).read_bytes()
            provenance.append(dict(path=str(path),sha256=hashlib.sha256(b).hexdigest()))
            return b.decode('utf-8-sig')
        raw=read(snapshot);drawing=_field(raw,'DWG')
        if not drawing:raise ValueError('Snapshot DWG provenance required')
        instances={};definitions={}
        for rec in re.split(r'(?m)(?=^EntityHandle=)',raw):
            if _field(rec,'DXF_Type')!='INSERT':continue
            h=_field(rec,'EntityHandle')
            instances[h]=dict(handle=h,block_name=_field(rec,'BlockName'),
                              effective_block_name=_field(rec,'EffectiveName_RAW'),attributes=_attrs_from_snapshot(rec))
        for path in probes:
            text=read(path)
            if _field(text,'DWG')!=drawing:raise ValueError('Probe belongs to different or unknown drawing')
            for block in text.split('Block_BEGIN=')[1:]:
                name=block.splitlines()[0].strip('"\r');defaults=[];children=[];count=0
                for rec in block.split('Entity_END'):
                    typ=_field(rec,'DXF_Type');h=_field(rec,'EntityHandle')
                    if typ:count+=1
                    if typ=='ATTDEF':defaults.append(_dxf_attr(rec,h))
                    if typ=='INSERT':
                        own=rec.split('Subentity_BEGIN')[0]
                        children.append(dict(handle=h,block_name=_field(own,'ReferencedBlockName'),
                            attributes=[_dxf_attr(a) for a in rec.split('Subentity_BEGIN')[1:] if _field(a,'DXF:0')=='ATTRIB']))
                expected=_field(block,'DirectEntityCount')
                complete=bool(expected and int(expected)==count and 'Block_END' in block and
                              not any(t in block for t in ('ENTITY_UNREADABLE','DETAIL_ERROR')))
                d=dict(defaults=defaults,children=children,source=str(path),complete=complete)
                if name in definitions:
                    prior=definitions[name]
                    if prior['defaults']!=defaults or prior['children']!=children:
                        prior['conflicting']=True
                        prior.setdefault('alternatives',[]).append(d)
                else:definitions[name]=d
        return cls(drawing,instances,definitions,legends,provenance,role_tags)


def resolve_device_role(device_handle,context):
    """Select evidence by priority, reporting lower defaults as overridden, not conflict."""
    inst=context.instances.get(device_handle)
    evidence=[];ignored=[];issues=[]
    result=dict(model_type='DeviceRoleEvidence',resolver_version='0.1',device_handle=device_handle,block_name=inst.get('block_name') if inst else None,
        effective_block_name=inst.get('effective_block_name') if inst else None,
        canonical_role='unknown',raw_role_text=None,display_code=None,role_status='unresolved',
        properties={},evidence=evidence,selected_evidence=[],conflicting_evidence=[],
        overridden_defaults=[],lower_priority_disagreements=[],ignored_evidence=ignored,
        provenance=context.provenance,assumptions=['No geometry, layer or connection evidence used',
            'ATTDEF roles are inherited defaults, not explicit instance facts',
            'Legend alone is partial symbol/type evidence; no code-only equivalence'],issues=issues)
    if inst is None:
        issues.append('instance_not_found');return result
    name=inst.get('block_name');definition=context.definitions.get(name,{})
    def add(attrs,priority,kind,path,source=None):
        for a in attrs:
            raw=a.get('raw_value','');role,properties=canonicalize(raw)
            e=dict(evidence_type=kind,source_handle=a.get('handle'),source_definition_path=list(path),
                   attribute_tag=a.get('tag'),raw_value=raw,priority=priority,canonical_role=role,
                   properties=properties,source=source or context.drawing)
            e['eligible']=bool(a.get('tag') in context.role_tags and raw.strip() and raw.strip() not in DISPLAY_CODES)
            evidence.append(e)
    add(inst.get('attributes',[]),1,'instance_attrib',[device_handle])
    for a in inst.get('attributes',[]):
        if a.get('tag')=='$TEXT$' and a.get('raw_value'):
            result['display_code']=a['raw_value'];break
        if a.get('raw_value','').strip() in DISPLAY_CODES:result['display_code']=a['raw_value']
    if definition.get('conflicting'):
        issues.append('definition_reports_conflict')
    for variant in [definition]+definition.get('alternatives',[]):
        for child in variant.get('children',[]):
            add(child.get('attributes',[]),2,'direct_child_instance_attrib',[device_handle,child['handle']],variant.get('source'))
            if result['display_code'] is None:
                for a in child.get('attributes',[]):
                    if a.get('tag')=='$TEXT$' and a.get('raw_value'):result['display_code']=a['raw_value'];break
        add(variant.get('defaults',[]),3,'block_definition_default',[device_handle,name],variant.get('source'))
    for legend in context.legends:
        allowed=(_basename(legend.get('source_drawing'))==LEGEND_SOURCE and
                 legend.get('target_drawing')==context.drawing and legend.get('target_block_name')==name and
                 legend.get('binding_verified') is True and bool(legend.get('binding_evidence_refs')))
        if not allowed:
            ignored.append(dict(evidence=legend,reason='legend_source_or_explicit_definition_binding_not_admitted'));continue
        add([dict(tag='A',raw_value=legend.get('raw_value',''),handle=legend.get('source_handle'))],4,
            'project_legend',[device_handle,name],legend.get('source_drawing'))
        evidence[-1]['binding_evidence_refs']=list(legend['binding_evidence_refs'])
    donors=[]
    for h,other in context.instances.items():
        if not name or h==device_handle or other.get('block_name')!=name:continue
        attrs=[a for a in other.get('attributes',[]) if a.get('tag') in context.role_tags
               and a.get('raw_value','').strip() and a['raw_value'].strip() not in DISPLAY_CODES]
        if attrs:donors.append(h);add(attrs,5,'same_definition_instance_inheritance',[h],context.drawing)
    eligible=[e for e in evidence if e['eligible']]
    if not eligible:return result
    priority=min(e['priority'] for e in eligible)
    selected=[e for e in eligible if e['priority']==priority];result['selected_evidence']=selected
    result['raw_role_text']=selected[0]['raw_value']
    # Conflicts require contradicting known roles or property values at equal priority.
    roles={e['canonical_role'] for e in selected if e['canonical_role']!='unknown'}
    prop_values={k:{e['properties'][k] for e in selected if k in e['properties']} for k in set().union(*(e['properties'] for e in selected))}
    if len(roles)>1 or any(len(v)>1 for v in prop_values.values()):
        result['role_status']='conflicting';result['conflicting_evidence']=selected;return result
    if any(e['canonical_role']=='unknown' for e in selected):
        issues.append('higher_priority_role_text_not_in_v01_dictionary');return result
    result['canonical_role']=selected[0]['canonical_role']
    result['properties']={k:next(iter(v)) for k,v in prop_values.items()}
    result['role_status']=('supported' if priority in (1,2) else 'inherited' if priority in (3,5) else 'partial')
    if priority==5 and len(set(donors))<2:
        result['role_status']='partial';issues.append('fewer_than_two_independent_explicit_donors')
    if priority in (2,3) and definition.get('complete') is False:
        result['role_status']='partial';issues.append('incomplete_definition_attribute_inventory')
    for e in eligible:
        if e['priority']>priority:
            if e['evidence_type']=='block_definition_default':result['overridden_defaults'].append(e)
            if e['canonical_role']!=result['canonical_role'] or any(result['properties'].get(k)!=v for k,v in e['properties'].items()):
                result['lower_priority_disagreements'].append(e)
    return result
