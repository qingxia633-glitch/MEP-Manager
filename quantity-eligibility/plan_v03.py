"""Current executable export; historical v0.2 export remains a legacy format."""
from copy import deepcopy
from plan_v02 import export_plan as export_legacy, seal
from executable_contract import validate_executable_plan_contract


def export_plan(decision, source_hash, correction, policy):
    draft = decision.get('quantity_formula_plan')
    if not isinstance(draft, dict):
        raise ValueError('Executable plan draft missing')
    if decision.get('semantic_gate') != draft.get('semantic_gate'):
        raise ValueError('Decision and plan semantic Gate records disagree')
    plan = export_legacy(decision, source_hash, correction, policy)
    # No default approvals, conditions or source facts are added here.
    plan['schema_version'] = '0.3'
    plan['unit_conversion_contract'] = deepcopy(decision.get('unit_conversion_contract'))
    validate_executable_plan_contract(plan)
    return seal(plan)
