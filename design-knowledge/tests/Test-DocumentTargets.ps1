$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../DocumentTargetResolver.psm1') -Force
$root=Join-Path $PSScriptRoot '../..'
$inputRun=Get-Content (Join-Path $root 'local_test_data/system-scope-propagation-validated-20260925/EW-0004.json') -Raw -Encoding UTF8|ConvertFrom-Json
$inventory=Get-Content (Join-Path $root 'reference/electrical-document-inventory-20260925.json') -Raw -Encoding UTF8|ConvertFrom-Json
$script:n=0
function Check($ok,$why){if(!$ok){throw $why};$script:n++}
$before=$inputRun.requirements|ConvertTo-Json -Depth 80 -Compress
$r=Resolve-DocumentTargets $inputRun.requirements $inputRun.consumption.searchScopes $inventory
Check ($r.targets.Count -eq 132) '44 documents evaluated for each separate requirement'
Check (($inputRun.requirements|ConvertTo-Json -Depth 80 -Compress) -ceq $before) 'Requirement unchanged'
foreach($q in $inputRun.requirements){
 $top=@($r.targets|Where-Object {$_.requirementRef -eq $q.requirementId -and $_.rank -eq 1})
 Check ($top.Count -eq 2 -and @($top|Where-Object {$_.candidateDocument.fileName -notmatch '弱电消防系统图'}).Count -eq 0) 'System drawing pair emerges without prescribed choice'
 Check (@($top|Where-Object targetStatus -EQ preferred_candidate).Count -eq 0) 'Unresolved versions do not get unique preference'
 Check (@($r.reviewItems|Where-Object {$_.requirementRef -eq $q.requirementId -and $_.type -eq 'version_relationship_unresolved'}).Count -gt 0) 'Version review retained'
 foreach($pattern in @('火灾报警平面图','消防干线平面图','弱电平面图')){Check (@($r.targets|Where-Object {$_.requirementRef -eq $q.requirementId -and $_.candidateDocument.fileName -match $pattern -and $_.targetStatus -in @('possible_candidate','supported_candidate')}).Count -eq 2) 'Reasonable alternatives retained'}
}
foreach($t in $r.targets){
 Check ($t.documentTypeStatus -eq 'candidate' -and !$t.contentVerified) 'Filename never establishes contents'
 Check ($t.evidenceRefs.Count -gt 0 -and $t.provenance.searchScopes[0].provenance.sourceTextSpans.Count -gt 0) 'Trace reaches raw spans'
 Check (!$t.automaticOpen -and !$t.resolvesRequirement) 'No opening or requirement satisfaction'
}
Check (!$r.requirementUpdates.Count -and !$r.networkEdges.Count) 'No downstream mutations'
$notes=@($r.targets|Where-Object {$_.candidateDocument.fileName -match '说明及配电箱'})
Check (@($notes|Where-Object {$_.rank -eq 1 -or $_.targetStatus -in @('preferred_candidate','supported_candidate')}).Count -eq 0) 'Design statements not a high priority substitute for installation evidence'
foreach($case in @(@('电气设计说明','design_notes'),@('消防图例','legend'),@('消防系统图','system_diagram'),@('消防平面图','plan'),@('消防干线平面图','riser/mainline_plan'),@('设备大样','detail'),@('设备表','schedule'),@('ABC','unknown'))){Check ((Get-DocumentTypeCandidates ($case[0]+'.dwg')).primary -eq $case[1]) 'Document type vocabulary'}
$reversed=$inventory|ConvertTo-Json -Depth 30|ConvertFrom-Json
$reversed.documents=@($reversed.documents|Sort-Object documentId -Descending)
$r2=Resolve-DocumentTargets $inputRun.requirements $inputRun.consumption.searchScopes $reversed
foreach($t in $r.targets){$same=@($r2.targets|Where-Object targetId -EQ $t.targetId)[0];Check ($same.rank -eq $t.rank -and $same.score -eq $t.score) 'Inventory order does not choose a version'}
$changed=$inventory|ConvertTo-Json -Depth 30|ConvertFrom-Json
foreach($d in $changed.documents){$d.sizeBytes=1;$d.lastWriteTimeUtc='2099-01-01T00:00:00Z';$d.fileName=$d.fileName -replace '_t8_t3','_t99_t1' -replace '_t8','_t1'}
$r3=Resolve-DocumentTargets $inputRun.requirements $inputRun.consumption.searchScopes $changed
foreach($t in $r.targets){$same=@($r3.targets|Where-Object targetId -EQ $t.targetId)[0];Check ($same.rank -eq $t.rank -and $same.score -eq $t.score) 'Suffix numbers size and dates do not imply priority'}
$badScopes=$inputRun.consumption.searchScopes|ConvertTo-Json -Depth 50|ConvertFrom-Json
foreach($s in $badScopes){$s.systemIdentity='unknown'}
Check (@((Resolve-DocumentTargets $inputRun.requirements $badScopes $inventory).targets|Where-Object {$null -ne $_.rank}).Count -eq 0) 'Unknown scope not wildcard'
foreach($s in $badScopes){$s.systemIdentity='monitoring_security'}
Check (@((Resolve-DocumentTargets $inputRun.requirements $badScopes $inventory).targets|Where-Object {$null -ne $_.rank}).Count -eq 0) 'Other system search cannot feed fire tasks'
$foreign=$inventory|ConvertTo-Json -Depth 30|ConvertFrom-Json;$foreign.projectId='other-project'
Check (@((Resolve-DocumentTargets $inputRun.requirements $inputRun.consumption.searchScopes $foreign).targets|Where-Object {$null -ne $_.rank}).Count -eq 0) 'Foreign inventory rejected'
$untraceable=$inputRun.consumption.searchScopes|ConvertTo-Json -Depth 50|ConvertFrom-Json
foreach($s in $untraceable){$s.provenance.sourceTextSpans=@()}
Check (@((Resolve-DocumentTargets $inputRun.requirements $untraceable $inventory).targets|Where-Object {$null -ne $_.rank}).Count -eq 0) 'Missing raw trace blocked'
# Generic vocabulary counterexample: an unrelated path/name prefix and a precise telephone document.
$generic=$inventory|ConvertTo-Json -Depth 30|ConvertFrom-Json
$prototype=@($generic.documents|Where-Object {$_.fileName -match '弱电消防系统图'})[0]
$prototype.fileName='任意区域-火警电话系统图.dwg';$prototype.documentId='opaque-document';$prototype.fullPath='X:\registered\opaque.dwg'
$generic.documents=@($prototype)+@($generic.documents|Where-Object {$_.readEvidence.Count -gt 0})
$gr=Resolve-DocumentTargets $inputRun.requirements $inputRun.consumption.searchScopes $generic
$phone=@($gr.targets|Where-Object {$_.candidateDocument.documentId -eq 'opaque-document' -and $_.systemScopeCandidate.requestedSystemType -eq 'fire_phone'})[0]
$alarm=@($gr.targets|Where-Object {$_.candidateDocument.documentId -eq 'opaque-document' -and $_.systemScopeCandidate.requestedSystemType -eq 'fire_alarm'})[0]
Check ($phone.targetStatus -eq 'preferred_candidate' -and $phone.score -gt $alarm.score) 'Generic precise system term outranks adjacent topic without known filename'
Check ($alarm.targetStatus -eq 'possible_candidate') 'Other explicit system stays a weak multi-system document possibility'
# A future task can seek physical layout evidence instead of assuming system diagrams always win.
$physical=$inputRun.requirements|ConvertTo-Json -Depth 30|ConvertFrom-Json
foreach($q in $physical){$q.requiredFact='physical_routing'}
$pr=Resolve-DocumentTargets $physical $inputRun.consumption.searchScopes $inventory
Check (@($pr.targets|Where-Object {$_.rank -eq 1 -and $_.candidateDocumentType -in @('plan','riser/mainline_plan')}).Count -gt 0 -and @($pr.targets|Where-Object {$_.rank -eq 1 -and $_.candidateDocumentType -eq 'system_diagram'}).Count -eq 0) 'Evidence gap changes type priority rather than hardcoded system-first'
$security=$inputRun.requirements|ConvertTo-Json -Depth 50|ConvertFrom-Json
$securityScopes=$inputRun.consumption.searchScopes|ConvertTo-Json -Depth 50|ConvertFrom-Json
foreach($q in $security){$q.systemIdentity.systemType='monitoring_security'}
foreach($s in $securityScopes){$s.systemIdentity='monitoring_security'}
$sr=Resolve-DocumentTargets $security $securityScopes $inventory
Check (@($sr.targets|Where-Object {$_.candidateDocument.fileName -match '消防' -and $_.targetStatus -in @('preferred_candidate','supported_candidate')}).Count -eq 0) 'Broad fire filename not promoted for security system task'
$unknownTask=$inputRun.requirements|ConvertTo-Json -Depth 50|ConvertFrom-Json
foreach($q in $unknownTask){$q.requiredFact='unrecognized_fact'}
$ur=Resolve-DocumentTargets $unknownTask $inputRun.consumption.searchScopes $inventory
Check (@($ur.targets|Where-Object {$null -ne $_.rank}).Count -eq 0 -and @($ur.reviewItems|Where-Object type -EQ expected_evidence_type_uncertain).Count -eq 3) 'Unknown evidence need remains unresolved with review'
$unregistered=$inventory|ConvertTo-Json -Depth 30|ConvertFrom-Json
foreach($d in $unregistered.documents){$d.readEvidence=@()}
Check (@((Resolve-DocumentTargets $inputRun.requirements $inputRun.consumption.searchScopes $unregistered).targets|Where-Object {$null -ne $_.rank}).Count -eq 0) 'Missing source registration cannot infer building scope from filename alone'
Write-Host "PASS: $script:n document target checks"
