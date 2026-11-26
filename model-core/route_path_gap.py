"""Project-reviewed gap projection for Read-RoutePath. No graph or quantity writes."""
import argparse
import hashlib
import json
import math
import re
import sys
from decimal import Context, Decimal, Inexact, Rounded, localcontext
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'project-evidence-discovery'))
from report_manifest import verify_manifest


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pinned(path, expected):
    data = path.read_bytes()
    require(hashlib.sha256(data).hexdigest() == expected, 'source_hash_mismatch: ' + path.name)
    return data


def field(record, key):
    matches = re.findall(r'^' + re.escape(key) + r'=(.*)$', record, re.M)
    require(len(matches) == 1, 'missing_or_duplicate_field: ' + key)
    return matches[0].strip('"')


def number(raw):
    value = Decimal(str(raw))
    require(value.is_finite(), 'invalid_number')
    return value


def point(raw):
    xyz = tuple(number(v) for v in raw.split())
    require(len(xyz) == 3, 'invalid_WCS')
    return xyz


def vector(a, b):
    return tuple(y-x for x, y in zip(a, b))


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def norm(v):
    return dot(v, v).sqrt()


def cross(a, b):
    return a[0]*b[1] - a[1]*b[0]


def aligned(direction, gap, outgoing, tolerance, angle_limit):
    if not norm(direction) or not norm(outgoing):
        return False
    return (dot(direction, gap) > 0 and dot(outgoing, gap) > 0
            and abs(direction[2]) <= tolerance and abs(outgoing[2]) <= tolerance
            and abs(gap[2]) <= tolerance
            and abs(cross(direction, gap)) <= tolerance * norm(direction)
            and abs(cross(outgoing, gap)) <= tolerance * norm(outgoing)
            and math.degrees(math.atan2(abs(cross(direction, outgoing)),
                                        dot(direction, outgoing))) <= angle_limit)


def inventory(data):
    raw = data.decode('utf-8-sig').replace('\r\n', '\n')
    chunks = re.split(r'(?m)(?=^EntityHandle=)', raw)[1:]
    require(field(raw, 'AllLayers').startswith('included') and
            field(raw, 'NestedBlocks') == 'not expanded', 'inventory_scope_mismatch')
    require(raw.rstrip().splitlines()[-1].startswith('END_OF_REPORT:')
            and field(raw, 'ReadErrorCount') == '0'
            and int(field(raw, 'SelectedEntityTotal')) == len(chunks), 'incomplete_report')
    seen, edges, rings = set(), {}, []
    for record in chunks:
        h, kind = field(record, 'EntityHandle'), field(record, 'DXF_Type')
        require(h and h not in seen, 'duplicate_entity')
        seen.add(h)
        if kind in ('INSERT', 'TEXT', 'MTEXT', 'POINT', 'ATTDEF'):
            continue  # Device interiors and nested spaces are outside the reviewed inventory.
        if kind in ('ARC', 'CIRCLE'):
            center = point(re.search(r'^Raw_DXF=\(10 ([^)]+)\)$', record, re.M)[1])
            radius = number(re.search(r'^Raw_DXF=\(40 \. ([^)]+)\)$', record, re.M)[1])
            require(point(field(record, 'Normal_DXF210').strip('()')) == (0, 0, 1)
                    and radius > 0, 'unsupported_curve')
            rings.append((center, radius))
            continue
        require(kind in ('LINE', 'LWPOLYLINE'), 'unreviewed_geometry: ' + kind)
        if kind == 'LINE':
            vertices = [point(field(record, k).strip('()')) for k in ('Start_WCS', 'End_WCS')]
            closed, bulges = False, [Decimal(0)]
        else:
            vertices = [point(v) for v in re.findall(r'^Vertex_WCS=\(([^)]+)\)$', record, re.M)]
            bulges = [number(v) for v in re.findall(r'^Width_or_bulge_DXF=\(42 \. ([^)]+)\)$', record, re.M)]
            flag = field(record, 'Closed')
            require(flag in ('nil', 'T') and len(vertices) >= 2 and len(bulges) == len(vertices),
                    'incomplete_polyline')
            closed = flag == 'T'
        edges[h] = dict(kind=kind, vertices=vertices, closed=closed, bulges=bulges,
                        layer=field(record, 'Layer'), linetype=field(record,'Style.entity_linetype.Value'))
    return edges, rings


