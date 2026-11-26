import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from project_legend import recover


def fixture(value="测试设备全称"):
    ident = dict(project_id="P", drawing="plan", snapshot_id="plan-hash", handle="AA", parent_path=[])
    attr = dict(tag="A", value=value, handle="AB", owner="AA")
    symbol = dict(identity=ident, attributes=[attr], name="block")
    direct = dict(attribute_tag="A", raw_value=value, source_handle="AB", source_definition_path=["AA"],
                  source="plan", evidence_type="instance_attrib")
    role = dict(device_handle="AA", evidence_identity=dict(project_id="P", drawing_ref="plan", parent_path=[]),
                evidence=[direct], role_status="unresolved", canonical_role="unknown", conflicting_evidence=[])
    obj = dict(handle="AA", project_id="P", parent_path=[], snapshot="plan-hash", drawing_instance_id="draw",
               block_name="block", geometry_types=[], role_evidence=role, candidate_types=[], legend_comparisons=[],
               block_definition_identity={"status":"unverified"}, provenance={"report_sha256":"plan-hash"})
    entry = dict(project_id="P", label="图例设备全称", names=["测试设备全称"], codes=["QQ"], kind="legend_row",
                 discipline="消防", membership="ambiguous", provenance={"snapshot_id":"source"}, usages=[],
                 symbol_block="other", row_id="row-1")
    return obj, symbol, [entry]


