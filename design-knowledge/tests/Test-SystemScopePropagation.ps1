$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../SystemScopePropagation.psm1') -Force
Import-Module (Join-Path $PSScriptRoot '../EvidenceAdmission.psm1') -Force
Import-Module (Join-Path $PSScriptRoot '../EvidenceInvestigationAdapter.psm1') -Force
$root=Join-Path $PSScriptRoot '../../local_test_data'
$s=Get-Content "$root/ew0004-design-statements-20260925.json" -Raw|ConvertFrom-Json
$h=Get-Content "$root/ew0004-hierarchy-bridge-20260925.json" -Raw|ConvertFrom-Json
$before=$s|ConvertTo-Json -Depth 80 -Compress
$script:n=0
function Check($ok,$why){if(!$ok){throw $why};$script:n++}
$r=Add-DesignSystemScopes $s $h 'local-project'
Check (($s|ConvertTo-Json -Depth 80 -Compress) -ceq $before) 'No upstream mutation'
Check ($r.designStatements.Count -eq 160) 'Statements preserved'
foreach($pair in @(@('233CA','fire_phone'),@('234DB','fire_alarm'),@('233C7','fire_broadcast'))){
 $found=@($r.designStatements|Where-Object {$_.sourceEntityHandles -contains $pair[0]})
 Check (@($found|ForEach-Object systemScopeCandidates|Where-Object canonicalSystemTypeCandidate -EQ $pair[1]).Count -gt 0) 'Real system propagated without handle rules'
}
foreach($st in $r.designStatements){Check ($st.statementType -eq @($s.designStatements|Where-Object statementId -EQ $st.statementId)[0].statementType) 'Statement types unchanged'}
$e=ConvertTo-DesignEvidenceAdmission $r
$all=@($e.statementEvidence)+@($e.referenceEvidence)
Check ($all.Count -eq 164) 'Evidence preserved'
Check (@($all|Where-Object {$_.systemIdentity -ne 'unknown'}).Count -gt 0) 'Known candidate categories reach evidence'
foreach($x in $all){Check (!(Test-DesignEvidenceUse $x 'assign_instance_attribute' -SystemIdentity $x.systemIdentity)) 'No instance use'}
Check (@(Find-SystemAlias '消防 非消防 普通照明 配电保护').Count -eq 0) 'Generic fire mention is not alarm system'
Check (@(Find-SystemAlias '火警电话系统').canonicalSystemTypeCandidate -eq 'fire_phone') 'Ontology alias independent of page'
Check (@(Find-SystemAlias '消防广播与火灾报警系统').Count -eq 2) 'Multiple systems retained'
$old=Get-Content "$root/ew0002-design-statements-reviewed-v2-20260924.json" -Raw|ConvertFrom-Json
$oh=Get-Content "$root/ew0002-hierarchy-bridge-validated-20260924.json" -Raw|ConvertFrom-Json
$o=Add-DesignSystemScopes $old $oh 'local-project'
$negative=@($o.designStatements|Where-Object {$_.sourceEntityHandles -contains '23428' -or $_.sourceEntityHandles -contains '23401' -or $_.sourceEntityHandles -contains '23402'})
Check ($negative.Count -eq 3 -and @($negative|Where-Object systemScopeStatus -NE unknown).Count -eq 0) 'Nonfire protection does not become fire system'
Import-Module (Join-Path $PSScriptRoot '../../model-core/FireGoldenSample.psm1')
$fire=Read-FireGoldenModel
$req=@($fire.requirements|Where-Object requirementId -In @('req:phone-relation','req:broadcast','req:membership'))
$rb=$req|ConvertTo-Json -Depth 80 -Compress
$tasks=@($req|ForEach-Object {[pscustomobject]@{requirement=$_;context=[pscustomobject]@{mode='engineering_task'}}})
$c=Invoke-EvidenceInvestigation $all $tasks
foreach($q in $req){Check (@($c.evaluations|Where-Object {$_.requirementRef -eq $q.requirementId -and $_.status -eq 'task_relevant'}).Count -gt 0) 'Each real fire task gains candidate guidance'}
Check (($req|ConvertTo-Json -Depth 80 -Compress) -ceq $rb) 'Requirement states unchanged'
foreach($search in $c.searchScopes){$q=@($req|Where-Object requirementId -EQ $search.requirementRef)[0];Check ($search.systemIdentity -eq $q.systemIdentity.systemType) 'No cross-system association';Check (!$search.automaticTargetSelection) 'No target selection'}
Check ($c.requirementUpdates.Count -eq 0 -and $c.networkEdges.Count -eq 0) 'No actual relation'
$raw=@{};foreach($f in $h.after.rawTextRecords){$raw[$f.handle]=$f.rawText}
foreach($evidence in $all){foreach($scope in $evidence.systemScopeCandidates){foreach($span in $scope.sourceRefs){Check ($raw[$span.handle].Substring($span.start,$span.length) -ceq $span.rawText) 'Every scope term traces to exact raw text'}}}
$multi=@($all|Where-Object {$_.sourceEntityHandles -contains '23779'})[0]
Check ($multi.evidenceSystemScopeStatus -eq 'ambiguous' -and $multi.systemIdentity -eq 'unknown') 'Alarm and broadcast coexist without merge'
Check (@($c.evaluations|Where-Object {$_.evidenceRef -eq $multi.evidenceId -and $_.status -eq 'task_relevant'}).Count -eq 0) 'Ambiguous statement cannot enter either network task'
$foreign=$req|ConvertTo-Json -Depth 80|ConvertFrom-Json
foreach($q in $foreign){$q.scope.projectId='foreign-project'}
$ft=@($foreign|ForEach-Object {[pscustomobject]@{requirement=$_;context=[pscustomobject]@{mode='engineering_task'}}})
Check (!(Invoke-EvidenceInvestigation $all $ft).searchScopes.Count) 'No project scope propagation'
Check (@(Find-SystemAlias '普通照明系统 消防设施 配电线路保护 非消防负荷').Count -eq 0) 'Electrical is not fire-alarm identity'
Check (@(Find-SystemAlias '火灾报警系统电源').Count -eq 1 -and @(Find-SystemAlias '火灾报警系统电源')[0].canonicalSystemTypeCandidate -eq 'fire_alarm_power') 'Power has independent longest alias'
$s2=($s|ConvertTo-Json -Depth 80 -Compress).Replace('233CA','ABC99').Replace('10.1.14','91.8.76')|ConvertFrom-Json
$h2=($h|ConvertTo-Json -Depth 80 -Compress).Replace('233CA','ABC99').Replace('10.1.14','91.8.76')|ConvertFrom-Json
$renamed=Add-DesignSystemScopes $s2 $h2 'local-project'
Check (($renamed.designStatements.systemScopeStatus -join '|') -ceq ($r.designStatements.systemScopeStatus -join '|')) 'Handles and numbering do not determine scopes'
Check (@($renamed.designStatements|ForEach-Object systemScopeCandidates|ForEach-Object sourceRefs|Where-Object handle -EQ ABC99).Count -gt 0) 'Renamed raw identity preserved'
$cross=$h|ConvertTo-Json -Depth 80|ConvertFrom-Json
$phone=@($r.designStatements|Where-Object {$_.sourceEntityHandles -contains '233CA'})[0]
$foreignFragment=@($cross.after.rawTextRecords|Where-Object handle -EQ '234DB')[0]
$p=@($cross.after.paragraphs|Where-Object paragraphId -EQ $phone.paragraphRef)[0]
$p.textFragments=@($p.textFragments)+@($foreignFragment)
$isolated=Add-DesignSystemScopes $s $cross 'local-project'
$phoneAfter=@($isolated.designStatements|Where-Object statementId -EQ $phone.statementId)[0]
Check ($phoneAfter.systemScopeStatus -eq 'supported_candidate' -and @($phoneAfter.systemScopeCandidates|Where-Object canonicalSystemTypeCandidate -NE fire_phone).Count -eq 0) 'Paragraph context cannot leak across section boundary'
Write-Host "PASS: $script:n system scope propagation checks"
