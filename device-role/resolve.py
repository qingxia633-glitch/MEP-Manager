"""Offline INSERT -> DeviceRoleEvidence command-line entrypoint."""
import argparse
import json
from pathlib import Path
from resolver import RoleContext,resolve_device_role

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--snapshot',required=True)
    p.add_argument('--probe',action='append',default=[])
    p.add_argument('--device',required=True)
    p.add_argument('--legend-evidence',help='Reviewed JSON list with explicit target-definition bindings')
    p.add_argument('--output',required=True)
    args=p.parse_args()
    legends=json.loads(Path(args.legend_evidence).read_text(encoding='utf-8-sig')) if args.legend_evidence else []
    context=RoleContext.from_reports(args.snapshot,args.probe,legends)
    if args.legend_evidence:
        import hashlib
        context.provenance.append(dict(path=args.legend_evidence,sha256=hashlib.sha256(Path(args.legend_evidence).read_bytes()).hexdigest()))
    result=resolve_device_role(args.device,context)
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
