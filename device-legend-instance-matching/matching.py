"""Compare definition-local native curves. This module grants no device role."""
from decimal import Decimal, InvalidOperation, localcontext
from collections import Counter


def values(raw, code):
    return [value for group, _, value in raw if group == code]


def one(raw, code):
    items = values(raw, code)
    if len(items) != 1:
        raise ValueError(f"missing/duplicate DXF {code}")
    return items[0]


def number(value):
    n = Decimal(str(value))
    if not n.is_finite() or len(n.as_tuple().digits) > 28 or abs(n.adjusted()) > 24:
        raise ValueError("unsupported numeric range")
    return n


def point(value, size=3):
    if not isinstance(value, list) or len(value) != size:
        raise ValueError("invalid coordinate dimension")
    return tuple(map(number, value))


def check_normal(raw):
    if point(one(raw, 210)) != (0, 0, 1):
        raise ValueError("unsupported OCS normal")


def local_point(raw, code, base):
    return tuple(v-b for v,b in zip(point(one(raw, code)), base))


def solid_boundary(raw, base):
    # Native strip order: 10-11 and 12-13 are opposite edges.
    ring = [local_point(raw, code, base) for code in (10, 11, 13, 12)]
    if len({p[2] for p in ring}) != 1:
        raise ValueError("nonplanar SOLID")
    # An adjacent repeated corner collapses one edge. Preserve raw slots on the member.
    ring = [p for i,p in enumerate(ring) if p != ring[i-1]]
    if len(ring) < 3 or len(set(ring)) != len(ring):
        raise ValueError("degenerate SOLID")
    turns = []
    for i,b in enumerate(ring):
        a, c = ring[i-1], ring[(i+1) % len(ring)]
        turns.append((b[0]-a[0])*(c[1]-b[1]) - (b[1]-a[1])*(c[0]-b[0]))
    if not (all(t > 0 for t in turns) or all(t < 0 for t in turns)):
        raise ValueError("unverified SOLID topology")
    if turns[0] < 0:
        ring.reverse()
    start = ring.index(min(ring))
    return tuple(ring[start:] + ring[:start])


def geometry(symbol):
    """Return centerline and width-sensitive multisets plus disjoint member evidence."""
    if not symbol.get("definition"):
        raise ValueError("current definition missing")
    if symbol["dynamic"] != ":vlax-false" or symbol["name"].startswith("*"):
        raise ValueError("dynamic or anonymous definition")
    if not symbol["effective_name"] or symbol["name"] != symbol["effective_name"]:
        raise ValueError("unqualified effective definition")
    if not symbol["inventory_verified"]:
        reasons = symbol.get("definition_coverage", {}).get("blocking_reasons", [])
        raise ValueError("definition inventory incomplete" + (": " + ", ".join(reasons) if reasons else ""))
    insert = symbol["transform"]
    if values(insert, 60) not in ([], [0]):
        raise ValueError("instance visibility unsupported")
    check_normal(insert)
    point(one(insert, 10))
    number(one(insert, 50))
    scales = [number(one(insert, c)) for c in (41, 42, 43)]
    if min(scales) <= 0 or len(set(scales)) != 1:
        raise ValueError("mirrored or nonuniform instance")
    if any(any(v not in (0, 1) for v in values(insert, c)) for c in (70, 71)):
        raise ValueError("array INSERT")
    base = point(symbol["base"])
    paths, details, auxiliary, widths_seen = [], [], [], []
    for node in symbol["members"]:
        raw, kind = node["raw"], node["entity_type"]
        if kind == "ATTDEF" and int(one(raw, 70)) & 1:
            continue
        if kind not in ("LINE", "LWPOLYLINE", "CIRCLE", "ARC", "SOLID", "POINT"):
            raise ValueError("unsupported member " + kind)
        if values(raw, 60) not in ([], [0]):
            raise ValueError("member visibility unsupported")
        check_normal(raw)
        if any(number(v) != 0 for v in values(raw, 39)):
            raise ValueError("extruded member")
        width = ()
        if kind == "POINT":
            auxiliary.append(local_point(raw, 10, base))
            continue
        if kind == "SOLID":
            try:
                boundary = solid_boundary(raw, base)
            except (ValueError, InvalidOperation, TypeError) as error:
                raise ValueError(f"SOLID {node.get('handle', '?')}: {error}") from error
            details.append(((kind, boundary), width))
            continue
        if kind in ("CIRCLE", "ARC"):
            radius = number(one(raw, 40))
            if radius <= 0:
                raise ValueError("invalid radius")
            path = (kind, local_point(raw, 10, base), radius)
            if kind == "ARC":
                start, end = (number(one(raw, c)) for c in (50, 51))
                # entget reports radians rounded by the probe to 12 places.
                # Limit v1 to canonical angles. Preserve ordered CCW endpoints.
                tau = Decimal("6.283185307180")
                if not (0 <= start < tau and 0 <= end < tau and start != end):
                    raise ValueError("unsupported or degenerate ARC angles")
                path += (start, end)
        elif kind == "LINE":
            ends = [point(one(raw, code)) for code in (10, 11)]
            path = (kind, tuple(sorted(tuple(v-b for v,b in zip(end, base)) for end in ends)))
            width = ()
        else:
            count, flags = one(raw, 90), one(raw, 70)
            if type(count) is not int or count < 2 or flags not in (0, 1, 128, 129):
                raise ValueError("unsupported polyline flags/count")
            z = number(one(raw, 38)) - base[2]
            vertices, widths = [], []
            # Group per vertex; aggregate arrays alone can misplace a missing bulge.
            groups = []
            for code, _, v in raw:
                if code == 10:
                    groups.append({10: v})
                if code in (40, 41, 42):
                    if not groups or code in groups[-1]:
                        raise ValueError("invalid vertex data")
                    groups[-1][code] = v
            if len(groups) != count:
                raise ValueError("polyline vertex count mismatch")
            for group in groups:
                x, y = point(group[10], 2)
                vertices.append((x-base[0], y-base[1], z, number(group[42])))
                widths.append((number(group[40]), number(group[41])))
            path = (kind, flags, tuple(vertices))
            width = (number(one(raw, 43)), tuple(widths))
            if any(v < 0 for v in (width[0], *(v for pair in widths for v in pair))):
                raise ValueError("negative polyline width")
            widths_seen.append((node.get("handle"), [str(width[0]), [[str(x),str(y)] for x,y in widths]]))
        paths.append(path)
        details.append((path, width))
    if not details:
        raise ValueError("no comparable geometry")
    return Counter(paths), Counter(details), sorted(auxiliary), widths_seen


