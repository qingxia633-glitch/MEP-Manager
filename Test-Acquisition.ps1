$ErrorActionPreference='Stop'
$s=Get-Content (Join-Path $PSScriptRoot 'Test-AutoCADEntities.lsp') -Raw -Encoding UTF8
$n=0
function Check($ok,$name) { if(!$ok){throw "FAIL: $name"}; $script:n++ }
Check ($s.Contains('(defun c:MEPFULLREAD')) 'new command exists'
Check ($s.Contains('(defun c:MEPENTITYREAD () (mep2:read nil))')) 'legacy mode retained'
Check ($s.Contains('(defun c:MEPFULLREAD () (mep2:read T))')) 'full mode explicit'
Check ($s.Contains('(or full (wcmatch')) 'all layers bypass professional filter'
$pattern=[regex]::Match($s,'wcmatch \(strcase layer\) "([^"]+)"').Groups[1].Value
Check ($pattern -eq '*EQUIP-*,*E-*,*EP-*,*CABLETRAY_*,*WIRE-*,*LWIRE,*TEL_TEXT,*TEL_SYMB') 'legacy filter unchanged'
foreach($layer in @('_D-SIG_TEXT','arbitrary notes','0','ARCH_TEXT')) {
 $candidate=@($pattern.Split(',')|Where-Object {$layer -like $_}).Count -gt 0
 Check (!$candidate) "fixture outside legacy filter: $layer"
 Check (($true -or $candidate)) "all-layer selection truth table: $layer"
}
Check (!$s.Contains('_D-SIG_TEXT')) 'no special layer hardcoded'
Check ($s.Contains('MEP-full-entity-report.txt') -and $s.Contains('MEP-entity-report.txt')) 'separate filenames'
Check ($s.Contains('(findfile outputPath)')) 'full snapshot overwrite guard'
Check (!$s.Contains('vl-filename-nondirectory')) 'standard filename functions only'
Check ($s.Contains('(vl-filename-base outputPath)') -and $s.Contains('(vl-filename-extension outputPath)')) 'base and extension validation'
Check ([regex]::Matches($s,'\(setq outputPath\b').Count -eq 1) 'chosen output path assigned exactly once'
Check ($s.Contains('(setq outputPath (getfiled')) 'dialog result preserved directly'
Check ($s.Contains('(open outputPath "w")')) 'open uses unchanged output path'
foreach($stage in @('getfiled','path-validation','filename-validation','existence-check','open-output','entity-acquisition','write-output','close-output')) { Check ($s.Contains('"'+$stage+'"')) "stage: $stage" }
foreach($label in @('OutputPath = ','OutputFileName = ','Exists = ','Existing snapshot protected:','Entity acquisition stopped at stage [')) { Check ($s.Contains($label)) "diagnostic: $label" }
Check ($s.Contains('UNPARSED_TYPE: identity and non-binary DXF fields only')) 'unsupported fallback preserved'
Check ($s.IndexOf('(mep2:val "EntityHandle"') -lt $s.IndexOf("(setq result (vl-catch-all-apply 'mep2:details")) 'identity before detail decoding'
foreach($field in @('ModelSpaceTopLevelAllLayers','AttachedATTRIB','BlockDefinitionRecursiveExpansion','NestedBlocks','XrefContents','PaperSpaceLayouts','ProxySemanticRecovery','TableSemanticExtraction','ExtractorVersion','AcquiredAtLocal','GlobalTypeCounts_DXF','ReadErrorCount')) { Check ($s.Contains($field)) "contract: $field" }
Check ($s.Contains('(410 . "Model")')) 'ModelSpace only'
Check ($s.Contains('(setq errors (1+ errors))')) 'read error accumulation retained'
# Structural check ignores strings and comments; not an AutoCAD runtime substitute.
foreach($field in @('EffectiveName_RAW','IsDynamicBlock','DynamicProperty_BEGIN','PropertyName','Value','AllowedValues','UnitsType','ReadOnly','Description','Show','DynamicMetadataStatus')) { Check ($s.Contains($field)) "dynamic metadata: $field" }
Check ($s.Contains('(if full (mep2:dynamic e))')) 'dynamic metadata restricted to full mode'
Check ($s.Contains("'vla-GetDynamicBlockProperties")) 'query dynamic properties'
Check (!$s.Contains('7EDD9') -and !$s.Contains('20A')) 'no dynamic sample answers'
Check ($s -notmatch 'vla-put-|vla-Explode|vla-ResetBlock|vla-TransformBy') 'no mutating ActiveX calls'
$clean=[regex]::Replace($s,'"(?:\\.|[^"\\])*"|;[^\r\n]*','')
$depth=0
foreach($c in $clean.ToCharArray()){if($c -eq '('){$depth++};if($c -eq ')'){$depth--;if($depth -lt 0){throw 'Unbalanced Lisp'}}}
Check ($depth -eq 0) 'balanced Lisp forms'
"PASS: $n acquisition contract checks (static; AutoCAD runtime acceptance pending)"