def verify_pair(edges, rings, endpoints, crossed, search_distance):
    # Recheck only this reviewed pair against the complete pinned inventory.
    # Same finite intersection and alignment tests as VisualContinuity, no link discovery.
    tol = Decimal('.001')
    parents = []
    for handle, path, side in endpoints:
        e = edges[handle]
        require(path == [] and side in ('start', 'end') and not e['closed']
                and len(e['vertices']) == 2 and not any(e['bulges']), 'unsupported_parent')
        p, q = e['vertices']
        parents.append((p, q) if side == 'start' else (q, p))
    (a, a_inner), (b, b_inner) = parents
    gap = vector(a, b)
    length = norm(gap)
    require(length > tol and search_distance >= length, 'unreviewed_gap_extent')
    require(edges[endpoints[0][0]]['layer'] == edges[endpoints[1][0]]['layer']
            and aligned(vector(a_inner, a), gap, vector(b, b_inner), tol, .01), 'alignment')
    mid = tuple((x+y)/2 for x, y in zip(a, b))
    for center, radius in rings:
        require(abs(norm(vector(mid[:2], center[:2]))-radius) > length/2+search_distance+tol,
                'unresolved_nearby_curve')
    hits = []
    alternatives = []
    parent_handles = {e[0] for e in endpoints}
    require(len(parent_handles) == 2 and crossed not in parent_handles, 'invalid_pair')
    for h, edge in edges.items():
        if h in parent_handles:
            continue
        vertices = edge['vertices']
        if not edge['closed']:
            for endpoint, (p, inner) in zip(endpoints, parents):
                for side,pos,nxt in (('start',vertices[0],vertices[1]), ('end',vertices[-1],vertices[-2])):
                    step = vector(p, pos)
                    if norm(step) <= search_distance:
                        require(pos != nxt, 'unresolved_competitor_direction: ' + h)
                        require(norm(step) > tol and not aligned(vector(inner, p), step,
                                vector(pos, nxt), tol, .01), 'competing_endpoint: ' + h)
                        alternatives.append(dict(source_endpoint=endpoint, alternative_handle=h,
                                                 alternative_endpoint=side, distance_mm=str(norm(step)),
                                                 reason='direction_or_alignment_incompatible'))
        targets = vertices[1:] + (vertices[:1] if edge['closed'] else [])
        for index, (x, y) in enumerate(zip(vertices, targets)):
            chord = vector(x, y)
            bulge = edge['bulges'][index]
            margin = abs(bulge)*norm(chord)/2 + tol
            if bulge:
                # A chord is not an arc tangent. Do not use it to exclude a local alternative.
                require(any(max(x[k], y[k])+margin+search_distance < min(a[k], b[k]) or
                            min(x[k], y[k])-margin-search_distance > max(a[k], b[k])
                            for k in range(3)), 'unresolved_local_bulge')
            if any(max(x[k], y[k])+margin < min(a[k], b[k]) or
                   min(x[k], y[k])-margin > max(a[k], b[k]) for k in range(3)):
                continue
            require(not bulge, 'unresolved_local_bulge')
            ax, ay = vector(a, x), vector(a, y)
            if max(abs(cross(ax, gap)), abs(cross(ay, gap))) <= tol*length:
                lo, hi = sorted((dot(ax, gap), dot(ay, gap)))
                require(min(length*length, hi)-max(0, lo) <= tol*length, 'native_path_overlap')
            det = cross(gap, chord)
            if det:
                t, s = cross(ax, chord)/det, cross(ax, gap)/det
                if 0 <= t <= 1 and 0 <= s <= 1 and abs(a[2]+t*gap[2]-x[2]-s*chord[2]) <= tol:
                    require(h == crossed and 0 < t < 1 and 0 < s < 1
                            and abs(t-Decimal('.5'))*length <= tol
                            and abs(det) >= Decimal('.1')*length*norm(chord), 'unqualified_crossing: '+h)
                    hits.append(h)
    require(hits == [crossed], 'missing_or_ambiguous_crossing')
    return a, b, length, alternatives


