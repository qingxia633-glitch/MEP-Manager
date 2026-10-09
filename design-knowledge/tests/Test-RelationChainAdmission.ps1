$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../EvidenceAdmission.psm1') -Force
. (Join-Path $PSScriptRoot 'Read-RelationChainFixture.ps1')
$b=Read-RelationChainFixture;$before=$b|ConvertTo-Json -Depth 70 -Compress
$script:checks=0
function Check($ok,$message){if(!$ok){throw $message};$script:checks++}
function Clone {$before|ConvertFrom-Json}
function Decision($r,$u){@($r.admission.useDecisions|Where-Object use -EQ $u)[0].status}
$r=Get-RelationChainAdmission $b
Check ($b.references.instance.handle-eq '15DFF' -and $b.references.lowerLine.handle-eq '15DEC' -and $b.references.speaker.handle-eq '16268') 'Real chain identities'
Check ($b.geometryAudit.endsInside -and $b.geometryAudit.intersections.Count-eq 1) 'Real circle crossing and interior endpoint'
Check ([math]::Abs($b.geometryAudit.radius-256.5)-lt 1e-8 -and [math]::Abs($b.geometryAudit.intersections[0][1]-67683.833874)-lt 1e-5) 'Actual instance transform'
Check ($r.chain.status-eq 'supported_candidate' -and $r.chain.systemScopeCandidate-eq 'fire_broadcast' -and $r.chain.systemScopeStatus-eq 'candidate') 'Complete chain with candidate scope'
foreach($u in @('support_information_requirement','support_search_scope','support_relation_candidate','support_device_role')){
 Check ((Decision $r $u)-eq 'allowed') $u
 Check (Test-RelationChainEvidenceUse $r $u $b.scopeId fire_broadcast) 'Candidate-use gate'
}
Check ((Decision $r 'support_system_identity')-eq 'partial') 'Identity stays partial'
foreach($u in @('support_port_role','support_physical_connection','create_logical_network_edge','create_routing_edge','infer_signal_direction')){
 Check ((Decision $r $u)-eq 'blocked') $u
 Check (!(Test-RelationChainEvidenceUse $r $u $b.scopeId fire_broadcast)) 'Blocked consumer use'
}
foreach($k in @('direction','portMapping','physicalConnection','internalConduction','controlLogic')){Check ($r.chain.$k-eq 'unresolved') $k}
Check ($r.requirementSupports.Count-eq 1 -and $r.requirementSupports[0].requirementRef-eq 'req:broadcast' -and !$r.requirementSupports[0].canSatisfyRequirement) 'Broadcast investigation support only'
Check ($r.searchScopes.Count-eq 1 -and $r.investigationHints.Count-eq 1) 'One bounded search and hint'
Check ($b.requirements[0].status-eq 'missing' -and $b.requirements[1].status-eq 'partial') 'Both requirement states unchanged'
Check (@($r.reviewItems|Where-Object {$_.type-eq 'unresolved_dual_semantics' -and $_.status-eq 'open'}).Count-eq 1) 'Hidden semantics remains open'
Check ($r.endpointRoleCandidates[0].status-eq 'supported' -and $r.endpointRoleCandidates[1].status-eq 'candidate') 'Roles not upgraded by chain'
Check (($r.networks.Count+$r.routingEdges.Count+$r.connections.Count+$r.circuits.Count+$r.quantities.Count)-eq 0) 'No engineering outputs'
foreach($index in @(0,1)){$x=Clone;$x.contacts[$index].status='unresolved';$q=Get-RelationChainAdmission $x;Check ($q.chain.status-eq 'unresolved' -and $q.requirementSupports.Count-eq 0) 'One contact cannot complete chain'}
$x=Clone;$x.endpointRoles|ForEach-Object {$_.status='unknown'};$q=Get-RelationChainAdmission $x
Check ($q.chain.systemScopeCandidate-eq 'unknown' -and (Decision $q 'support_relation_candidate')-eq 'blocked') 'Contacts without roles do not support broadcast'
$x=Clone;$x.context.systemScopeCandidate='unknown';$q=Get-RelationChainAdmission $x
Check ($q.requirementSupports.Count-eq 0 -and $q.admission.allowedUses.Count-eq 0) 'Unknown not wildcard'
$x=Clone;$x.requirements[0].systemIdentity='fire_phone'
Check ((Get-RelationChainAdmission $x).requirementSupports.Count-eq 0) 'Phone cannot consume broadcast chain'
$x=Clone;$x.requirements[0].scopeId='other'
Check ((Get-RelationChainAdmission $x).requirementSupports.Count-eq 0) 'Scope isolation'
$x=Clone;$x.references.speakerBoundary.resolved=$false
Check ((Get-RelationChainAdmission $x).chain.status-eq 'unresolved') 'Missing boundary source blocks chain'
$x=Clone;$x.contacts[1].toRef=$x.endpointA
Check ((Get-RelationChainAdmission $x).chain.status-eq 'unresolved') 'Duplicate endpoint cannot substitute second end'
$x=Clone;foreach($p in $x.references.PSObject.Properties){$p.Value.handle='replacement'}
Check (((Get-RelationChainAdmission $x).admission.useDecisions.status -join ',')-eq ($r.admission.useDecisions.status -join ',')) 'No Handle keyed policy'
Check (!(Test-RelationChainEvidenceUse $r support_relation_candidate $b.scopeId unknown)) 'Unknown consumer rejected'
Check (!(Test-RelationChainEvidenceUse $r support_relation_candidate $b.scopeId fire_broadcast instance)) 'Instance application blocked'
Check (($b|ConvertTo-Json -Depth 70 -Compress)-ceq $before) 'Input facts and requirements not mutated'
$root=Resolve-Path (Join-Path $PSScriptRoot '../..')
$source=[IO.File]::ReadAllText((Join-Path $root $b.references.lowerLine.sourcePath))
$record=[regex]::Match($source,'(?ms)^EntityHandle="'+$b.references.lowerLine.handle+'".*?(?=^EntityHandle=|\z)').Value
$rawLayer='WIRE-'+[char]0x6D88+[char]0x9632
Check ($record-match ('(?m)^Layer="'+[regex]::Escape($rawLayer)+'"')) 'Raw layer retained'
Check ($r.chain.rawLayerRef-eq $b.pathRepresentation -and $r.chain.scopeSource-eq 'endpoint roles + local system context') 'Scope not inferred from layer'
Check (($r|ConvertTo-Json -Depth 70)-notmatch '"rawText"|"RawEntity"|"Layer"') 'No raw rewrite or duplicated entities'
$x=Clone;$x.contacts[1].geometryType='ends_inside'
Check ((Get-RelationChainAdmission $x).chain.status-eq 'unresolved') 'Inside alone does not prove boundary contact'
$x=Clone;$x.reviewItems+=,[pscustomobject]@{type='role_contradicted';status='open'}
Check ((Get-RelationChainAdmission $x).admission.admissionStatus-eq 'blocked') 'Other conflicts block semantic admission'
$x=Clone;$x.endpointRoles[1].systemScopeCandidate='fire_phone'
Check ((Get-RelationChainAdmission $x).admission.admissionStatus-eq 'blocked') 'Endpoint scope mismatch does not merge systems'
$x=Clone;$x.endpointRoles[1].roleCandidate='unknown'
Check ((Get-RelationChainAdmission $x).admission.admissionStatus-eq 'blocked') 'Unknown role label remains unknown despite candidate status'
Write-Host "RelationChainAdmission: $script:checks checks passed"
$r.admission.useDecisions|Format-Table use,status
