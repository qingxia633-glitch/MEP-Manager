import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from linetype_definition import associate, definition
from verify_linetypes import unpack, verify
from report_manifest import write_manifest

SOURCE = dict(project_id="test", drawing_instance_id="drawing", dwg_sha256="bytes", report_sha256="snapshot")
STYLE = [[0, "STR", "STYLE"], [5, "STR", "A"], [2, "STR", "font"]]


def rec(elements=(), name="sample"):
    length = sum(abs(float(v)) for rows in elements for c, _, v in rows if c == 49)
    return [[0, "STR", "LTYPE"], [2, "STR", name], [5, "STR", "B"], [3, "STR", "pattern"],
            [70, "INT", 0], [72, "INT", 65], [73, "INT", len(elements)], [40, "REAL", str(length)],
            *[row for element in elements for row in element]]


def element(bits=2, text="X"):
    rows = [[49, "REAL", "-2.0"], [74, "INT", bits], [75, "INT", 7 if bits & 4 else 0],
            [340, "ENAME", "A"], [50, "REAL", "0.25"], [46, "REAL", "0.1"],
            [44, "REAL", "-1.5"], [45, "REAL", "0"]]
    if text is not None:
        rows.append([9, "STR", text])
    return rows


def parse(*elements):
    return definition(rec(elements), {"A": STYLE}, SOURCE)


def entity(mode="direct", name="sample"):
    return {"identity": dict(SOURCE, handle="E", parent_path=[]), "style_resolution_status": {"linetype": mode},
            "raw_entity_style": {"entity_linetype": {"status": "read", "value": "BYLAYER" if mode == "bylayer_candidate" else name}},
            "layer_raw_style": {"fields": {"layer_linetype": {"value": name}}}}


class PatternTests(unittest.TestCase):
    def test_continuous(self):
        d = parse()
        self.assertEqual((d["status"], d["elements"], d["pattern_length"]), ("read", [], 0))

    def test_text(self):
        e = parse(element())["elements"][0]
        self.assertEqual((e["stroke"], e["embedded_text"], e["offset_x"]), ("gap", "X", -1.5))

    def test_repeated_order(self):
        elems = [element(text="甲"), element(text="乙"), element(text="甲")]
        d = parse(*elems)
        self.assertEqual([e["embedded_text"] for e in d["elements"]], ["甲", "乙", "甲"])
        self.assertEqual(d["raw"], rec(elems))

    def test_sign_and_omitted_simple_flag(self):
        d = parse([[49, "REAL", "3"]], [[49, "REAL", "-1"]], [[49, "REAL", "0"]])
        self.assertEqual(d["status"], "read")
        self.assertEqual([e["stroke"] for e in d["elements"]], ["dash", "gap", "dot"])

    def test_shape_and_rotation(self):
        for bits in [2, 3, 4, 5]:
            with self.subTest(bits=bits):
                d = parse(element(bits, None if bits & 4 else "X"))
                self.assertEqual(d["status"], "read")
                e = d["elements"][0]
                self.assertEqual(e["rotation_mode"], "absolute" if bits & 1 else "relative")
                self.assertEqual(e["shape_number"], 7 if bits & 4 else 0)
                self.assertEqual(e["embedded_text"], None if bits & 4 else "X")

    def test_unknown_and_conflicting_flags(self):
        for bits in (6, 8, -1):
            self.assertEqual(parse(element(bits))["status"], "partial")

    def test_style_missing(self):
        self.assertEqual(definition(rec([element()]), {}, SOURCE)["status"], "partial")

    def test_incomplete_pattern(self):
        for c in (340, 50, 75, 9):
            self.assertEqual(parse([r for r in element() if r[0] != c])["status"], "partial")

    def test_orphan_duplicate_number_and_length(self):
        for col, val in ((73, 2), (40, "9.0"), (72, 2)):
            r = rec([element()])
            next(x for x in r if x[0] == col)[2] = val
            self.assertEqual(definition(r, {"A": STYLE}, SOURCE)["status"], "partial")
        self.assertEqual(parse(element() + [[9, "STR", "Y"]])["status"], "partial")
        self.assertEqual(definition(rec() + [[9, "STR", "Z"]], {}, SOURCE)["status"], "partial")

    def test_explicit_and_bylayer(self):
        d = parse(element())
        for mode, status in (("direct", "explicit"), ("bylayer_candidate", "bylayer_candidate")):
            link = associate(entity(mode, "SAMPLE"), SOURCE, [d])
            self.assertEqual((link["definition_handle"], link["status"]), ("B", status))

    def test_byblock_and_nested(self):
        for mode in ("unresolved_byblock", "unresolved"):
            self.assertEqual(associate(entity(mode), SOURCE, [parse()])["status"], "unresolved")
        s = entity()
        s["identity"]["parent_path"] = ["D"]
        self.assertEqual(associate(s, SOURCE, [parse()])["status"], "unresolved")

    def test_contradictory_layer_hint(self):
        s = entity("bylayer_candidate")
        s["raw_entity_style"]["entity_linetype"]["value"] = "Other"
        self.assertEqual(associate(s, SOURCE, [parse()])["status"], "unresolved")

    def test_cross_drawing_snapshot_collision(self):
        d = parse(element())
        for key in SOURCE:
            other = {**SOURCE, key: "other"}
            self.assertEqual(associate(entity(), SOURCE, [dict(d, source=other)])["status"], "unresolved")
            self.assertEqual(associate(entity(), other, [d])["status"], "unresolved")
        self.assertEqual(associate(entity(), SOURCE, [d, d])["status"], "unresolved")

    def test_neighbor_and_pattern_do_not_propagate(self):
        defs = [parse(element(text="X，Y")), definition(rec(name="Continuous"), {}, SOURCE)]
        result = associate(entity(name="Continuous"), SOURCE, defs)
        self.assertEqual(result["observed_embedded_codes"], [])
        self.assertEqual(result["engineering_function_applicability"], "unresolved")
        self.assertNotIn("quantity", result)
        self.assertEqual(associate(entity(), SOURCE, defs)["lexical_code_candidates"], ["X，Y"])


