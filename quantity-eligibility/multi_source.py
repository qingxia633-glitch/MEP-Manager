"""Bounded RoutePath measurement. Independent execution review for plan 0.4."""
from copy import deepcopy
from decimal import Context, Decimal, DecimalException, Inexact, Rounded, localcontext
from fractions import Fraction
from itertools import combinations
import hashlib
import json
import os
from pathlib import Path
import re
import stat

from quantity_contract import approved_role
from unit_contract import FACTORS

# Installation-owned, outside project evidence. Never resolved from a request or cwd.
AUTHORITY_DIR = (Path(r'C:\Program Files\MEP-Manager\quantity-grants') if os.name == 'nt'
                 else Path('/etc/mep-manager/quantity-grants'))
SCOPE_KEYS = ('project_id', 'drawing_instance_id', 'dwg_sha256', 'report_sha256', 'space')
BASES = {'conduit':'conduit', 'grouped_wire':'wire', 'conductor':'wire'}


def digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(raw.encode('utf8')).hexdigest()


def need(value, reason):
    if not value:
        raise ValueError(reason)


def pin(value):
    need(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value), 'invalid_source_digest')


def number(value):
    need(type(value) in (str, int), 'exact_decimal_required')
    d = Decimal(value)
    need(d.is_finite(), 'nonfinite_number')
    return d


def point(value):
    need(isinstance(value, list) and len(value) == 3, 'invalid_wcs')
    return tuple(number(v) for v in value)


def distance(points):
    need(len(points) == 2, 'straight_segment_required')
    a, b = map(point, points)
    squared = sum((x-y)**2 for x, y in zip(a,b))
    with localcontext(Context(prec=48)):
        return squared.sqrt()


def approval_covers(plan, approved_scope):
    scope = plan['scope']
    need(all(approved_scope.get(k)==v for k,v in scope.items()), 'independent_approval_scope_mismatch')
    edges = plan['route']['native_steps']
    gaps = plan['route']['approved_recovered_components']
    extra = set(approved_scope) - set(scope)
    if extra == {'native_identities','component_ids'}:
        requested = {digest(e['identity']) for e in edges}
        allowed = {digest(i) for i in approved_scope['native_identities']}
        need(requested==allowed and {g['id'] for g in gaps}==set(approved_scope['component_ids']),
             'approval_path_extent_mismatch')
        return
    # Existing bounded-section confirmations describe the two outside endpoints,
    # whereas RoutePath records the two inside endpoints of the drawing break.
    need(extra=={'parent_path','bounded_start','bounded_end','component_id'} and len(edges)==2
         and all(g['id']==approved_scope['component_id'] for g in gaps), 'unqualified_approval_extent')
    outer = set()
    for handle, path, side in gaps[0]['endpoints']:
        need(path==approved_scope['parent_path'],'foreign_approval_parent_path')
        outer.add(handle + ('/end' if side=='start' else '/start'))
    need(outer=={approved_scope['bounded_start'],approved_scope['bounded_end']},
         'approval_endpoint_extent_mismatch')


def authority_bytes(path):
    """The deployment protects the directory entries against untrusted replacement."""
    for directory in reversed(path.parents):
        info = directory.lstat()
        need(stat.S_ISDIR(info.st_mode) and not redirected(info), 'redirected_authority_directory')
    info = path.lstat()
    need(stat.S_ISREG(info.st_mode) and not redirected(info) and info.st_nlink == 1,
         'untrusted_authority_file')
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        need(os.path.samestat(info, opened) and opened.st_nlink == 1, 'authority_file_changed')
        return stream.read()


def redirected(info):
    return (stat.S_ISLNK(info.st_mode) or
            bool(getattr(info,'st_file_attributes',0) & stat.FILE_ATTRIBUTE_REPARSE_POINT))


