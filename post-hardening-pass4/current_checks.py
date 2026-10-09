"""Old assertions, new explicitly synthetic/source-backed fixture factories only."""
import copy
import json
import sys
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
from synthetic_contract import previous,plan,item,assumption,parameter_plan

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/post-hardening-pass4-20261009'
load=previous.load
def project_plan(kind='conduit'):
    return json.loads((OUT/('golden-'+kind+'-profile1.json')).read_text(encoding='utf-8'))['fixture']
def current_loader(folder,filename='resolver.py'):
    return load(folder,'plan_v03.py' if folder=='quantity-eligibility' and filename=='plan_v02.py' else filename)
class Current(unittest.TestCase):pass
def attach(label,cls,module,replacements):
    for name in unittest.defaultTestLoader.getTestCaseNames(cls):
        def test(self,name=name,cls=cls,module=module,replacements=replacements):
            with ExitStack() as stack:
                for key,value in replacements.items():
                    if key=='load' and name=='test_G2_no_correction':value=load
                    if hasattr(module,key):stack.enter_context(patch.object(module,key,value))
                if cls is previous.Admission:stack.enter_context(patch.object(cls,'assumed_plan',staticmethod(lambda:assumption(plan()))))
                case=cls(name);case.setUp()
                try:getattr(case,name)()
                finally:case.tearDown()
        setattr(Current,'test_'+label+'_'+name,test)

attach('Pass3',previous.Admission,previous,dict(complete_plan=plan,item=item))
pass2=load('post-hardening-pass2/tests','test_pass2.py')
attach('Pass2',pass2.Pass2,pass2,dict(plan=plan,item=item,load=current_loader))
builder=load('design-net-quantity/tests','test_builder.py')
attach('Builder',builder.BuilderTests,builder,dict(plan=project_plan,synthetic=parameter_plan))
for file in sorted((ROOT/'safety-hardening').glob('test_*.py')):
    module=load('safety-hardening',file.name)
    for cls in list(vars(module).values()):
        if isinstance(cls,type) and issubclass(cls,unittest.TestCase) and cls.__module__==module.__name__:
            attach(file.stem,cls,module,dict(plan=parameter_plan,item=item,load=current_loader,policy=lambda:plan()['reporting_policy']))
migration=load('contract-migration/tests','test_migration.py')
for cls in (migration.SourceBackedSafety,migration.SourceBackedBuilder,migration.SourceBackedGate,migration.SourceBackedEligibility):
    cls.setUpClass()
    attach(cls.__name__,cls,migration,dict(plan=project_plan))

if __name__=='__main__':
    sys.path.insert(0,str(ROOT/'post-hardening-pass3'));from legacy_audit import Observed
    result=unittest.TextTestRunner(verbosity=2,resultclass=Observed).run(unittest.defaultTestLoader.loadTestsFromTestCase(Current))
    with (OUT/sys.argv[1]).open('x',encoding='utf-8') as f:json.dump(dict(testsRun=result.testsRun,failures=len(result.failures),errors=len(result.errors),cases=result.cases),f,ensure_ascii=False,indent=2)
    sys.exit(0 if result.wasSuccessful() else 1)
