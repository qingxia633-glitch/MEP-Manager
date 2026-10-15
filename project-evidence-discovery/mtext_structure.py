"""Conservative MTEXT paragraph evidence, never rendered text or scope approval."""
from copy import deepcopy
import re

from model import identity


def structure_record(annotation, snapshot_id):
    source = {'project_id': annotation.get('project_id'),
              'drawing_ref': annotation.get('source_drawing'),
              'parent_path': deepcopy(annotation.get('parent_path')),
              'handle': annotation.get('handle'), 'snapshot_id': snapshot_id}
    result = {'version': '1', 'status': 'unresolved', 'source_identity': source,
              'span_basis': 'entity.decoded_text Unicode characters; zero-based half-open',
              'paragraphs': [], 'separators': [], 'gaps': []}
    if annotation.get('type') != 'MTEXT':
        result['gaps'].append('not_mtext'); return result
    if (not all(isinstance(source[k], str) and source[k].strip()
                for k in ('project_id', 'drawing_ref', 'handle', 'snapshot_id'))
            or source['parent_path'] != []):
        result['gaps'].append('identity_missing_or_scope_not_top_level'); return result
    text = annotation.get('decoded_text')
    if annotation.get('text_decode_status') != 'read' or not isinstance(text, str):
        result['gaps'].append('exporter_decode_unresolved'); return result
    if not annotation.get('provenance'):
        result['gaps'].append('source_provenance_missing'); return result

    # Treat control payloads atomically: a backslash-P inside a font/stack payload
    # is not an established paragraph separator. Unknown payload extent stops scan.
    spans = []; start = 0; i = 0; depth = 0
    gaps = result['gaps']
    while i < len(text):
        ch = text[i]
        if text.startswith('%<', i):
            gaps.append('field_expression_unresolved'); break
        if ch in '\r\n':
            gaps.append('literal_line_break_not_interpreted')
        if ch in '{}':
            gaps.append('formatting_group_preserved')
            depth += 1 if ch == '{' else -1
            if depth < 0:
                gaps.append('unbalanced_group'); depth = 0
        if ch != '\\':
            i += 1; continue
        if i + 1 == len(text):
            gaps.append('truncated_escape'); break
        code = text[i + 1]
        if code == 'P':
            spans.append((start, i))
            result['separators'].append({'type': 'explicit_paragraph_break',
                                         'raw_fragment': text[i:i+2], 'source_span': [i, i+2]})
            i += 2; start = i; continue
        if code in '\\{}~LOKlok':
            gaps.append('formatting_escape_preserved'); i += 2; continue
        if code in 'FfHWT CcQApS'.replace(' ', ''):
            end = text.find(';', i+2)
            gaps.append('formatting_control_preserved')
            if end < 0:
                gaps.append('unterminated_control'); break
            i = end+1; continue
        if code == 'U' and re.match(r'\\U\+[0-9A-Fa-f]{4}', text[i:]):
            gaps.append('unicode_control_preserved'); i += 7; continue
        gaps.append('unknown_control_remaining_not_split'); break
    if depth:
        gaps.append('unbalanced_group')
    spans.append((start, len(text)))
    result['gaps'] = list(dict.fromkeys(gaps))
    result['status'] = 'partial' if gaps else 'read'
    for index, (start, end) in enumerate(spans):
        fragment = text[start:end]
        marker = re.match(r'^\s*(\d+[.、]|[（(]\d+[）)]|[一二三四五六七八九十]+、|[①②③④⑤⑥⑦⑧⑨⑩●]|-(?=\s))', fragment)
        heading = re.fullmatch(r'\s*(设计说明|说明|注|备注)\s*[:：]?\s*', fragment)
        paragraph_identity = dict(source, paragraph_index=index, source_span=[start, end])
        result['paragraphs'].append({
            'subelement_type': 'paragraph', 'paragraph_index': index,
            'identity': paragraph_identity, 'subelement_id': identity('mtext-paragraph-v1', paragraph_identity),
            'source_entity_handle': source['handle'], 'source_parent_path': deepcopy(source['parent_path']),
            'raw_fragment': fragment, 'decoded_text': fragment, 'source_span': [start, end],
            'structure_status': result['status'], 'text_interpretation': 'formatting_preserved_not_rendered',
            'list_marker_candidate': marker[1] if marker else None,
            'heading_lexical_candidate': heading[1] if heading else None,
            'provenance': deepcopy(annotation['provenance'])})
    return result
