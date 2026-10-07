"""Small, deliberately closed applicability contract (no CAD or semantic inference)."""
CHANNELS = frozenset(('object_facts', 'region_memberships', 'system_memberships',
                     'local_group_memberships', 'explicit_bindings', 'exclusions',
                     'conflicting_evidence'))
STRENGTHS = frozenset(('direct_object_binding', 'direct_local_design_binding',
                      'system_mapping', 'project_rule_binding', 'drawing_fact'))


def combine(states):
    # A known failed requirement rules out applicability, even if another conflicts.
    # Conflicts are always retained in the output, never erased.
    if 'false' in states:
        return 'not_applicable'
    if 'conflicting' in states:
        return 'conflicting'
    if 'unknown' in states or not states:
        return 'unresolved'
    return 'applicable'
