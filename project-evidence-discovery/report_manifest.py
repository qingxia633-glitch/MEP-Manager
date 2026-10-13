"""Post-write report metadata. Never edits the source report or overwrites output."""
import argparse
import hashlib
import json
import codecs
import re
from pathlib import Path

HASH_SCOPE = 'exact completed report bytes'  # Manifest v2 sole supported scope.

def report_identity(raw):
    header=raw.split('EntityHandle=',1)[0]
    def value(key):
        match=re.search(r'^'+re.escape(key)+r'=(.*?)\r?$',header,re.M)
        return match[1].strip().strip('"') if match else None
    return {'drawing':value('DWG'),'extractor_version':value('ExtractorVersion'),
            'acquisition_mode':value('AcquisitionMode'),'model_space_top_level':value('ModelSpaceTopLevel'),
            'nested_blocks':value('NestedBlocks'),
            'leader_evidence_versions':sorted(set(re.findall(r'^LeaderEvidenceVersion="([^"\r\n]+)"\r?$',raw,re.M)))}

def verify_manifest(data, report, encoding, manifest):
    if not isinstance(manifest,dict):
        manifest=json.loads(Path(manifest).read_text(encoding='utf-8-sig'))
    raw=data.decode(encoding)
    expected={'report_file':Path(report).name,'report_sha256':hashlib.sha256(data).hexdigest(),
              'report_bytes':len(data),'report_identity':report_identity(raw)}
    for field,value in expected.items():
        if manifest.get(field)!=value:raise ValueError('manifest mismatch: '+field)
    try:encoding_equal=codecs.lookup(manifest.get('encoding','')).name==codecs.lookup(encoding).name
    except (LookupError,TypeError):encoding_equal=False
    if not encoding_equal:raise ValueError('manifest mismatch: encoding')
    if manifest.get('manifest_version')!='2':raise ValueError('manifest unsupported version: identity contract required')
    if manifest.get('hash_scope')!=HASH_SCOPE:raise ValueError('manifest mismatch: hash_scope')
    return expected

def write_manifest(report, output, encoding='utf-8-sig'):
    report=Path(report)
    data=report.read_bytes()
    raw=data.decode(encoding)  # No silent replacement or encoding guessing.
    result={'manifest_version':'2','report_file':report.name,
            'report_sha256':hashlib.sha256(data).hexdigest(),
            'report_bytes':len(data),'encoding':encoding,
            'hash_scope':HASH_SCOPE,'report_identity':report_identity(raw)}
    with Path(output).open('x',encoding='utf-8') as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2)
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('report');parser.add_argument('output')
    parser.add_argument('--encoding',default='utf-8-sig')
    args=parser.parse_args()
    write_manifest(args.report,args.output,args.encoding)