def capture():
    def stage(which, fn, args):
        return dict(kind="dbmod_stage", stage=which, call=fn, target_context="sample",
                    before=0, after=0, argument_tokens=args)
    return [dict(kind="header", LinetypeDefinitionEvidenceVersion=1, active_document="shadow.dwg",
                 before_load=0, after_load=0, names=["sample"], request_sha256="pin"),
            stage("ltype_lookup", "TBLOBJNAME", ['"LTYPE"', '"sample"']),
            stage("ltype_read", "ENTGET", ["token"]), stage("style_read", "ENTGET", ["style"]),
            dict(kind="style", raw=STYLE), dict(kind="definition", requested="sample", raw=rec([element()])),
            dict(kind="complete", dbmod=0)]


class AcquisitionTests(unittest.TestCase):
    def unpack(self, events):
        return unpack(events, dict(names=["sample"], shadow="shadow.dwg"), "pin", SOURCE)

    def test_ordered_capture(self):
        defs, styles, gaps = self.unpack(capture())
        self.assertEqual((defs[0]["status"], styles, gaps), ("read", {"A": STYLE}, []))

    def test_dirty_incomplete_mismatched_or_swapped(self):
        for idx, key, val in [(0, "active_document", "other"), (0, "request_sha256", ""),
                              (0, "after_load", 1), (1, "before", 1), (2, "after", 1),
                              (3, "target_context", "other"), (-1, "dbmod", 1)]:
            rows = capture()
            rows[idx][key] = val
            with self.assertRaises(ValueError):
                self.unpack(rows)
        with self.assertRaises(ValueError):
            self.unpack(capture()[:-1])

    def test_wrong_style_type_or_name(self):
        rows = copy.deepcopy(capture())
        rows[4]["raw"][0][2] = "BLOCK"
        with self.assertRaises(ValueError):
            self.unpack(rows)
        rows = capture()
        rows[5]["requested"] = "wrong"
        with self.assertRaises(ValueError):
            self.unpack(rows)

    def test_no_result_lookup(self):
        rows = capture()
        defs, _, gaps = self.unpack(rows[:2] + [dict(kind="unavailable", requested="sample"), rows[-1]])
        self.assertEqual((defs, gaps), ([], ["sample"]))

    def test_external_acceptance_and_input_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, shadow, entity_dwg = (root / n for n in ("author.dwg", "shadow.dwg", "entity.dwg"))
            for path in (source, shadow, entity_dwg):
                path.write_bytes(b"synthetic bytes")
            report, manifest = root / "full.txt", root / "manifest.json"
            report.write_text(
                f'DWG="{entity_dwg.as_posix()}"\nExtractorVersion="2.8-field-graph-evidence-v1"\n'
                'AcquisitionMode="ModelSpaceTopLevelAllLayers"\nModelSpaceTopLevel="included"\n'
                'EntityHandle="E"\nDXF_Type="LINE"\nStyleEvidenceVersion="1"\n'
                'Style.entity_linetype_mode.Status="read"\nStyle.entity_linetype_mode.Value="explicit"\n'
                'Style.entity_linetype_mode.Source="DXF"\nStyle.entity_linetype.Status="read"\n'
                'Style.entity_linetype.Value="sample"\nStyle.entity_linetype.Source="DXF"\n'
                'ReadErrorCount=0\nEND_OF_REPORT: completed\n', encoding="utf-8-sig")
            write_manifest(report, manifest)
            def sha(path):
                return hashlib.sha256(path.read_bytes()).hexdigest()
            trace, req, native = (root / n for n in ("trace", "request", "capture"))
            q = dict(SOURCE, names=["sample"], handles=["E"], authoritative=str(source),
                     shadow=str(shadow), report_dwg=str(entity_dwg), dwg_sha256=sha(source),
                     report=str(report), report_sha256=sha(report), manifest=str(manifest),
                     manifest_sha256=sha(manifest), dbmod_trace=str(trace))
            req.write_text(json.dumps(q), encoding="utf8")
            events = capture()
            events[0].update(active_document=str(shadow), request_sha256=sha(req))
            lines = ["before_load|0", "after_load|0"]
            for event in events:
                if event["kind"] == "dbmod_stage":
                    lines.append(f'{event["stage"]}|0|0|{event["call"]}')
                lines.append("report_output|0|0|serialize/write-line")
            trace.write_text("\n".join(lines + ["after_close|0"]), encoding="utf-8-sig")
            native.write_text("\n".join(map(json.dumps, events)), encoding="utf-8-sig")
            self.assertEqual(verify(req, native)["associations"][0]["observed_embedded_codes"], ["X"])
            for path in (shadow, report, manifest, trace):
                original = path.read_bytes()
                path.write_bytes(original + b"bad")
                with self.assertRaises(ValueError):
                    verify(req, native)
                path.write_bytes(original)