def grant(plan):
    fingerprint = digest(plan)
    try:
        record = json.loads(authority_bytes(AUTHORITY_DIR / (fingerprint + '.json')))
    except FileNotFoundError:
        return None
    need(record['plan_sha256'] == fingerprint and record['scope'] == plan['scope']
         and record['role'] == plan['role'] and record['approval'] == plan['approval']
         and record['status'] == 'approved_for_design_net' and approved_role(record['source']),
         'independent_grant_mismatch')
    expected = record['approval']['sha256']
    raw = authority_bytes(AUTHORITY_DIR / 'approvals' / (expected + '.json'))
    need(hashlib.sha256(raw).hexdigest()==expected, 'independent_approval_bytes_mismatch')
    approved = json.loads(raw)
    need(approved['approval_id']==record['approval']['id'], 'independent_approval_id_mismatch')
    approval_covers(plan, approved['scope'])
    item_id = plan['material'].get('item_id')
    need(record.get('material_item_id') == item_id, 'independent_material_item_mismatch')
    policy = record['reporting_policy']
    need(type(policy['decimal_places']) is int and 0 <= policy['decimal_places'] <= 1000
         and policy['rounding_mode']=='half_even' and approved_role(policy['source']),
         'invalid_reporting_policy')
    from executable_contract import validate_gate
    from evidence_contracts import authorization
    # Each approved edge retains its own established semantic Gate. A route-level
    # authorization cannot manufacture a single fictitious native edge identity.
    gates = record['parent_gates']
    expected = {digest(e['identity']) for e in plan['route']['native_steps']}
    need(isinstance(gates,dict) and set(gates)==expected, 'incomplete_parent_gates')
    for edge in plan['route']['native_steps']:
        ident = edge['identity']
        binding = dict(project_id=ident['project_id'],drawing_ref=plan['scope']['drawing'],
                       parent_path=ident['parent_path'],edge_handle=ident['handle'],
                       segment_id=None,scope_type='edge')
        parent = dict(binding=binding,approved_semantic_role=plan['role'],
                      semantic_gate=gates[digest(ident)])
        validate_gate(parent)
        authorization(parent)
    return record


class Calculation:
    def __init__(self):
        self.nodes = []
        self.values = {}

    def node(self, name, op, inputs, value, unit, source, status):
        need(name not in self.values, 'duplicate_calculation_node')
        self.values[name] = value
        self.nodes.append(dict(id=name, op=op, inputs=inputs, value=None if value is None else str(value),
                               unit=unit, source=source, approval_status=status))
        return name

    def operation(self, name, op, inputs, unit):
        values = [self.values[k] for k in inputs]
        value = None
        if None not in values:
            value = sum(values, Decimal(0)) if op == 'sum' else values[0]*values[1]
        return self.node(name, op, inputs, value, unit, 'derived_from_inputs',
                         'pending' if value is None else 'derived')

    def metres(self, name, coords, source):
        measured = distance(coords)
        raw = self.node(name+'.mm', 'distance_mm', [], measured, 'mm',
                        dict(source, wcs_mm=coords), 'source_measurement')
        return self.operation(name, 'multiply', [raw,'mm_to_m'], 'm')


def overlaps(first, second):
    """Positive collinear WCS extent. Shared end points and crossings are allowed."""
    a,b = [tuple(map(Fraction,p)) for p in first]
    c,d = [tuple(map(Fraction,p)) for p in second]
    axis = next((i for i in range(3) if a[i] != b[i]), None)
    if axis is None:
        return False
    lo,hi = sorted((a[axis],b[axis]))
    left,right = sorted((c[axis],d[axis]))
    if max(lo,left) >= min(hi,right):
        return False
    return all((p[i]-a[i])*(b[axis]-a[axis]) == (b[i]-a[i])*(p[axis]-a[axis])
               for p in (c,d) for i in range(3))


