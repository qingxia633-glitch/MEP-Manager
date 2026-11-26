"""Spatial review population and unique-instance accounting."""
from collections import Counter, defaultdict
from math import isfinite


def relation(point, box):
    if point is None or len(point)<2 or not all(isfinite(n) for n in point):
        return 'unresolved'
    x,y=point[:2]
    a,b,c,d=box
    if x<a or x>c or y<b or y>d:
        return 'outside'
    return 'on_boundary' if x in (a,c) or y in (b,d) else 'inside'


def identity(obj):
    return (obj['project_id'],obj['drawing_instance_id'],obj['snapshot'],tuple(obj['parent_path']),obj['handle'])


def merge_evidence(entries):
    grouped=defaultdict(list)
    for key,evidence in entries:
        grouped[key].append(evidence)
    return grouped


def reconcile(roles,role_status,geometry_types):
    roles,geom=set(roles),set(geometry_types)
    types=sorted(roles|geom)
    if role_status=='conflicting' or (roles and geom and roles.isdisjoint(geom)):
        return types,'conflicting'
    if not types:
        return types,'unresolved'
    return types,'multiple' if len(types)>1 else 'single'


def interior(rows):
    return [r for r in rows if not r['parent_path'] and r['boundary_relation']=='inside']


def duplicate_groups(rows):
    groups=defaultdict(set)
    for r in interior(rows):
        if r['entity_type']=='INSERT' and r['location'] is not None:
            groups[identity(r)[:3]+(tuple(r['location']),)].add(identity(r))
    return sorted(sorted(group) for group in groups.values() if len(group)>1)


def aggregate(rows):
    population=interior(rows)
    if len(set(map(identity,population)))!=len(population):
        raise ValueError('repeated survey object')
    classes=Counter(r['inventory_class'] for r in population)
    instances=[r for r in population if r['entity_type']=='INSERT' and r['inventory_class']!='confirmed_non_device']
    hits=Counter(t for r in instances for t in set(r['candidate_types']))
    groups=duplicate_groups(rows)
    counts=dict(distinct_native_object_count=len(population),
                distinct_device_candidate_count=classes['device_candidate'],
                confirmed_non_device_count=classes['confirmed_non_device'],
                unclassified_object_count=classes['unclassified'],
                candidate_type_hits=dict(sorted(hits.items())),
                single_candidate_instance_count=sum(len(set(r['candidate_types']))==1 for r in instances),
                multiple_candidate_instance_count=sum(len(set(r['candidate_types']))>1 for r in instances),
                unresolved_instance_count=sum(r['device_status']=='unresolved' for r in instances),
                conflicting_instance_count=sum(r['device_status']=='conflicting' for r in instances),
                suspected_duplicate_count=sum(map(len,groups)),suspected_duplicate_groups=len(groups),
                distinct_insert_count=sum(r['entity_type']=='INSERT' for r in population),
                approved_device_quantity=None,approved_floor_quantity=None)
    if sum(classes[k] for k in ('device_candidate','confirmed_non_device','unclassified'))!=len(population):
        raise ValueError('unaccounted object class')
    return counts