class RecoveryTests(unittest.TestCase):
    def test_literal_and_project_alias(self):
        r = recover(*fixture())
        self.assertEqual(r["candidate_status"], "explicit_name_candidate")
        self.assertEqual(r["raw_device_names"], ["测试设备全称"])
        self.assertEqual(r["project_legend_evidence"][0]["label"], "图例设备全称")

    def test_no_geometry_needed_for_name(self):
        self.assertEqual(recover(*fixture())["geometry_status"]["definition"], {"status":"unverified"})

    def test_direct_name_with_no_legend_or_geometry(self):
        o,s,_=fixture("感温探测器")
        result=recover(o,s,[])
        self.assertEqual(result["role_candidates"],["heat_detector"])
        self.assertEqual(result["candidate_status"],"explicit_name_candidate")
        self.assertFalse(result["project_legend_evidence"])

    def test_raw_category_remains_unresolved_even_when_repeated(self):
        o,s,e=fixture("箱柜")
        e[0]["names"]=["箱柜"]
        self.assertEqual(recover(o,s,e)["candidate_status"],"unresolved")

    def test_owner(self):
        obj,s,e = fixture()
        s["attributes"][0]["owner"] = "FF"
        with self.assertRaises(ValueError): recover(obj,s,e)

    def test_missing_native_attrib(self):
        obj,s,e = fixture()
        s["attributes"].clear()
        with self.assertRaises(ValueError): recover(obj,s,e)

    def test_other_project(self):
        o,s,e=fixture("QQ")
        e[0]["project_id"]="other"
        with self.assertRaises(ValueError): recover(o,s,e)

    def test_same_code_independent_project_meanings(self):
        o,s,e=fixture("QQ")
        e[0]["names"]=["QQ"]
        first=recover(o,s,e)["role_candidates"]
        o["project_id"]=s["identity"]["project_id"]=o["role_evidence"]["evidence_identity"]["project_id"]="Q"
        e[0].update(project_id="Q",label="另一项目图例")
        self.assertEqual(first,["图例设备全称"])
        self.assertEqual(recover(o,s,e)["role_candidates"],["另一项目图例"])

    def test_priority_and_original_result(self):
        o,s,e=fixture()
        o["role_evidence"]["overridden_defaults"]=[{"raw_value":"其他名称"}]
        before=copy.deepcopy(o)
        r=recover(o,s,e)
        self.assertEqual(before,o)
        self.assertEqual(r["original_device_role_result"],before["role_evidence"])
        self.assertNotIn("其他名称",r["role_candidates"])

    def test_missing_empty_generic_and_unknown(self):
        for raw in ("", "箱柜", "任意未知字段", "O/I"):
            with self.subTest(raw=raw): self.assertEqual(recover(*fixture(raw))["candidate_status"],"unresolved")

    def test_unknown_tag(self):
        o,s,e=fixture()
        s["attributes"][0]["tag"]=o["role_evidence"]["evidence"][0]["attribute_tag"]="REMARK"
        self.assertFalse(recover(o,s,e)["role_candidates"])

    def test_ambiguous_row_conditional(self):
        o,s,e=fixture("QQ")
        e[0]["names"]=["QQ"]
        r=recover(o,s,e)
        self.assertEqual(r["candidate_status"],"conditional_legend_candidate")
        self.assertEqual(r["project_legend_evidence"][0]["membership"],"ambiguous")

    def test_code_requires_row(self):
        o,s,e=fixture("QQ")
        e[0]["kind"]="name_witness"
        self.assertFalse(recover(o,s,e)["role_candidates"])

    def test_multiple_code_interpretations(self):
        o,s,e=fixture("QQ")
        e.append(dict(e[0],label="另一解释",row_id="row-2"))
        self.assertEqual(recover(o,s,e)["candidate_status"],"competing_interpretations")
        self.assertEqual(recover(o,s,e),recover(o,s,list(reversed(e))))

    def test_geometry_disagreement(self):
        o,s,e=fixture()
        o["geometry_types"]=o["candidate_types"]=["独立图形候选"]
        self.assertEqual(recover(o,s,e)["candidate_status"],"conflicting_evidence")

    def test_scoped_discipline(self):
        o,s,e=fixture()
        e[0]["discipline"]="强电"
        self.assertEqual(recover(o,s,e)["discipline_candidates"],["强电"])

    def test_official_result(self):
        o,s,e=fixture("感烟探测器")
        o["candidate_types"]=["smoke_detector"]
        o["role_evidence"].update(canonical_role="smoke_detector",role_status="supported")
        self.assertEqual(recover(o,s,e)["original_device_role_result"],o["role_evidence"])

    def test_explicit_reading_precedes_compatible_polysemous_display(self):
        o,s,e=fixture("感烟探测器")
        o["role_evidence"].update(canonical_role="smoke_detector",role_status="supported")
        o["candidate_types"]=["smoke_detector"]
        e[0].update(label="感烟探测器",names=["感烟探测器"])
        e.append(dict(e[0],label="其他解释",names=[],row_id="row-2"))
        s["attributes"].append(dict(handle="AD",owner="AA",tag="$TEXT$",value="QQ"))
        o["role_evidence"]["evidence"].append(dict(o["role_evidence"]["evidence"][0],
            source_handle="AD",attribute_tag="$TEXT$",raw_value="QQ"))
        result=recover(o,s,e)
        self.assertEqual(result["role_candidates"],["smoke_detector"])
        self.assertIn("其他解释",result["code_interpretations"])

    def test_unrelated_positive_geometry_is_not_an_alias(self):
        o,s,e=fixture()
        o["candidate_types"]=o["geometry_types"]=["独立图形"]
        e[0]["names"].append("独立图形")
        self.assertEqual(recover(o,s,e)["candidate_status"],"conflicting_evidence")

    def test_geometry_contradicts_the_selected_legend_symbol(self):
        o,s,e=fixture()
        o["legend_comparisons"]=[dict(legend_row_identity="row-1",match_status="conflicting",
            geometry_comparison_status="different",legend_symbol_identity={"handle":"FE","snapshot_id":"source"})]
        e[0]["provenance"]["handle"]="FE"
        self.assertEqual(recover(o,s,e)["candidate_status"],"conflicting_evidence")
        o["legend_comparisons"][0]["legend_symbol_identity"]["handle"]="FA"
        self.assertEqual(recover(o,s,e)["candidate_status"],"explicit_name_candidate")

    def test_no_quantity_or_propagation(self):
        r=recover(*fixture())
        self.assertEqual(r["engineering_approval_status"],"not_approved")
        self.assertIsNone(r["approved_device_quantity"])
        self.assertEqual(r["propagated_properties"],[])

    def test_colocated_identities(self):
        o,s,e=fixture()
        r=recover(o,s,e)
        o["handle"]=s["identity"]["handle"]=s["attributes"][0]["owner"]=o["role_evidence"]["device_handle"]="AC"
        o["role_evidence"]["evidence"][0]["source_definition_path"]=["AC"]
        self.assertNotEqual(r["stable_instance_identity"],recover(o,s,e)["stable_instance_identity"])
