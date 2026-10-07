$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../EvidenceAdmission.psm1') -Force
. (Join-Path $PSScriptRoot 'Read-RoleFixture.ps1')
$b=Read-RoleAdmissionFixture
$before=$b|ConvertTo-Json -Depth 70 -Compress
$script:checks=0
function Check($ok,$message){if(!$ok){throw $message};$script:checks++}
function Clone { $before|ConvertFrom-Json }
function Decision($r,$u){@($r.admission.useDecisions|Where-Object use -EQ $u)[0].status}
$r=Get-RoleEvidenceAdmission $b
$allowed=@('support_device_role','support_cross_system_association','support_information_requirement','support_search_scope')
$partial=@('support_system_identity','support_logical_network_membership')
$blocked=@('support_port_role','support_physical_connection')
foreach($u in $allowed){Check ((Decision $r $u)-eq 'allowed') $u}
foreach($u in $partial){Check ((Decision $r $u)-eq 'partial') $u}
foreach($u in $blocked){Check ((Decision $r $u)-eq 'blocked') $u}
Check ($r.deviceRole.status-eq 'supported' -and $r.deviceRole.subjectRef-eq 'instance') 'Real instance role supported'
Check ($b.references.instance.handle-eq '15DFF' -and $b.references.legendSymbol.handle-eq '239B2') 'Real identities'
Check ($r.reviewItems[0].status-eq 'open') 'Dual semantics remains open'
Check ($r.crossSystemAssociation.status-eq 'supported') 'Interface expression supported'
foreach($k in @('direction','portMapping','internalConduction','controlLogic','physicalConnection')){Check ($r.crossSystemAssociation.$k-eq 'unresolved') $k}
Check (!$r.crossSystemAssociation.networkMergeAllowed) 'No network merge'
Check ($r.lineRelations.Count-eq 3) 'Three boundary relations'
foreach($l in $r.lineRelations){Check ($l.status-eq 'supported' -and $l.portConnection-eq 'unresolved' -and $l.physicalConnection-eq 'unresolved') 'Boundary not port'}
Check ($r.requirementSupports.Count-eq 2 -and $r.searchScopes.Count-eq 2 -and $r.investigationHints.Count-eq 2) 'Two independent investigation tasks'
Check (($r.searchScopes[0].regionCandidates -join ',')-eq 'instance,lowerLine,speaker') 'Local references narrow search'
Check (($b|ConvertTo-Json -Depth 70 -Compress)-ceq $before) 'Input requirements and reviews unchanged'
Check ($b.requirements[0].status-eq 'missing' -and $b.requirements[1].status-eq 'partial') 'Requirement state preserved'
Check ($b.requirements[0].requirementId-eq 'req:broadcast' -and $b.requirements[1].requirementId-eq 'req:membership') 'Existing Golden requirement identities'
Check ($r.networks.Count-eq 0 -and $r.connections.Count-eq 0 -and $r.circuits.Count-eq 0 -and $r.quantities.Count-eq 0) 'No engineering outputs'
$x=Clone;$x.legend.status='unresolved';$x.compatibility.status='unresolved'
Check ((Decision (Get-RoleEvidenceAdmission $x) 'support_device_role')-eq 'blocked') 'Letter alone rejected'
$x=Clone;$x.legend.status='unresolved';$x.instanceCode='other'
Check ((Decision (Get-RoleEvidenceAdmission $x) 'support_device_role')-eq 'blocked') 'Rectangle and points alone rejected'
$x=Clone;$x.legend.status='unresolved'
Check ((Decision (Get-RoleEvidenceAdmission $x) 'support_port_role')-eq 'blocked') 'Boundary alone not a port'
$x=Clone;$x.reviewItems[0].status='resolved'
Check ((Get-RoleEvidenceAdmission $x).reviewItems[0].status-eq 'open') 'Distinct hidden names not silently resolved'
$x=Clone;$x.systemScopes=@('unknown');$x.boundaries|ForEach-Object {$_.systemIdentity='unknown'}
$q=Get-RoleEvidenceAdmission $x
Check ($q.requirementSupports.Count-eq 0 -and (Decision $q 'support_system_identity')-eq 'blocked') 'Unknown not wildcard'
$x=Clone;$x.requirements[0].systemIdentity='fire_phone'
Check (@((Get-RoleEvidenceAdmission $x).requirementSupports|Where-Object requirementRef -EQ $x.requirements[0].requirementId).Count-eq 0) 'Unrelated system rejected'
$x=Clone;$x.requirements[0].scopeId='other-project'
Check (@((Get-RoleEvidenceAdmission $x).requirementSupports|Where-Object requirementRef -EQ $x.requirements[0].requirementId).Count-eq 0) 'Project scope isolation'
$x=Clone;$x.references.instance.resolved=$false
Check ((Decision (Get-RoleEvidenceAdmission $x) 'support_device_role')-eq 'blocked') 'Missing provenance blocked'
$x=Clone;$x.boundaries[0].status='unresolved'
Check ((Decision (Get-RoleEvidenceAdmission $x) 'support_cross_system_association')-eq 'blocked') 'Two supported system sides required'
$x=Clone;$x.compatibility.sourceRefs=@('nonexistent')
Check ((Decision (Get-RoleEvidenceAdmission $x) 'support_device_role')-eq 'blocked') 'Missing comparison source blocked'
$x=Clone;$x.reviewItems+=,[pscustomobject]@{reviewId='direct-contradiction';type='role_contradicted';status='open';sourceRefs=@('legendName')}
Check ((Decision (Get-RoleEvidenceAdmission $x) 'support_device_role')-eq 'blocked') 'Other unresolved conflicts fail closed'
$x=Clone;$x.instanceCode='different-symbol'
Check ((Decision (Get-RoleEvidenceAdmission $x) 'support_device_role')-eq 'blocked') 'Different symbol code not silently compatible'
$x=Clone
foreach($p in $x.references.PSObject.Properties){$p.Value.handle='REPLACED';$p.Value.sourceSnapshot='replacement-snapshot'}
$q=Get-RoleEvidenceAdmission $x
Check (($q.admission.useDecisions.status -join ',')-eq ($r.admission.useDecisions.status -join ',')) 'No Handle or hash keyed admission'
foreach($u in $allowed){Check (Test-RoleEvidenceUse $r $u -ScopeId $b.scopeId -SystemIdentity fire_broadcast) 'Candidate consumer gate'}
foreach($u in $partial+$blocked){Check (!(Test-RoleEvidenceUse $r $u -ScopeId $b.scopeId -SystemIdentity fire_broadcast)) 'Partial and blocked cannot auto-apply'}
Check (!(Test-RoleEvidenceUse $r 'support_device_role' -ScopeId $b.scopeId -SystemIdentity unknown)) 'Unknown consumer denied'
Check (!(Test-RoleEvidenceUse $r 'support_device_role' -ScopeId $b.scopeId -SystemIdentity fire_broadcast -ApplicationMode instance)) 'Instance execution denied'
Check (!(Test-RoleEvidenceUse $r 'support_device_role' -ScopeId other -SystemIdentity fire_broadcast)) 'Wrong scope denied'
Check (!(Test-RoleEvidenceUse $r 'create_network_edge' -ScopeId $b.scopeId -SystemIdentity fire_broadcast)) 'Unregistered use denied'
$x=Clone;$x.systemScopes+='fire_phone';$q=Get-RoleEvidenceAdmission $x
Check (!(Test-RoleEvidenceUse $q 'support_device_role' -ScopeId $b.scopeId -SystemIdentity fire_phone)) 'Declared category without supported side cannot obtain permission'
$json=$r|ConvertTo-Json -Depth 70 -Compress
Check ($json-notmatch '"rawText"|"RawEntity"') 'Output retains references, not copies of raw records'
$roundtrip=$json|ConvertFrom-Json
Check (!(Test-RoleEvidenceUse $roundtrip 'support_physical_connection' -ScopeId $b.scopeId -SystemIdentity fire_alarm)) 'Serialization cannot grant connection permission'
$caps=Get-Content -LiteralPath (Join-Path $PSScriptRoot '../../model-core/capabilities.json') -Raw -Encoding UTF8|ConvertFrom-Json
foreach($id in @('evidence_usage_boundary','device_role_evidence_admission','cross_system_evidence_admission')){
 $c=@($caps|Where-Object id -EQ $id)
 Check ($c.Count-eq 1 -and $c[0].status-eq 'validated_sample') 'Bounded validated sample registration'
}
Write-Host "RoleEvidenceAdmission: $script:checks checks passed"
$r.admission.useDecisions|Format-Table use,status
