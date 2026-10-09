"""Versioned engineering-length conversions; CAD scaling is a separate contract."""
from decimal import Decimal
import hashlib
import json

VERSION='engineering-length-units/1'
FACTORS={('mm','m'):Decimal('0.001'),('m','mm'):Decimal('1000'),
         ('m','m'):Decimal('1'),('mm','mm'):Decimal('1')}


def conversion_contract(conversion,binding):
    source,target=conversion.get('from_unit'),conversion.get('to_unit')
    supplied=Decimal(str(conversion.get('factor')))
    kind=conversion.get('conversion_kind','engineering_units')
    if kind=='engineering_units':
        expected=FACTORS.get((source,target))
        if expected is None or supplied!=expected:
            raise ValueError('Unsupported physical units or incorrect physical conversion factor')
        return {'contract_id':VERSION,'version':'1','kind':kind,'source_unit':source,
                'target_unit':target,'factor':str(expected)}
    if kind!='cad_geometry_scale':raise ValueError('Unknown conversion kind')
    c=conversion.get('reviewed_scale_contract')
    if not isinstance(c,dict):raise ValueError('CAD scaling requires an independent reviewed contract')
    digest=hashlib.sha256(json.dumps({k:v for k,v in c.items() if k!='content_hash'},
        sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    if (c.get('content_hash')!=digest or c.get('status')!='approved' or not c.get('contract_id') or
        not c.get('version') or not c.get('provenance') or c.get('binding')!=binding or
        c.get('kind')!='cad_geometry_scale' or c.get('source_unit')!=source or c.get('target_unit')!=target or
        Decimal(str(c.get('factor')))!=supplied or not supplied.is_finite() or supplied<=0):
        raise ValueError('CAD scale contract approval/binding mismatch')
    return c
