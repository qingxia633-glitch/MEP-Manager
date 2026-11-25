"""Static acquisition safety checks, not a substitute for AutoCAD execution."""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]

class SourceTests(unittest.TestCase):
    def test_balanced_lisp(self):
        for path in (ROOT/'TargetedNativeProbe.lsp',ROOT/'tests/HostTests.lsp'):
            depth=0; quoted=False; escape=False; comment=False
            for c in path.read_text(encoding='utf-8'):
                if comment:
                    if c=='\n':comment=False
                elif quoted:
                    if escape:escape=False
                    elif c=='\\':escape=True
                    elif c=='"':quoted=False
                elif c==';':comment=True
                elif c=='"':quoted=True
                elif c=='(':depth+=1
                elif c==')':
                    depth-=1
                    self.assertGreaterEqual(depth,0)
            self.assertEqual(depth,0)
            self.assertFalse(quoted)

    def test_no_mutation_entrypoints(self):
        source=(ROOT/'TargetedNativeProbe.lsp').read_text().lower()
        self.assertIsNone(re.search(r'\(\s*(?:command|command-s|vl-cmdf|entmod|entmake|entmakex|entdel|setvar|vla-save|vla-saveas|vla-put-[\w-]+)\b',source))

    def test_generic_tool_has_no_seed_constants(self):
        source=(ROOT/'TargetedNativeProbe.lsp').read_text()
        # The encoder's digit alphabet and the trace file's append mode
        # are non-handle literals. Scope each exception to its call site.
        source=source.replace('(substr "0123456789abcdef"', '(substr alphabet')
        source=source.replace('(open tnp:trace-path "a" "utf8-bom")', '(open trace append-mode encoding)')
        # Handles are strings. Also catch embedded mixed-hex identifiers in
        # comments, symbols and longer strings (case insensitive).
        fixed_seed=re.compile(r'"[0-9a-f]+"|(?=[0-9a-f]*[0-9])(?=[0-9a-f]*[a-f])[0-9a-f]{5,}', re.I)
        for example in ('(handent "B17E5")', 'targets=f029b', '(list "76543")'):
            self.assertRegex(example, fixed_seed)
        self.assertNotRegex(source, fixed_seed)

if __name__=='__main__':unittest.main()
