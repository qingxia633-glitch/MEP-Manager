"""Exact instance/scope identity; missing paths are never ModelSpace defaults."""
def canonical_id(value):
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError('Nonempty canonical string identity required')
    return value


def scope_identity(binding):
    if not isinstance(binding, dict):
        raise ValueError('Structured scope binding required')
    project, drawing, edge = (canonical_id(binding.get(k)) for k in ('project_id', 'drawing_ref', 'edge_handle'))
    segment = binding.get('segment_id')
    if segment is not None:
        canonical_id(segment)
    kind = binding.get('scope_type')
    if kind not in ('edge', 'segment') or (kind == 'segment') != (segment is not None):
        raise ValueError('Scope kind/segment mismatch')
    path = binding.get('parent_path')
    if not isinstance(path, list):
        raise ValueError('Explicit parent_path required (ModelSpace uses [])')
    return project, drawing, kind, edge, segment, tuple(canonical_id(p) for p in path)


def identity_record(binding):
    project, drawing, kind, edge, segment, path = scope_identity(binding)
    return dict(project_id=project, drawing_ref=drawing, scope_type=kind,
                edge_handle=edge, segment_id=segment, parent_path=list(path))
