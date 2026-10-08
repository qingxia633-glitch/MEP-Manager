"""Preserve raw historical unittest outcomes; classification is a separate artifact."""
import json,sys,unittest
from pathlib import Path

class Recorded(unittest.TextTestResult):
    def __init__(self,*a,**kw):super().__init__(*a,**kw);self.cases=[]
    def addSuccess(self,test):
        super().addSuccess(test);self.cases.append({'test_id':test.id(),'raw_status':'passed'})
    def addFailure(self,test,err):
        super().addFailure(test,err);self.cases.append({'test_id':test.id(),'raw_status':'failure','traceback':self._exc_info_to_string(err,test)})
    def addError(self,test,err):
        super().addError(test,err);self.cases.append({'test_id':test.id(),'raw_status':'error','traceback':self._exc_info_to_string(err,test)})
    def addSkip(self,test,reason):
        super().addSkip(test,reason);self.cases.append({'test_id':test.id(),'raw_status':'skipped','reason':reason})

if __name__=='__main__':
    suite=unittest.defaultTestLoader.discover(sys.argv[1])
    result=unittest.TextTestRunner(verbosity=2,resultclass=Recorded).run(suite)
    with Path(sys.argv[2]).open('x',encoding='utf-8') as f:
        json.dump(dict(testsRun=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),cases=result.cases),f,ensure_ascii=False,indent=2)
    sys.exit(0 if result.wasSuccessful() else 1)
