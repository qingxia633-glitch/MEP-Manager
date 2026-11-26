"""Targeted LTYPE evidence. Input triples retain entget order and native types."""
import math
import re


def triples(raw):
    if not isinstance(raw, list) or not raw:
        raise ValueError("empty native record")
    for row in raw:
        if not isinstance(row, list) or len(row) != 3 or type(row[0]) is not int:
            raise ValueError("malformed native DXF triple")
    return raw


def field(rows, code, kind, issues, required=True):
    hits = [(t, v) for c, t, v in rows if c == code]
    if not hits and not required:
        return None
    if len(hits) == 1 and hits[0][0] == kind:
        value = hits[0][1]
        if kind == "STR" and isinstance(value, str):
            return value
        if kind == "INT" and type(value) is int:
            return value
        if kind == "REAL" and isinstance(value, str):
            try:
                number = float(value)
                if math.isfinite(number):
                    return number
            except ValueError:
                pass
        if kind == "ENAME" and isinstance(value, str) and re.fullmatch("[0-9a-fA-F]+", value):
            return value
    issues.append(f"missing_invalid_or_duplicate_{code}")
    return None


def record_identity(rows, expected):
    issues = []
    typ = field(rows, 0, "STR", issues)
    name = field(rows, 2, "STR", issues)
    handle = field(rows, 5, "STR", issues)
    if issues or typ != expected or not name or not re.fullmatch("[0-9A-Fa-f]+", handle or ""):
        raise ValueError(f"unverified {expected} identity")
    return name, handle


def pattern_element(rows, idx, styles):
    issues = []
    length = field(rows, 49, "REAL", issues)
    bits = field(rows, 74, "INT", issues, required=False)
    flags = bits if bits is not None else 0  # documented DXF default
    embedded = {0: "none", 2: "text", 4: "shape"}.get(flags & 6, "unknown")
    if flags not in (0, 2, 3, 4, 5):
        embedded = "unknown"
        issues.append("unsupported_flags")
    complex_element = embedded in ("shape", "text")
    text = field(rows, 9, "STR", issues, required=embedded == "text")
    shape = field(rows, 75, "INT", issues, required=complex_element)
    style = field(rows, 340, "ENAME", issues, required=complex_element)
    rotation = field(rows, 50, "REAL", issues, required=complex_element)
    scale, dx, dy = (field(rows, c, "REAL", issues, required=False) for c in (46, 44, 45))
    if complex_element and style not in styles:
        issues.append("style_not_verified")
    if embedded == "text" and (not text or shape != 0):
        issues.append("invalid_text_element")
    if embedded == "shape" and (shape is None or shape < 0):
        issues.append("invalid_shape_number")
    if text is not None and embedded != "text":
        issues.append("unexpected_text")
    if not complex_element and any(c in (75, 340, 50, 46, 44, 45) for c, _, _ in rows):
        issues.append("unexpected_complex_fields")
    if any(c not in (49, 74, 75, 340, 46, 50, 44, 45, 9) for c, _, _ in rows):
        issues.append("unknown_element_field")
    stroke = None if length is None else ("dash" if length > 0 else "gap" if length < 0 else "dot")
    return dict(index=idx, length=length, stroke=stroke, flags=bits, embedded_kind=embedded,
                embedded_text=text if embedded == "text" else None, shape_number=shape,
                style_reference=style, scale=scale, rotation_radians=rotation,
                rotation_mode=("absolute" if flags & 1 else "relative") if complex_element else None,
                offset_x=dx, offset_y=dy, raw=rows, issues=issues)


def definition(raw, styles, source):
    triples(raw)
    name, handle = record_identity(raw, "LTYPE")
    header, groups, issues = [], [], []
    for row in raw:
        if row[0] == 49:
            groups.append([])
        (groups[-1] if groups else header).append(row)
    flags = field(header, 70, "INT", issues)
    description = field(header, 3, "STR", issues)
    alignment = field(header, 72, "INT", issues)
    count = field(header, 73, "INT", issues)
    length = field(header, 40, "REAL", issues)
    if alignment != 65 or length is None or length < 0:
        issues.append("invalid_pattern_header")
    if any(c in (74, 75, 340, 46, 50, 44, 45, 9) for c, _, _ in header):
        issues.append("orphan_element_field")
    if count != len(groups):
        issues.append("element_count_mismatch")
    elements = [pattern_element(group, i, styles) for i, group in enumerate(groups)]
    if any(e["issues"] for e in elements):
        issues.append("incomplete_element")
    if length is not None and all(e["length"] is not None for e in elements):
        if not math.isclose(length, sum(abs(e["length"]) for e in elements), abs_tol=1e-9):
            issues.append("pattern_length_mismatch")
    return dict(name=name, handle=handle, source=source, flags=flags, description=description,
                alignment=alignment, declared_count=count, pattern_length=length, elements=elements,
                raw=raw, status="partial" if issues else "read", issues=issues)


def associate(style, source, definitions):
    identity = style["identity"]
    result = dict(identity=identity, status="unresolved", observed_embedded_codes=[],
                  lexical_code_candidates=[], project_legend_correspondence="unresolved",
                  engineering_function_applicability="unresolved")
    required = ("project_id", "drawing_instance_id", "report_sha256", "dwg_sha256")
    if (identity.get("parent_path") != [] or not identity.get("handle")
            or any(not source.get(k) or identity.get(k) != source[k] for k in required)):
        return result
    hint = style["style_resolution_status"]["linetype"]
    result["resolution_hint"] = hint
    if hint == "direct":
        name = style["raw_entity_style"]["entity_linetype"]["value"]
    elif hint == "bylayer_candidate":
        raw = style["raw_entity_style"]["entity_linetype"]
        if raw.get("status") != "read" or str(raw["value"]).upper() != "BYLAYER":
            return result
        name = style["layer_raw_style"]["fields"]["layer_linetype"]["value"]
    else:
        return result
    matches = [d for d in definitions if d["source"] == source and d["name"].upper() == name.upper()]
    if len(matches) == 1 and matches[0]["status"] == "read":
        d = matches[0]
        codes = [e["embedded_text"] for e in d["elements"] if e["embedded_kind"] == "text"]
        result.update(status="explicit" if hint == "direct" else "bylayer_candidate",
                      definition_handle=d["handle"], observed_embedded_codes=codes,
                      lexical_code_candidates=list(dict.fromkeys(codes)))
    return result