def measure_route(plan, calc):
    scope, route = plan['scope'], plan['route']
    need(set(scope) == set(SCOPE_KEYS) | {'drawing'} and all(approved_role(v) for v in scope.values()),
         'incomplete_scope')
    for k in ('dwg_sha256','report_sha256'):
        pin(scope[k])
    need(type(route['RoutePathComponentVersion']) is int and route['RoutePathComponentVersion'] == 1
         and route['status'] == 'qualified'
         and route['unresolved_gaps'] == [] and digest(route) == plan['route_sha256'],
         'unqualified_projection')
    base = {k:scope[k] for k in SCOPE_KEYS}
    def identity(obj):
        need(set(obj) == set(base) | {'handle','parent_path'} and all(obj[k] == v for k,v in base.items())
             and approved_role(obj['handle']) and isinstance(obj['parent_path'],list)
             and all(approved_role(x) for x in obj['parent_path']), 'foreign_or_invalid_identity')
        return digest(obj)

    gaps = route['approved_recovered_components']
    need(isinstance(gaps,list) and gaps, 'approved_recovery_required')
    unit = gaps[0]['provenance']['unit']
    pin(unit['sha256'])
    factor = FACTORS['mm','m']
    need(approved_role(unit['id']) and number(unit['conversion_to_meter']) == factor,
         'unit_authorization_mismatch')
    calc.node('mm_to_m','source',[],factor,'m/mm',unit,'source_conversion')
    native, recovered, sources, segments = {}, {}, [], []
    for edge in route['native_steps']:
        need(set(edge)<= {'kind','identity','vertices_wcs_mm','native_length_mm','layer','linetype'},
             'unsupported_native_subsegment')
        ident = edge['identity']
        key = identity(ident)
        coords = edge['vertices_wcs_mm']
        need(key not in native and edge['kind']=='geometry' and distance(coords)>0
             and distance(coords)==number(edge['native_length_mm']), 'invalid_native_length_or_duplicate')
        need(point(coords[0])[2] == point(coords[1])[2], 'nonplanar_native')
        native[key] = coords
        segments.append(tuple(map(point,coords)))
        sources.append(calc.metres('native:'+key,coords,dict(identity=ident,report=scope['report_sha256'])))
    need(len(native)>=2,'multiple_parents_required')
    native_keys = sources.copy()
    for gap in gaps:
        ends, parents, coords = gap['endpoints'], gap['parents'], gap['wcs_mm']
        need(len(ends)==len(parents)==len(coords)==2 and gap['scope']==scope
             and gap['eligibility']=='project_path_component_only' and gap['kind']=='approved_recovered_gap'
             and gap['crossed_connection_allowed'] is False and identity(gap['crossed_witness']) not in native
             and gap['competing_continuation_status']=='excluded_in_reviewed_inventory','invalid_gap_scope')
        prov = gap['provenance']
        for k in ('assumption_sha256','review_sha256','manifest_sha256'):
            pin(prov[k])
        need(prov['unit']==unit and prov['report_sha256']==scope['report_sha256']
             and approved_role(prov['assumption_id']), 'wrong_gap_provenance')
        for end, ident, xyz in zip(ends,parents,coords):
            key = identity(ident)
            need(key in native and end[:2]==[ident['handle'],ident['parent_path']]
                 and len(end)==3 and end[2] in ('start','end')
                 and point(native[key][0 if end[2]=='start' else 1])==point(xyz),'wrong_gap_endpoint')
        pair_key = dict(project_id=scope['project_id'],drawing_instance_id=scope['drawing_instance_id'],
                        snapshot=scope['report_sha256'],space=scope['space'],endpoints=sorted(ends))
        key = 'gap:'+digest(pair_key)
        length = distance(coords)
        a,b = map(point,coords)
        need(a[2]==b[2] and length>0 and key==gap['id'] and length==number(gap['length_mm'])
             and sum((x-y)**2 for x,y in zip(a,b))==number(gap['squared_length_mm2'])
             and length*factor==number(gap['length_m']), 'gap_identity_or_length_mismatch')
        witness = (tuple(sorted((a,b))),digest(prov),identity(gap['crossed_witness']))
        if key in recovered:
            need(recovered[key]==witness,'conflicting_gap_observations')
            continue
        recovered[key] = witness
        segments.append((a,b))
        sources.append(calc.metres(key,coords,dict(component=key,provenance=prov,endpoints=ends)))
    # A reviewed bounded path must be one chain; reject branches, loops and detached pieces.
    need(not any(overlaps(a,b) for a,b in combinations(segments,2)), 'overlapping_path_components')
    adjacent = {}
    for a,b in segments:
        adjacent.setdefault(a,[]).append(b)
        adjacent.setdefault(b,[]).append(a)
    tips = [v for v,peers in adjacent.items() if len(peers)==1]
    need(len(tips)==2 and all(len(v)<=2 for v in adjacent.values()),'not_a_bounded_path')
    visited, todo = set(), [tips[0]]
    while todo:
        v = todo.pop()
        if v not in visited:
            visited.add(v)
            todo.extend(adjacent[v])
    need(len(visited)==len(adjacent),'disconnected_path')
    calc.operation('native_m','sum',sorted(native_keys),'m')
    calc.operation('recovered_m','sum',sorted(recovered),'m')
    calc.operation('planar_m','sum',['native_m','recovered_m'],'m')
    return sorted(sources)


