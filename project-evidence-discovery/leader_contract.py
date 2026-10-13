"""Pure leader-record validation shared by adapter and direct Discovery entry.

No evidence creation, tolerance enlargement, CAD access or semantic approval.
"""
import math

TOP_LEVEL = 'ModelSpace top-level only'

def annotation_identity(annotation):
    return {key:annotation.get(key) for key in
            ('handle','parent_path','type','source_drawing','project_id')}

def finite_point(value):
    return (isinstance(value,(list,tuple)) and len(value)==3 and
            all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in value))

def validate_leader_evidence_record(record, annotations, context, tolerance=.001):
    if record.get('type') in ('MLEADER','MULTILEADER'):
        # No classic vertex/annotation semantics are imposed on MLEADER.
        # This version preserves capability output but has no validated binding chain.
        checks={'version':record.get('evidence_version')=='1',
                'scope':record.get('acquisition_scope')==TOP_LEVEL and record.get('reported_scope')==TOP_LEVEL,
                'path':record.get('parent_path')==[] and record.get('reported_parent_path')=='[]',
                'mleader_object_chain_validated':False}
        return {'validation':checks,'association_status':'unresolved',
                'failure_reasons':[key for key,value in checks.items() if not value]}
    vertices=record.get('vertices_wcs')
    geometry=isinstance(vertices,list) and len(vertices)>=2 and all(finite_point(v) for v in vertices)
    arrow=record.get('arrow_wcs');arrow_valid=finite_point(arrow)
    drawing=context.get('drawing_ref');project=context.get('project_id')
    annotation_path=record.get('annotation_parent_path',record.get('parent_path'))
    matches=[a for a in annotations if a.get('handle')==record.get('annotation_handle') and
             a.get('parent_path')==annotation_path and
             a.get('source_drawing')==record.get('source_drawing') and
             a.get('project_id')==record.get('project_id')]
    conflict=bool(matches and any(a!=matches[0] for a in matches))
    annotation=matches[0] if matches and all(a==matches[0] for a in matches) else None
    declared=record.get('validation')
    flags_ok=isinstance(declared,dict) and bool(declared) and all(v is True for v in declared.values())
    # Adapter first pass has no declared flags; consumers still recompute every
    # condition below. Omitted flags cannot repair any missing source field.
    if declared is None:flags_ok=True
    checks={
      'version':record.get('evidence_version')=='1',
      'classic':record.get('type')=='LEADER',
      'scope':record.get('acquisition_scope')==TOP_LEVEL and record.get('reported_scope')==TOP_LEVEL,
      'path':record.get('parent_path')==[] and record.get('reported_parent_path')=='[]',
      'identity':all(k in record for k in ('source_drawing','project_id','parent_path')) and
                 record['source_drawing']==drawing and record['project_id']==project,
      'coordinates':record.get('coordinate_system')=='WCS',
      'geometry':geometry and record.get('geometry_status')=='read',
      'count':type(record.get('vertex_count')) is int and geometry and record['vertex_count']==len(vertices),
      'arrow':arrow_valid and record.get('arrow_status')=='read',
      'arrow_origin':bool(geometry and arrow_valid and math.dist(arrow,vertices[0])<=tolerance),
      'annotation':record.get('annotation_status')=='resolved' and bool(record.get('annotation_handle')),
      'annotation_exists':annotation is not None,
      'annotation_path':annotation_path==[],
      'annotation_conflict':not conflict,
      'annotation_type':bool(annotation and record.get('annotation_type') in ('TEXT','MTEXT') and
                             record['annotation_type']==annotation.get('type')),
      'annotation_text':bool(annotation and annotation.get('text_decode_status')=='read'),
      'declared_validation':flags_ok,
      'provenance':bool(record.get('provenance')),
    }
    return {'validation':checks,'association_status':'explicit' if all(checks.values()) else 'unresolved',
            'validated_annotation_identity':annotation_identity(annotation) if all(checks.values()) else None,
            'failure_reasons':[key for key,value in checks.items() if not value]}
