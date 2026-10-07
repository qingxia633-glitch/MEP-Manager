$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../RoleInheritance.psm1') -Force
$script:n=0
function Check($ok,$msg){if(!$ok){throw $msg};$script:n++}
function CloneRole($x){$x|ConvertTo-Json -Depth 30|ConvertFrom-Json}
function E($kind,$role='role_a',$doc='drawing_a'){
 New-RoleEvidenceSource -Kind $kind -CanonicalRole $role -RawText $role -SourceDocument $doc -Snapshot 'snapshot' -DefinitionRef 'definition' -SourceRefs @('raw:1') -CompatibilityRef 'reviewed-role-vocabulary'
}
$d=[pscustomobject]@{sourceDocument='drawing_a';scopeId='local_scope';definitionRef='definition';dynamicStatus='static';visibilityStateStatus='single';evidence=@((E block_definition_default))}
$i=[pscustomobject]@{instanceRef='raw:instance';sourceDocument='drawing_a';scopeId='local_scope';definitionRef='definition';dynamicStatus='static';roleAttributeState='absent_in_snapshot';evidence=@()}
$r=Resolve-DeviceRoleInheritance $d @($i)
Check ($r.instances[0].roleStatus -eq 'inherited_candidate') 'Missing own role may inherit supported local default'
$q=CloneRole $d;$q.evidence=@();Check ((Resolve-DeviceRoleInheritance $q @($i)).instances[0].roleStatus -eq 'unresolved') 'No default does not inherit'
$q=CloneRole $i;$q.roleAttributeState='present';$q.evidence=@((E instance_explicit));$r=Resolve-DeviceRoleInheritance $d @($q)
Check ($r.instances[0].roleStatus -eq 'explicit' -and $r.instances[0].inheritanceRequired -eq $false) 'Own compatible role retained'
$q.evidence=@((E instance_explicit role_b));$r=Resolve-DeviceRoleInheritance $d @($q)
Check ($r.instances[0].status -eq 'conflicting' -and $r.instances[0].roleStatus -ne 'inherited_candidate') 'Own conflicting role not overwritten'
$a=CloneRole $i;$a.instanceRef='sibling_a';$a.roleAttributeState='present';$a.evidence=@((E instance_explicit))
$b=CloneRole $a;$b.instanceRef='sibling_b';$b.evidence=@((E instance_explicit role_b))
$r=Resolve-DeviceRoleInheritance $d @($i,$a,$b)
Check ($r.definition.status -eq 'conflicting' -and $r.instances[0].roleStatus -eq 'unresolved') 'Conflicting siblings block propagation'
$q=CloneRole $d;$q.dynamicStatus='dynamic';$q.visibilityStateStatus='unknown'
Check ((Resolve-DeviceRoleInheritance $q @($i)).instances[0].roleStatus -eq 'unresolved') 'Dynamic state unresolved blocks'
$q=CloneRole $d;$q.evidence=@((E block_definition_default role_a drawing_b))
Check ((Resolve-DeviceRoleInheritance $q @($i)).instances[0].roleStatus -eq 'unresolved') 'Cross-DWG same name insufficient'
$q=CloneRole $d;$q.evidence+=@(E project_legend role_b drawing_b);$r=Resolve-DeviceRoleInheritance $q @($i)
Check ($r.definition.status -eq 'conflicting' -and $r.instances[0].roleStatus -eq 'unresolved') 'Legend conflict does not replace local default'
$q=CloneRole $i;$q.roleAttributeState='present_empty'
Check ((Resolve-DeviceRoleInheritance $d @($q)).instances[0].roleStatus -eq 'unresolved') 'Empty role attribute is not missing'
$q=CloneRole $d;$q.evidence+=@(E block_definition_default role_b)
Check ((Resolve-DeviceRoleInheritance $q @($i)).definition.status -eq 'conflicting') 'Multiple defaults block'
$q=CloneRole $i;$q.scopeId='other_scope'
Check ((Resolve-DeviceRoleInheritance $d @($q)).instances[0].status -eq 'blocked') 'Scope isolation'
$q=CloneRole $i;$q.sourceDocument='other_drawing'
Check ((Resolve-DeviceRoleInheritance $d @($q)).instances[0].status -eq 'blocked') 'Instance document isolation'
$q=CloneRole $d;$q.visibilityStateStatus='multiple'
Check ((Resolve-DeviceRoleInheritance $q @($i)).instances[0].roleStatus -eq 'unresolved') 'Multiple states block'
$q=CloneRole $d;$q.evidence[0].sourceRefs=@()
Check ((Resolve-DeviceRoleInheritance $q @($i)).instances[0].roleStatus -eq 'unresolved') 'Missing provenance blocks'
. (Join-Path $PSScriptRoot 'Read-SmokeRoleFixture.ps1')
$q=CloneRole $d;$q.evidence=@((E human_confirmation))
Check ((Resolve-DeviceRoleInheritance $q @($i)).instances[0].roleStatus -eq 'unresolved') 'Human evidence alone not an automatic default override'
$q=CloneRole $d;$q.evidence=@((E block_definition_default unknown))
Check ((Resolve-DeviceRoleInheritance $q @($i)).instances[0].roleStatus -eq 'unresolved') 'Unknown is not a role wildcard'
$q=CloneRole $d;$q.evidence=@()
Check ((Resolve-DeviceRoleInheritance $q @($i,$a)).instances[0].roleStatus -eq 'unresolved') 'Sibling evidence alone insufficient'
$q=CloneRole $i;$q.dynamicStatus='unknown'
Check ((Resolve-DeviceRoleInheritance $d @($q)).instances[0].roleStatus -eq 'unresolved') 'Instance dynamic state missing blocks'
$f=Read-SmokeRoleFixture
$q=CloneRole $d;$q.evidence+=@(E block_definition_default unknown)
Check ((Resolve-DeviceRoleInheritance $q @($i)).instances[0].roleStatus -eq 'unresolved') 'Unresolved additional default cannot be silently ignored'
$q=CloneRole $d;$e=E project_legend;$e.status='conflicting';$q.evidence+=@($e)
Check ((Resolve-DeviceRoleInheritance $q @($i)).instances[0].status -eq 'conflicting') 'Explicit legend conflict status blocks'
$before=$f|ConvertTo-Json -Depth 40 -Compress
$r=Resolve-DeviceRoleInheritance $f.definition $f.instances
Check (($f|ConvertTo-Json -Depth 40 -Compress) -ceq $before) 'Raw input preserved'
Check ($r.instances.Count -eq 821) 'All real representations retained'
Check (@($r.instances|Where-Object roleStatus -eq explicit).Count -eq 80) '80 explicit'
Check (@($r.instances|Where-Object roleStatus -eq inherited_candidate).Count -eq 741) '741 inherited candidates'
Check ($r.conflicts.Count -eq 0) 'No real conflicts'
foreach($x in $r.instances){Check ($x.confirmedInstanceRole -eq $false -and $x.sourceRefs.Count -gt 0) 'Candidate only and traceable'}
$inside=@($r.instances|Where-Object {$_.instanceRef -in $f.insideRefs})
Check (@($inside|Where-Object roleStatus -eq explicit).Count -eq 20) '20 explicit inside'
Check (@($inside|Where-Object roleStatus -eq inherited_candidate).Count -eq 88) '88 inherited inside'
$audit=[pscustomobject]@{insideExplicit=@($inside|Where-Object roleStatus -eq explicit).Count;insideInheritedCandidate=@($inside|Where-Object roleStatus -eq inherited_candidate).Count;systemQuantityCandidate=$f.quantity;quantityConsistency=$(if($f.quantity -eq $inside.Count){'consistent_candidate'}else{'mismatch_candidate'});delta=($f.quantity-$inside.Count);cause='unresolved';quantityRef=$f.quantityRef;polygonRef=$f.polygonRef}
Check ($f.quantity -eq 112 -and $audit.delta -eq 4) 'Independent mismatch retained'
Write-Output "PASS: $script:n role inheritance checks; explicit=80 inherited_candidate=741 conflicts=0 confirmed=0"
$audit|ConvertTo-Json -Compress
