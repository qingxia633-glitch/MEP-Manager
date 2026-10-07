$ErrorActionPreference='Stop'
$n=0
function Check($ok,$message){if(!$ok){throw $message};$script:n++}
$code=Get-Content (Join-Path $PSScriptRoot 'BlockLocalGeometryProbe.lsp') -Raw
$base=Get-Content (Join-Path $PSScriptRoot 'BlockDefinitionProbe.lsp') -Raw
foreach($s in @($code,$base)){
 Check ($s -notmatch '(?i)\((entmod|entmake|entdel|command|command-s|setvar|vla-put-\S*|vla-explode|vla-resetblock|vla-save\S*)\b') 'getter-only CAD API contract'
 $clean=[regex]::Replace($s,'"(?:\\.|[^"\\])*"|;[^\r\n]*','');$depth=0
 foreach($ch in $clean.ToCharArray()){if($ch -eq '('){$depth++};if($ch -eq ')'){$depth--;Check ($depth -ge 0) 'Lisp prefix balanced'}}
 Check ($depth -eq 0) 'Lisp balanced'
}
Check ($code -notmatch 'JSK|836|K1-4|QWB|1\.5[kK]') 'no sample answers in generic probe'
Check ($code.Contains('(vlax-for obj block')) 'direct definition traversal'
Check ($code.Contains('(bp:entity (') -or $code.Contains("'bp:entity (list obj)")) 'reuse raw entity exporter'
foreach($key in @('SourceHandle','SourceBlock','AnchorHandle','AnchorPoint','WindowHalfSize','WindowSelectionBasis','window_scope_uncertain','unknown','ReadErrorCount','BoundsError','END_OF_REPORT')){Check ($code.Contains($key)) "retains $key"}
Check ($code.Contains('(vl-catch-all-error-p box) (blp:overlap')) 'unavailable bbox retained rather than excluded'
Check ($code.Contains("'trans (list input normal 0)")) 'nonidentity OCS normalization retained'
Check ($code.Contains('(equal handle (blp:normalize-handle (cdr (assoc 5 d))))')) 'anchor membership checked in requested block'
Check ($code.Contains('(findfile path)')) 'existing report protected'
Check ($code.Contains('BLOCK-LOCAL-GEOMETRY-PROBE.TXT')) 'separate fixed output name'
Check ($code -notmatch '(?i)nearest|circuit|quantity|usesConfiguration') 'no semantic binding or quantity generation'
foreach($type in @('LINE','LWPOLYLINE','CIRCLE','ARC','INSERT','TEXT','MTEXT','ATTDEF')){Check ($code.Contains('"'+$type+'"')) "raw supported type $type"}
Check ($base.Contains('(bp:raw "DXF:" d)')) 'raw geometry, transforms, text and visibility preserved'
# Real fixture: no coordinates or Handles are algorithm inputs baked into the LISP.
$report=Join-Path $PSScriptRoot '../local_test_data/plumbing-block-text-index-20260917/block-text-index.txt'
if(Test-Path $report){
 $s=[IO.File]::ReadAllText((Resolve-Path $report))
 Check ((Get-FileHash $report -Algorithm SHA256).Hash -eq '90954BB823B53B8CD338A4B016BD993D1C39E3875CD6B49A14DE341CB30C59D5') 'window evidence snapshot unchanged'
 $b=([regex]::Matches($s,'(?ms)^Block_BEGIN\r?\n.*?^Block_END')|Where-Object{$_.Value -match '(?m)^BlockName="PX-B-P01\(-1F\)-JSK"'}).Value
 $labels=@(foreach($m in [regex]::Matches($b,'(?ms)^Text_BEGIN\r?\n.*?^Text_END')){
  $v=$m.Value;$text=[regex]::Match($v,'Text_RAW="([^"]*)"').Groups[1].Value
  if($text -match '^K\d+-\d+$'){$p=[regex]::Match($v,'LocalPoint_DXF10=\(([^)]+)\)').Groups[1].Value -split ' ';[pscustomobject]@{Handle=[regex]::Match($v,'InternalHandle="([^"]*)"').Groups[1].Value;X=[double]$p[0];Y=[double]$p[1];Text=$text}}
 })
 $anchor=$labels|Where-Object Handle -eq '836'
 Check ($anchor.Text -eq 'K1-4') 'real anchor identity'
 $others=@($labels|Where-Object Handle -ne '836')
 $inside=@($others|Where-Object{[math]::Abs($_.X-$anchor.X) -le 3000 -and [math]::Abs($_.Y-$anchor.Y) -le 3000})
 Check ($inside.Count -eq 0) 'initial window excludes all other readable pit labels'
 $nearest=$others|Sort-Object { [math]::Pow($_.X-$anchor.X,2)+[math]::Pow($_.Y-$anchor.Y,2)}|Select-Object -First 1
 Check ($nearest.Handle -eq '696') 'window evidence nearest label remains K4-5'
}else{throw 'Real window evidence fixture missing'}
"PASS: $n static/source and real-window evidence checks. AutoCAD execution/bbox correctness NOT exercised."
