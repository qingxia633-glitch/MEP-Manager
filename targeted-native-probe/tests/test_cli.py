import hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from test_probe import fixture,ROOT

class CliTests(unittest.TestCase):
    def test_actual_bytes_unicode_manifest_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);dwg=p/'测试.dwg';dwg.write_bytes(b'synthetic bytes, not CAD evidence')
            q,r=fixture();q['project_id']='软件测试';q['drawing_path']=str(dwg)
            q['dwg_sha256_before']=hashlib.sha256(dwg.read_bytes()).hexdigest()
            r[0].update(project_id=q['project_id'],drawing_path=str(dwg))
            request=p/'request.json';request.write_text(json.dumps(q,ensure_ascii=False),encoding='utf-8')
            report=p/'report.jsonl';report.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in r),encoding='utf-8-sig')
            before=report.read_bytes();out=p/'verified'
            cmd=[sys.executable,'-B',str(ROOT/'verify.py'),'--report',str(report),'--request',str(request),'--output',str(out)]
            first=subprocess.run(cmd,capture_output=True)
            self.assertEqual(first.returncode,0,first.stderr)
            manifest=json.loads((out/'manifest-v2.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['report_sha256'],hashlib.sha256(before).hexdigest())
            self.assertEqual(manifest['report_bytes'],len(before))
            saved=(out/'native-evidence.json').read_bytes()
            self.assertNotEqual(subprocess.run(cmd,capture_output=True).returncode,0)
            self.assertEqual((out/'native-evidence.json').read_bytes(),saved)
            self.assertEqual(report.read_bytes(),before)
            dwg.write_bytes(b'changed')
            cmd[-1]=str(p/'rejected')
            self.assertNotEqual(subprocess.run(cmd,capture_output=True).returncode,0)
            self.assertFalse((p/'rejected').exists())

if __name__=='__main__':unittest.main()
