"""Raw layout plumbing only. No grouping, scope or binding decisions."""
import math
import re
from report_text import serialized_field, text_record

SCALARS = ('rotation', 'text_height', 'width_factor', 'oblique_angle', 'text_style',
           'horizontal_alignment', 'vertical_alignment', 'direction_wcs',
           'reference_width', 'attachment_point', 'alignment_point_wcs')
LAYOUT_KEYS = ('layout_evidence_version', 'layout_evidence', 'position_status',
               'position_frame', 'position_source', 'position_raw', 'position_contract_status',
               'visibility_evidence', 'visibility_status', 'tag') + SCALARS + tuple(k+'_status' for k in SCALARS)


def layout_record(record, kind):
    prefix = 'AttributeLayout.' if kind == 'ATTRIB' else ''
    fields = {}

    def raw(key):
        literal = serialized_field(record, prefix + key)
        if literal is None or literal == 'nil':
            return None
        return text_record(literal)['decoded_text'] if literal.startswith('"') else literal

    def triple(value):
        if not isinstance(value, str) or not re.fullmatch(r'\([^()]+\)', value):
            return None
        try:
            values = [float(x) for x in value[1:-1].split()]
            return values if len(values) == 3 and all(math.isfinite(x) for x in values) else None
        except ValueError:
            return None

    def scalar(value):
        try:
            value = float(value)
            return value if math.isfinite(value) else None
        except (TypeError, ValueError):
            return None

    def read(key, parser, status_key=None):
        value = raw(key)
        reported = raw(status_key or key + '_Status')
        parsed = parser(value) if value is not None else None
        status = reported or ('missing' if value is None else 'unresolved')
        if status == 'read' and parsed is None:
            status = 'invalid_result'
        fields[key] = {'raw_serialized_value': serialized_field(record, prefix + key),
                       'reported_status': reported, 'status': status}
        return (parsed if status == 'read' else None), status

    result = {'layout_evidence_version': '1'}
    pos, status = read('Position_WCS', triple, 'positionStatus')
    frame = raw('positionFrame') or 'unknown'
    current = any(serialized_field(record, prefix + k) is not None
                  for k in ('Position_WCS', 'positionStatus', 'positionFrame'))
    source = 'exporter_wcs' if current else 'missing'
    if current and status == 'read' and frame != 'WCS':
        pos, status = None, 'unresolved'
    legacy_raw = None
    if not current:
        if kind == 'ATTRIB':
            dxf = serialized_field(record, 'Attribute_DXF') or ''
            match = re.search(r'\(10 ([^)]+)\)', dxf)
            legacy_raw = triple('(' + match[1] + ')') if match else None
            if match:
                source, status, frame = 'legacy_raw_dxf', 'unresolved', 'entity_ocs'
        else:
            literal = serialized_field(record, 'Insertion_WCS')
            if literal is not None:
                pos = triple(literal)
                source, frame = 'legacy_exporter_wcs', 'WCS'
                status = 'read' if pos is not None else 'invalid_result'
    result.update(position_wcs=pos, position_status=status, position_frame=frame,
                  position_source=source, position_raw=legacy_raw,
                  position_contract_status='current' if current else 'legacy')
    lo, ls = read('bboxMin', triple, 'bboxStatus')
    hi, hs = read('bboxMax', triple, 'bboxStatus')
    bs = raw('bboxStatus') or ('missing' if raw('bboxMin') is None and raw('bboxMax') is None else 'unresolved')
    bf = raw('bboxFrame') or 'unknown'
    if bs == 'read':
        if ls != 'read' or hs != 'read' or any(x > y for x, y in zip(lo, hi)):
            bs = 'invalid_result'
        elif bf != 'WCS':
            bs = 'unresolved'
    result['bounds'] = {'min_wcs': lo if bs == 'read' else None,
                        'max_wcs': hi if bs == 'read' else None,
                        'frame': bf, 'status': bs, 'reported_status': raw('bboxStatus'),
                        'error_raw': raw('bboxError_RAW')}
    names = {'rotation':'Rotation', 'text_height':'TextHeight', 'width_factor':'WidthFactor',
             'oblique_angle':'ObliqueAngle', 'text_style':'TextStyle',
             'horizontal_alignment':'HorizontalAlignment', 'vertical_alignment':'VerticalAlignment',
             'direction_wcs':'Direction_WCS_RAW', 'reference_width':'ReferenceWidth',
             'attachment_point':'AttachmentPoint', 'alignment_point_wcs':'AlignmentPoint_WCS'}
    for name, key in names.items():
        parser = triple if name in ('direction_wcs', 'alignment_point_wcs') else (lambda x:x) if name == 'text_style' else scalar
        value, state = read(key, parser, 'AlignmentPointStatus' if name == 'alignment_point_wcs' else None)
        if kind == 'MTEXT' and name == 'rotation':
            value = None
            state = raw('Rotation_Status') or 'not_interpreted_use_direction_vector'
            if state == 'read':
                state = 'not_interpreted_use_direction_vector'
        if name == 'alignment_point_wcs' and raw('AlignmentPointFrame') != 'WCS':
            value, state = None, 'unresolved' if state == 'read' else state
        result[name], result[name + '_status'] = value, state
    visibility = raw('VisibilityEvidence')
    result.update(visibility_evidence=visibility,
                  visibility_status='read' if visibility is not None else 'missing')
    if kind != 'ATTRIB':
        from line_style import read_field
        visible = read_field(record, 'entity_visibility')
        result.update(visibility_evidence=visible, visibility_status=visible['status'])
    result['layout_evidence'] = {'fields': fields, 'position_error_raw':raw('positionError_RAW'),
                                 'parent_insert_handle':raw('ParentINSERTHandle'),
                                 'raw_position':raw('Insertion_DXF10_RAW'),
                                 'raw_position_frame':raw('InsertionRawFrame')}
    return result