def evaluate(plan):
    """Regenerate the audit for every caller, including direct build and replay."""
    try:
        with localcontext(Context(prec=160)) as context:
            context.traps[Inexact] = context.traps[Rounded] = True
            return _evaluate(plan)
    except (ValueError, KeyError, TypeError, IndexError, AttributeError, DecimalException, OSError) as exc:
        return dict(status='blocked',blocking_reasons=[str(exc)],quantity=None,audit=None)


def _evaluate(plan):
    need(set(plan)=={'schema_version','scope','route','route_sha256','approval','role','installation',
                     'material','events'} and plan['schema_version']=='0.4','unexpected_plan_fields')
    need(set(plan['approval'])=={'id','sha256'} and approved_role(plan['role'])
         and approved_role(plan['approval']['id']), 'missing_local_approval')
    pin(plan['approval']['sha256'])
    calc = Calculation()
    source_ids = measure_route(plan,calc)
    material = plan['material']
    need(set(material)-{'item_id'}=={'wire','conduit','group_count','conductor_count',
                         'conductor_cross_section_mm2','issue_basis'},'unexpected_material_fields')
    if 'item_id' in material:
        need(approved_role(material['item_id']), 'invalid_material_item_id')
    basis = material['issue_basis']
    need(basis in BASES and all(approved_role(material[k]) for k in ('wire','conduit'))
         and number(material['conductor_cross_section_mm2'])>0,'invalid_material')
    for name in ('group_count','conductor_count'):
        count = material[name]
        need(type(count) is int and count>0,'invalid_material_count')
        calc.node(name,'source',[],Decimal(count),'count',plan['approval'],'declared_in_review')
    reasons = []
    install = plan['installation']
    need(set(install)=={'source','method','status'} and approved_role(install['source'])
         and approved_role(install['method']),'missing_installation_source')
    if install['status']!='approved':
        reasons.append('installation_scope_pending')
    receipt = grant(plan)
    if receipt is None:
        reasons.append('independent_execution_grant_missing')
    targets = {name:['planar_m'] for name in ('physical','conduit','wire')}
    clearance = None
    if reasons:
        clearance = calc.node('execution_clearance','pending',[],None,'authorization',
                              dict(approval=plan['approval'],reasons=list(reasons)),'pending')
    kinds, seen, vertical_owners = set(), set(), set()
    allocated = set()
    pending_events = []
    for event in plan['events']:
        kind, name, owners = event['kind'], event['id'], event['targets']
        need(set(event)<={'id','kind','targets','source','status','allocation_basis','length_m','wcs_mm'}
             and isinstance(owners,list),'invalid_event_fields')
        need(kind in ('vertical','beam','reserve','other') and approved_role(name) and name not in seen
             and approved_role(event['source']) and owners and len(set(owners))==len(owners)
             and set(owners)<=targets.keys(),'invalid_event_or_ownership')
        kinds.add(kind)
        seen.add(name)
        ref = 'event:'+name
        origin = dict(event_id=name,kind=kind,targets=owners,source=event['source'])
        if event['status']=='pending':
            need(event.get('length_m') is None and event.get('wcs_mm') is None,'pending_value_conflict')
            calc.node(ref,'pending',[],None,'m',origin,'pending')
            pending_events.append(name)
            if BASES[basis] in owners:
                reasons.append('pending:'+name)
        elif event['status']=='approved':
            need(event['allocation_basis']=='per_route_before_counts','unsupported_event_allocation_basis')
            origin['allocation_basis']=event['allocation_basis']
            if kind=='vertical':
                coords=event['wcs_mm']
                need(len(coords)==2 and point(coords[0])[:2]==point(coords[1])[:2]
                     and 'length_m' not in event,'invalid_vertical_path')
                leg=tuple(sorted(map(point,coords)))
                for owner in owners:
                    need((leg,owner) not in vertical_owners,'duplicate_vertical_allocation')
                    need(not any(owner==prior_owner and overlaps(leg,prior_leg)
                                 for prior_leg,prior_owner in vertical_owners),'overlapping_vertical_allocation')
                    vertical_owners.add((leg,owner))
                calc.metres(ref,coords,origin)
            else:
                length=number(event['length_m'])
                need(length>=0 and 'wcs_mm' not in event,'invalid_net_increment')
                calc.node(ref,'source',[],length,'m',origin,
                          'reviewed_input' if receipt is not None else 'submitted_unverified')
            if receipt is not None and calc.values[ref] > 0:
                allocation = receipt['event_allocations'][name]
                component = allocation['physical_component_id']
                need(approved_role(component) and allocation['source']==event['source'] and
                     allocation['basis']==('vertical_path' if kind=='vertical' else 'net_additional_to_measured_path'),
                     'unreconciled_event_extent')
                for owner in owners:
                    need((component,owner) not in allocated and component not in source_ids,
                         'duplicate_event_extent')
                    allocated.add((component,owner))
        else:
            raise ValueError('unknown_event_status')
        for owner in owners:
            targets[owner].append(ref)
    need({'vertical','beam','reserve'}<=kinds,'missing_required_event_inventory')
    for owner,refs in targets.items():
        if clearance is None:
            calc.operation(owner,'sum',refs,'m')
        else:
            # Permission is a control dependency, never a length operand.
            calc.node(owner,'withheld',refs,None,'m',
                      dict(intended_operation='sum',requires=clearance),'blocked')
    for name,root in [('planar_grouped','planar_m'),('grouped_wire','wire')]:
        calc.operation(name,'multiply',[root,'group_count'],'group.m')
    for name,root in [('planar_conductor','planar_grouped'),('conductor','grouped_wire')]:
        calc.operation(name,'multiply',[root,'conductor_count'],'conductor.m')
    views={k:None if v is None else str(v) for k,v in calc.values.items()
           if k in ('native_m','recovered_m','planar_m','planar_grouped','planar_conductor',
                    'physical','conduit','grouped_wire','conductor')}
    audit = dict(nodes=calc.nodes,views=views,source_ids=source_ids,grant=receipt,
                 scope=plan['scope'],pending_events=pending_events,procurement_quantity=None)
    return dict(status='blocked' if reasons else 'eligible', blocking_reasons=reasons, audit=audit,quantity=None)


