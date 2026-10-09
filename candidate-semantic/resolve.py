"""CLI consuming structured upstream evidence, not raw CAD reports."""
import argparse
import hashlib
import json
from pathlib import Path
from rules import load_rules
from resolver import resolve_candidate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--rules', required=True, help='Machine-readable project binding JSON')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if Path(args.output).exists() or Path(args.output).is_symlink():
        raise FileExistsError('Output already exists; evidence is append-only')
    source = Path(args.input)
    item = json.loads(source.read_text(encoding='utf-8-sig'))
    item.setdefault('provenance', []).append({'path': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()})
    result = resolve_candidate(item, load_rules(args.rules))
    with Path(args.output).open('x',encoding='utf-8') as output:
        json.dump(result,output,ensure_ascii=False,indent=2)

if __name__ == '__main__': main()
