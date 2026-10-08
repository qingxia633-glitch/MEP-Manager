"""Offline INSERT -> DeviceRoleEvidence command-line entrypoint."""
import argparse
import json
from pathlib import Path
from resolver import RoleContext,resolve_device_role

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--snapshot',required=True)
    p.add_argument('--project-id',help='Explicit project identity for downstream evidence composition')
    p.add_argument('--probe',action='append',default=[])
    p.add_argument('--device',required=True)
    p.add_argument('--legend-evidence',help='Reviewed JSON list with explicit target-definition bindings')
    p.add_argument('--legend-policy',help='Versioned approved source policy with content hash')
    p.add_argument('--output',required=True)
    args=p.parse_args()
    if Path(args.output).exists() or Path(args.output).is_symlink():
        raise FileExistsError('Output already exists; evidence is append-only')
    legends=json.loads(Path(args.legend_evidence).read_text(encoding='utf-8-sig')) if args.legend_evidence else []
    context=RoleContext.from_reports(args.snapshot,args.probe,legends)
    context.project_id=args.project_id
    if args.legend_policy:
        context.legend_policy=json.loads(Path(args.legend_policy).read_text(encoding='utf-8-sig'))
    if args.legend_evidence:
        import hashlib
        context.provenance.append(dict(path=args.legend_evidence,sha256=hashlib.sha256(Path(args.legend_evidence).read_bytes()).hexdigest()))
    result=resolve_device_role(args.device,context)
    with Path(args.output).open('x',encoding='utf-8') as output:
        json.dump(result,output,ensure_ascii=False,indent=2)

if __name__=='__main__':main()
