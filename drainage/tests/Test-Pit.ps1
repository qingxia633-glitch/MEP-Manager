$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../DrainagePit.psm1') -Force
$f=Get-Content (Join-Path $PSScriptRoot 'k1-4-fixture.json') -Raw -Encoding UTF8|ConvertFrom-Json
$m=Read-PitCandidate $f
$n=0
function Check($v,$why){if(!$v){throw $why};$script:n++}
Check ($m.pumpSymbolCandidates.Count -eq 2) 'two independent symbols'
Check ($m.pumpSymbolCandidates[0].id -ne $m.pumpSymbolCandidates[1].id) 'independent identities'
Check (($m.pumpSymbolCandidates[0].members.handle -join ',') -eq '685,688,689,68B,68A') 'first complete group'
Check (($m.pumpSymbolCandidates[1].members.handle -join ',') -eq '68C,68D,68E,690,68F') 'second complete group'
Check ($m.pitOutlineCandidate.members.Count -eq 4) 'outer members'
Check ($m.innerOutlineCandidate.members[0].handle -eq '67F') 'inner member'
Check ($m.placementStatus -eq 'unresolved' -and $m.InstanceWCS -eq 'not_computed') 'no instance WCS'
Check (!(Test-PitCrossDocumentEligibility $m)) 'cross document coordinates blocked'
Check ($m.placementHypotheses.Count -eq 3) 'all paths preserved'
Check ($m.placementHypotheses[2].nestedReferences[0].transformStatus -eq 'incomplete_rotation_scale_normal_not_exported') 'nested transform not invented'
Check ($m.exceptions.unknownWindowRecords[0].handle -eq '830') 'earlier bbox exception retained'
Check ($m.pitOutlineCandidate.members[0].geometryPoints[0].Count -eq 3) 'numeric local XYZ preserved'
foreach($p in $m.placementHypotheses){
 Check ($p.InstanceWCS -eq 'not_computed' -and $p.selectionStatus -eq 'unresolved') 'no path auto-selected'
 Check ($p.topInsert.indexVisibilityEvidence.DXF60_RAW -eq 'nil' -and $p.topInsert.visibilityStatus -eq 'evaluated_visibility_unknown') 'raw visibility separated from evaluated visibility'
}
Check ($m.categoryRelationCandidate.status -eq 'partially_compatible') 'category relation only'
foreach($a in $m.categoryAttributeCandidates){Check ($a.status -eq 'candidate' -and $a.scope -eq 'category_only') 'no inherited instance attribute'}
foreach($r in @($m.pitOutlineCandidate.members)+@($m.pumpSymbolCandidates|ForEach-Object {$_.members})){
 Check ($r.sourceSnapshot.sha256.Length -eq 64 -and $r.rawRecord -and $r.layer -and $r.sourceInstancePath.Count -eq 3) 'provenance'
 Check ($r.coordinateFrame -eq 'DefinitionLocal') 'local coordinate frame'
}
$json=$m|ConvertTo-Json -Depth 80
Check ($json -notmatch '"(Circuit|circuits|connections|quantities|confirmedAttributes)"\s*:') 'no engineering outputs'
Check (($json|ConvertFrom-Json).pumpSymbolCandidates.Count -eq 2) 'JSON roundtrip'
$g=$f|ConvertTo-Json -Depth 30|ConvertFrom-Json;$g.identifier='wrong';$caught=$false
try{Read-PitCandidate $g|Out-Null}catch{$caught=$true};Check $caught 'mismatched reviewed identity rejected'
$g=$f|ConvertTo-Json -Depth 30|ConvertFrom-Json;$g.sources.probe.sha256='wrong';$caught=$false
try{Read-PitCandidate $g|Out-Null}catch{$caught=$true};Check $caught 'snapshot drift rejected'
"PASS: $n drainage candidate checks"
