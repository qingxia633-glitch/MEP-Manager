$ErrorActionPreference='Stop'
$code=Get-Content (Join-Path $PSScriptRoot 'BlockDefinitionProbe.lsp') -Raw
$n=0
function Check($ok,$message){if(!$ok){throw $message};$script:n++}
Check ($code.Contains('(defun c:MEPONELEVELBLOCKPROBE')) 'generic command exists'
Check ($code.Contains('(getstring T "\nBlockDefinition: ")')) 'arbitrary block name input'
foreach($field in @('SourceDefinitionPath','SourceInternalHandle','ParentReferenceDXF:','DefinitionPathStatus','BoundsStatus','BoundsError','BoundsFrame','SemanticStatus','Closed_RAW')){Check ($code.Contains($field)) "preserves $field"}
Check ($code.Contains('(not (equal actualName requestedName))')) 'parent reference target verified'
Check ($code.Contains("'vla-get-Handle (list record)")) 'parent owner verified against block record'
Check ($code -notmatch '(?i)\((entmod|entmake|entdel|command|vla-put-\S*|vla-explode|vla-resetblock)\b') 'no CAD writes'
Check ($code.Contains('(bp:entity obj)')) 'reuse raw reader without deduplication'
Check ($code.Contains('definition path only; ModelSpace instance unresolved')) 'not a ModelSpace instance'
Check ($code.Contains('unknown; raw identity retained')) 'unsupported semantic status'
Check ($code.Contains('Nested INSERT references are recorded, not expanded')) 'nonrecursive contract'
$clean=[regex]::Replace($code,'"(?:\\.|[^"\\])*"|;[^\r\n]*','');$depth=0
foreach($c in $clean.ToCharArray()){if($c -eq '('){$depth++};if($c -eq ')'){$depth--;if($depth -lt 0){throw 'unbalanced prefix'}}}
Check ($depth -eq 0) 'balanced Lisp'
"PASS: $n one-level static contract checks; AutoCAD runtime not exercised"
