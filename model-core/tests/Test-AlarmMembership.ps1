param([string]$OutputPath)
$ErrorActionPreference='Stop'
$r=& (Join-Path $PSScriptRoot '../Read-AlarmMembership.ps1') -OutputPath $OutputPath
function Check($ok,$why){if(!$ok){throw $why}}
function CloneCandidate($x){$x|ConvertTo-Json -Depth 90|ConvertFrom-Json}
function Reject($action){$failed=$false;try{& $action|Out-Null}catch{$failed=$true};Check $failed 'Invalid membership accepted'}
Check ($r.categoryMembershipCoverage.Count -eq 6) 'Six reviewed alarm categories'
$smoke=@($r.categoryMembershipCoverage|Where-Object role -EQ smoke_detector)[0]
Check ($smoke.explicit -eq 20 -and $smoke.inherited -eq 88 -and $smoke.quantityDelta -eq 4) 'Smoke evidence tiers unchanged'
Check (@($r.edges|Where-Object relationType -EQ branch_to_bus).Count -eq 14) 'Bus contacts retained'
Check (@($r.memberships|Where-Object confirmed).Count -eq 0) 'No confirmed members'
Check (!$r.routingEdges.Count -and !$r.circuits.Count -and !$r.quantities.Count) 'No physical products'
Check (@($r.gaps|Where-Object bridgeAllowed).Count -eq 0) 'No boundary bridge'
Check (@($r.nodes|Where-Object {$_.systemIdentity.systemType -ne 'fire_alarm'}).Count -eq 0) 'System isolation'
Check (@($r.reviewItems|Where-Object {$_.reason -eq 'quantity_mismatch' -and $_.status -eq 'open'}).Count -ge 3) 'Smoke phone broadcast reviews survive'
Import-Module (Join-Path $PSScriptRoot '../LogicalMembership.psm1') -Force
$b=@{sourceRegion=$r.sourceRegion};$n=$r.upstreamNetwork;$m=$r.upstreamMappings[0]
$before=$n|ConvertTo-Json -Depth 90 -Compress
foreach($system in @('unknown','fire_phone','fire_broadcast')){$bad=CloneCandidate $m;$bad.systemIdentity=$system;Reject {Join-LogicalNetworkMembership $n $m.compartmentRef $b.sourceRegion.reference @($bad)}}
$bad=CloneCandidate $m;$bad.compartmentRef='another';Reject {Join-LogicalNetworkMembership $n $m.compartmentRef $b.sourceRegion.reference @($bad)}
$bad=CloneCandidate $m;$bad.membershipStatus='unresolved';$x=Join-LogicalNetworkMembership $n $m.compartmentRef $b.sourceRegion.reference @($bad);Check (!$x.memberships.Count) 'Unresolved mapping cannot join'
$bad=CloneCandidate $m;$bad.assessments[0].classification='on_boundary';$bad.membersExplicit=@($bad.assessments[0].instanceRef);Reject {Join-LogicalNetworkMembership $n $m.compartmentRef $b.sourceRegion.reference @($bad)}
$bad=CloneCandidate $m;$bad.systemQuantityCandidate=999;$x=Join-LogicalNetworkMembership $n $m.compartmentRef $b.sourceRegion.reference @($bad);Check ($x.memberships.Count -eq $m.roleSupportedExpressionCount) 'Count cannot create edges'
Check (($n|ConvertTo-Json -Depth 90 -Compress) -ceq $before) 'Upstream untouched'
$bad=CloneCandidate $m;$bad.membersInherited+=@($bad.membersInherited[0]);Reject {Join-LogicalNetworkMembership $n $m.compartmentRef $b.sourceRegion.reference @($bad)}
$badNet=CloneCandidate $n;$badNet.edges[0].geometryType='segment_crossing';Reject {Join-LogicalNetworkMembership $badNet $m.compartmentRef $b.sourceRegion.reference @($m)}
$badNet=CloneCandidate $n;$badNet.gaps[0].bridgeAllowed=$true;Reject {Join-LogicalNetworkMembership $badNet $m.compartmentRef $b.sourceRegion.reference @($m)}
Check (@($r.requirements|Where-Object status -EQ satisfied).Count -eq 0) 'Requirements not satisfied'
$r.categoryMembershipCoverage|Format-Table role,members,explicit,inherited,quantityConsistency,quantityDelta
Write-Host "PASS alarm membership: nodes=$($r.knownNodes) edges=$($r.knownEdges) memberships=$($r.memberships.Count) unresolved=$($r.unresolvedEdges)"