def export_plan(plan):
    result=evaluate(plan)
    need(result['status']=='eligible', ', '.join(result['blocking_reasons']))
    return deepcopy(plan)


def overlapping_items(plan, audit, previous):
    """Compare independently revalidated items within one material family."""
    other = previous['source_plan']
    left, right = plan['scope'], other['scope']
    if left['project_id'] != right['project_id'] or left['space'] != right['space']:
        return False
    if left['drawing_instance_id'] != right['drawing_instance_id'] and left['drawing'] != right['drawing']:
        return False
    if left != right:
        return True  # Related drawing with unreconciled identity or snapshot.
    first_item = plan['material'].get('item_id')
    second_item = other['material'].get('item_id')
    if first_item and second_item and first_item != second_item:
        return False  # Both IDs were bound by independent installation reviews.
    if set(audit['source_ids']).intersection(previous['source_ids']):
        return True
    owner = BASES[plan['material']['issue_basis']]
    def extents(item, receipt):
        route = item['route']
        lines = [edge['vertices_wcs_mm'] for edge in route['native_steps']]
        lines.extend(gap['wcs_mm'] for gap in route['approved_recovered_components'])
        components = set()
        for event in item['events']:
            if event['status'] != 'approved' or owner not in event['targets']:
                continue
            if event['kind']=='vertical':
                leg=event['wcs_mm']
                if point(leg[0])==point(leg[1]):
                    continue
                lines.append(leg)
            elif number(event['length_m'])==0:
                continue
            components.add(receipt['event_allocations'][event['id']]['physical_component_id'])
        return lines, components
    a, a_components = extents(plan, audit['grant'])
    b, b_components = extents(other, previous['grant'])
    return bool(a_components & b_components) or any(overlaps(x,y) for x in a for y in b)


def decision(plan):
    result=evaluate(plan)
    ready=result['status']=='eligible'
    return dict(model_type='QuantityEligibilityDecision',quantity_eligibility_status=result['status'],
                quantity_formula_ready=ready,design_net_quantity_generation_allowed=ready,
                quantity_formula_plan=deepcopy(plan) if ready else None,quantity_generated=False,
                blocking_reasons=result['blocking_reasons'],audit=result['audit'])
