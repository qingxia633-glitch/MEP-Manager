import argparse,json
from pathlib import Path
from registry import build_registry

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input-map',required=True);p.add_argument('--output',required=True)
 a=p.parse_args();m=json.loads(Path(a.input_map).read_text(encoding='utf-8-sig'))
 result=build_registry(m['project_id'],m['inputs'])
 with Path(a.output).open('x',encoding='utf-8',newline='\n') as f:
  json.dump(result,f,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