def compare(legend, instance, row):
    provenance = [s["identity"] for s in (legend, instance)]
    result = dict(DeviceLegendInstanceMatchVersion=1, comparison_contract_revision="block-local-1",
                  project_id=legend["identity"]["project_id"],
                  legend_symbol_identity=provenance[0], instance_identity=provenance[1],
                  legend_row_identity=row.get("row_id"), legend_membership_status=row["status"],
                  legend_evidence=row, source_definition_identity=legend.get("definition"),
                  target_definition_identity=instance.get("definition"),
                  name_evidence=[{k:s[k] for k in ("name", "effective_name")} for s in (legend, instance)],
                  attribute_evidence=[dict(actual=s["attributes"], defaults=s.get("defaults", []))
                                      for s in (legend, instance)],
                  transform_evidence=[s.get("transform") for s in (legend, instance)],
                  geometry_comparison_status="unresolved", match_status="unresolved",
                  exact_geometry_status="unresolved", centerline_geometry_status="unresolved",
                  presentation_attribute_differences=None, auxiliary_geometry_differences=None,
                  engineering_device_type_status="pending_independent_review",
                  device_name_evidence=dict(legend_row_texts=row.get("texts", []),
                        instance_attributes=instance["attributes"], definition_defaults=instance.get("defaults", []),
                        legend_attributes=legend["attributes"], legend_defaults=legend.get("defaults", [])),
                  candidate_device_roles=[], conflicting_evidence=[], missing_evidence=[],
                  supported_scope=None, propagated_attributes=[], provenance=provenance)
    try:
        for s in (legend, instance):
            i = s["identity"]
            if (not i.get("project_id") or i["project_id"] != result["project_id"]
                    or i.get("parent_path") != [] or not all(i.get(k) for k in
                    ("drawing", "handle", "snapshot_id", "dwg_sha256"))):
                raise ValueError("object provenance mismatch")
            definition = s.get("definition")
            if definition and (any(definition.get(k) != i[k] for k in ("dwg_sha256","drawing","project_id"))
                               or not definition.get("probe_sha256")):
                raise ValueError("definition provenance mismatch")
        for label, symbol in (("legend", legend), ("instance", instance)):
            if not symbol.get("definition"):
                result["missing_evidence"].append(label + ": current definition missing")
        if result["missing_evidence"]:
            return result
        with localcontext() as ctx:
            ctx.prec = 80
            a, aw, ap, widths_a = geometry(legend)
            b, bw, bp, widths_b = geometry(instance)
    except (ValueError, KeyError, InvalidOperation, TypeError) as error:
        result["missing_evidence"].append(str(error))
        return result
    result["exact_geometry_status"] = "equal" if aw == bw else "different_native_records"
    result["centerline_geometry_status"] = ("equal" if a == b else "different_native_records") if a or b else "not_applicable"
    result["auxiliary_geometry_differences"] = {} if ap == bp else dict(
        legend_points=[list(map(str,p)) for p in ap], instance_points=[list(map(str,p)) for p in bp])
    result["presentation_attribute_differences"] = presentation = {}
    if Counter(w for _,w in aw.elements() if w) != Counter(w for _,w in bw.elements() if w) or (
            a == b and {k:n for k,n in aw.items() if k[1]} != {k:n for k,n in bw.items() if k[1]}):
        presentation["polyline_widths"] = dict(legend=widths_a, instance=widths_b)
    for c, label in ((8,"layer"), (6,"linetype"), (62,"aci"), (420,"truecolor"), (370,"lineweight")):
        va, vb = (values(s["transform"], c) for s in (legend, instance))
        if va != vb:
            presentation["insert_raw_" + label] = dict(legend=va, instance=vb)
    structure_a = Counter(k[0] for k,w in aw.elements())
    structure_b = Counter(k[0] for k,w in bw.elements())
    if structure_a != structure_b:
        result.update(match_status="conflicting", geometry_comparison_status="different_native_primitive_inventory")
        result["conflicting_evidence"].append("different primitive inventory for proposed native geometry match")
        return result
    if a != b:
        # A different starting vertex, direction or segmentation can describe
        # the same polyline. v1 has no equivalence proof for those encodings.
        if any(path[0] == "LWPOLYLINE" for path in (*a, *b)):
            result["geometry_comparison_status"] = "different_native_path_records"
            result["missing_evidence"].append("equivalence across path encodings unverified")
        else:
            status = "different_native_line_members" if set(structure_a) == {"LINE"} else "different_native_curve_members"
            result.update(match_status="conflicting", geometry_comparison_status=status)
            result["conflicting_evidence"].append("different normalized native curve records")
        return result
    if {k:n for k,n in aw.items() if k[0][0]=="SOLID"} != {k:n for k,n in bw.items() if k[0][0]=="SOLID"}:
        result.update(match_status="conflicting", geometry_comparison_status="different_native_solid_boundaries")
        result["conflicting_evidence"].append("different filled boundaries")
        return result
    if aw == bw:
        result["geometry_comparison_status"] = "equal_native_geometry" if "SOLID" in structure_a else "equal_native_curves"
        if ap != bp:
            result["exact_geometry_status"] = "different_auxiliary_geometry"
    else:
        result["geometry_comparison_status"] = "equal_paths_different_widths"
    if aw != bw:
        result["conflicting_evidence"].append("native curve widths differ")
    if row["status"] not in ("bounded", "ambiguous") or not row.get("row_id"):
        result["missing_evidence"].append("no located legend row")
        return result
    result["match_status"] = "candidate"
    result["candidate_device_roles"] = row.get("lexical_roles", [])
    observed = {a["lexical_role"] for a in instance["attributes"]
                if a.get("lexical_role") not in (None, "unknown")}
    row_roles = {c["role"] for c in result["candidate_device_roles"]}
    if observed and row_roles and not observed <= row_roles:
        result.update(match_status="conflicting", candidate_device_roles=[])
        result["conflicting_evidence"].append("instance ATTRIB role differs from legend role candidate")
        return result
    if row["status"] == "bounded" and aw == bw and ap == bp:
        scope = "native_curves_and_fills_only" if "SOLID" in structure_a else "native_curve_geometry_only"
        result.update(match_status="supported", supported_scope=scope)
    elif row["status"] != "bounded":
        result["missing_evidence"].append("bounded legend row and cell")
    return result


def compare_set(pairs):
    """One instance may retain several candidate legends. Preserve every comparison."""
    results = [compare(*pair) for pair in pairs]
    def identity(r, key):
        i = r[key]
        return tuple(i[k] for k in ("project_id","drawing","snapshot_id","handle"))
    def key(r):
        return (identity(r, "instance_identity"), identity(r, "legend_symbol_identity"), r["legend_row_identity"] or "")
    if len({key(r) for r in results}) != len(results):
        raise ValueError("duplicate comparison")
    viable = [r for r in results if r["match_status"] in ("supported", "candidate")]
    counts = Counter(identity(r, "instance_identity") for r in viable)
    for r in viable:
        if counts[identity(r, "instance_identity")] > 1:
            r.update(match_status="ambiguous", supported_scope=None)
    return sorted(results, key=key)