def _verified_projection(request, review, review_hash, root):
    require(set(request) == {'files', 'scope', 'traversals'}, 'unexpected_request_fields')
    files = request['files']
    def read(name, digest):
        return pinned(root / files[name], digest)
    rule = json.loads(read('assumption', review['assumption_sha256']))
    unit_ref = review['unit_authorization']
    unit = json.loads(read('unit', unit_ref['sha256']))
    scope = request['scope']
    require(scope == rule['scope']['verified_application'] and scope['space'] == 'ModelSpace'
            and all(isinstance(scope[k], str) and scope[k].strip() for k in
                    ('project_id', 'drawing_instance_id', 'drawing'))
            and scope['project_id'] == rule['scope']['project_id'], 'approval_scope_mismatch')
    require(rule['status'] == 'approved_assumption' and rule['id'] == review['assumption']
            and rule['source']['kind'] == 'explicit_user_confirmation'
            and review['review']['local_gap_path_basis'] == 'eligible_under_project_assumption'
            and 'human_native_observation' in review['review']['review_evidence']
            and review['review']['crossed_engineering_connection'] is False, 'missing_pair_approval')
    src = review['source']
    require((src['snapshot'], src['dwg_sha256'], src['drawing']) ==
            (scope['report_sha256'], scope['dwg_sha256'], scope['drawing']), 'drawing_mismatch')
    applicability = unit['applicability']
    require(unit['assumption_id'] == unit_ref['id'] and unit['status'] == 'approved'
            and unit['authorization_type'] == 'approved_assumption'
            and all(applicability[k] == scope[k] for k in ('project_id','drawing','dwg_sha256','report_sha256'))
            and applicability['scope'] == 'current verified version ModelSpace'
            and applicability['universal_engineering_rule'] is False
            and applicability['other_drawings_allowed'] is False
            and (unit['cad_coordinate_unit'], unit['physical_length_unit']) == ('mm','m')
            and number(unit['conversion_to_meter']) == number(unit_ref['conversion_to_meter']) == Decimal('.001'),
            'unit_authorization_mismatch')
    read('dwg', scope['dwg_sha256'])
    data = read('report', scope['report_sha256'])
    manifest = json.loads(read('manifest', src['manifest_sha256']))
    meta = verify_manifest(data, root / files['report'], 'utf-8-sig', manifest)['report_identity']
    require(Path(meta['drawing'].replace('\\','/')).name == scope['drawing']
            and meta['acquisition_mode'] == 'ModelSpaceTopLevelAllLayers'
            and meta['model_space_top_level'] == 'included'
            and meta['extractor_version'] == '2.8-field-graph-evidence-v1', 'report_scope_mismatch')
    edges, rings = inventory(data)
    identity = {k:v for k,v in scope.items() if k != 'drawing'}
    parents = review['raw_parents']
    def check_native(row):
        h = row['identity']['handle']
        require(row['identity'] == dict(identity,handle=h,parent_path=[]), 'native_identity_mismatch')
        e = edges[h]
        require(e['kind'] == row['entity_type'] and e['layer'] == row['layer']
                and e['linetype'] == row['explicit_linetype']
                and e['vertices'] == [tuple(map(number,p)) for p in row['vertices_wcs_mm']],
                'native_geometry_mismatch')
        return h
    ordered_handles = [check_native(row) for row in parents]
    crossed = check_native(review['crossed'])
    derived = review['derived_gap']
    key = derived['dedup_key']
    endpoints = sorted(key['endpoints'])
    require(len(endpoints) == 2 and sorted(ordered_handles) == sorted(e[0] for e in endpoints)
            and key == dict(project_id=scope['project_id'], drawing_instance_id=scope['drawing_instance_id'],
                            snapshot=scope['report_sha256'], space=scope['space'], endpoints=endpoints),
            'pair_scope_mismatch')
    stable = 'gap:'+hashlib.sha256(json.dumps(key,sort_keys=True,separators=(',',':'),
                                               ensure_ascii=False).encode()).hexdigest()
    require(derived['id'] == stable, 'component_identity_mismatch')
    search = review['competition']
    for name in ('existing_overlapping_native_segments', 'bulged_segments_with_nearby_bounds',
                 'arc_or_circle_circumferences_in_expanded_window'):
        require(search[name] == [], 'unresolved_review_coverage')
    for first, second in (endpoints, endpoints[::-1]):
        endpoint_ref = first[0] + ':' + first[2]
        require(search['device_control_endpoint_status'][first[0]][first[2]] == 'unresolved',
                'device_contact_at_gap_or_unreviewed')
        require(search['qualified_oriented_pairs'][endpoint_ref] == [[second[0], second[2]]]
                and search['existing_endpoint_peers'][endpoint_ref] == [], 'unresolved_pair_review')
    require(number(search['contact_tolerance_mm']) == Decimal('.001')
            and number(search['angle_tolerance_deg']) == Decimal('.01'), 'unsupported_contact_policy')
    a,b,length,alternatives = verify_pair(edges, rings, endpoints, crossed, number(search['search_distance_mm']))
    factor = number(unit['conversion_to_meter'])
    with localcontext(Context(prec=max(28, len(length.as_tuple().digits) + len(factor.as_tuple().digits)))) as conversion:
        conversion.traps[Inexact] = conversion.traps[Rounded] = True
        meters = length*factor
    require({a,b} == {tuple(map(number,derived[k])) for k in ('from_wcs','to_wcs')}
            and dot(vector(a,b),vector(a,b)) == number(derived['squared_mm'])
            and length == number(derived['length_mm']) and meters == number(derived['length_m']),
            'declared_length_or_endpoints_mismatch')
    ownership = {}
    path_views = {}
    require(isinstance(request['traversals'],list) and request['traversals'], 'empty_traversals')
    for traversal in request['traversals']:
        require(set(traversal) == {'item_id', 'endpoints'}, 'unexpected_traversal_fields')
        item = traversal['item_id']
        require(isinstance(item,str) and item.strip() and sorted(traversal['endpoints']) == endpoints,
                'traversal_not_authorized')
        ownership[item] = [stable]
        enter, leave = traversal['endpoints']
        order = (enter[0], leave[0])
        path_views[order] = [
            dict(kind='geometry', handle=enter[0], to_endpoint=enter[2]),
            dict(kind='approved_recovered_gap', ref=stable, from_endpoint=enter, to_endpoint=leave),
            dict(kind='geometry', handle=leave[0], from_endpoint=leave[2])]
    native = [dict(kind='geometry',identity=row['identity'],vertices_wcs_mm=row['vertices_wcs_mm'],
                   layer=row['layer'],linetype=row['explicit_linetype'],
                   native_length_mm=str(norm(vector(*edges[row['identity']['handle']]['vertices']))))
              for row in parents]
    recovered = dict(kind='approved_recovered_gap',id=stable, scope=scope, endpoints=endpoints, parents=[r['identity'] for r in parents],
                     wcs_mm=[[str(x) for x in p] for p in (a,b)], length_mm=str(length),length_m=str(meters),
                     squared_length_mm2=str(dot(vector(a,b),vector(a,b))),
                     crossed_witness=review['crossed']['identity'],crossed_connection_allowed=False,
                     competing_continuation_status='excluded_in_reviewed_inventory',
                     rejected_nearby_endpoints=alternatives,
                     eligibility='project_path_component_only',
                     provenance=dict(review_sha256=review_hash,assumption_id=rule['id'],
                                     assumption_sha256=review['assumption_sha256'],unit=unit_ref,
                                     manifest_sha256=src['manifest_sha256'],report_sha256=src['snapshot']))
    return dict(RoutePathComponentVersion=1,status='qualified',native_steps=native,
                observed_visual_gap=dict(kind='visual',endpoints=endpoints,length_mm=str(length),additive=False),
                ordered_path_views=[path_views[k] for k in sorted(path_views)],
                approved_recovered_components=[recovered],item_component_refs=ownership,
                unresolved_gaps=[],other_approved_adjustments=[],other_adjustments_status='not_evaluated',
                formal_quantity=None)


def project(request_path, review_path, approved_review_sha256):
    try:
        # The reviewed coordinate measurement uses 48 significant digits for the
        # square root. Preserve its exact radicand; unit conversion above is exact.
        with localcontext(Context(prec=48)):
            review = json.loads(pinned(Path(review_path),approved_review_sha256))
            path = Path(request_path)
            return _verified_projection(json.loads(path.read_bytes()),review,approved_review_sha256,path.parent)
    except (ValueError, OSError, KeyError, IndexError, TypeError, ArithmeticError) as exc:
        return dict(RoutePathComponentVersion=1,status='blocked',reason=str(exc),unresolved_gaps=['unqualified_request'],
                    approved_recovered_components=[],item_component_refs={},formal_quantity=None)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('request','review','approved_review_sha256'):
        parser.add_argument(name)
    args = parser.parse_args()
    print(json.dumps(project(args.request,args.review,args.approved_review_sha256),allow_nan=False))
