param([string]$OutputPath)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../RoutingCorrespondence.psm1') -Force
function Assert($condition,$message){if(!$condition){throw $message}}
$root=Resolve-Path (Join-Path $PSScriptRoot '../..')
$rp=Join-Path $root 'outputs/fire-alarm-routing/results.json'
$lp=Join-Path $root 'outputs/fire-alarm-logical-network/results.json'
$ap=Join-Path $root 'outputs/fire-alarm-routing/device-attachment.json'
$before=@($rp,$lp,$ap|ForEach-Object {(Get-FileHash $_).Hash})
$r=Get-Content $rp -Raw -Encoding utf8|ConvertFrom-Json
$l=Get-Content $lp -Raw -Encoding utf8|ConvertFrom-Json
$a=Get-Content $ap -Raw -Encoding utf8|ConvertFrom-Json
$x=& (Join-Path $PSScriptRoot '../Read-RoutingCorrespondence.ps1') -OutputPath $OutputPath
Assert ($x.statistics.rawOpenEndpointCount -eq 148 -and $x.statistics.deviceTerminatedCandidateCount -eq 94 -and $x.statistics.unexplainedOpenEndpointCount -eq 54) 'Real termination counts'
Assert ($x.statistics.attachedDevices -eq 67 -and $x.resultComponentCount -eq 74) 'Device/component preservation'
Assert (@($x.terminations|Where-Object {!$_.rawOpenEndpoint}).Count -eq 0) 'Raw endpoints must survive'
Assert ($x.logicalEdgeCorrespondences.Count -eq 17 -and @($x.logicalEdgeCorrespondences|Where-Object status -eq supported).Count -eq 0) 'No invented edge correspondence'
Assert ($x.createdRoutingEdges.Count -eq 0 -and $x.confirmedConnections.Count -eq 0 -and !$x.bridgeAllowed -and !$x.requirementsModified) 'Forbidden mutation'
Assert (@($x.continuations|Where-Object {$_.bridgeAllowed -or $_.internalContinuity -ne 'unresolved'}).Count -eq 0) 'No device bridging'
Assert ($x.golden.Count -eq 1 -and $x.golden[0].membershipStatus -eq 'partial') 'Traceable partial Golden'
Assert ($x.statistics.oneAttachment -eq 42 -and $x.statistics.twoAttachments -eq 21 -and $x.statistics.moreAttachments -eq 4 -and $x.continuations.Count -eq 25) 'Real device endpoint aggregation'
Assert (@($x.logicalEdgeCorrespondences|Where-Object status -eq unresolved).Count -eq 2 -and @($x.logicalEdgeCorrespondences|Where-Object status -eq no_candidate).Count -eq 15) 'Preserve unresolved branch target evidence'
Assert (($x.upstreamReviewItems|ConvertTo-Json -Depth 60 -Compress) -ceq ($l.reviewItems|ConvertTo-Json -Depth 60 -Compress)) 'Upstream reviews changed'
Assert (@($x.upstreamGaps|Where-Object bridgeAllowed).Count -eq 0 -and @($x.reviewItems|Where-Object type -eq terminal_box_internal_unknown).Count -gt 0) 'DZX not bridged or forgotten'
foreach($d in $x.deviceAttachments){$original=@($a.geometry|Where-Object instanceRef -CEQ $d.deviceRef)[0];Assert ($d.roleStatus -ceq $original.roleStatus) 'Inherited role cannot be upgraded'}
$withoutMembership=$l|ConvertTo-Json -Depth 90|ConvertFrom-Json
$withoutMembership.memberships=@()
$case=Join-RoutingCorrespondence $r $withoutMembership $a
Assert ($case.correspondences.Count -eq 0 -and $case.statistics.deviceTerminatedCandidateCount -eq 94) 'Geometry cannot invent logical membership'
$unexplained=@($x.terminations|Where-Object terminationType -eq unresolved)[0].endpointRef
foreach($kind in @('terminal_box_boundary_candidate','drawing_open_end','missing_geometry_candidate')){
 $evidence=[pscustomobject]@{endpointRef=$unexplained;sourceSnapshot=$r.sourceSnapshot;systemScope='fire_alarm';status='supported_candidate';terminationType=$kind;evidenceRefs=@('controlled-test-evidence')}
 $case=Join-RoutingCorrespondence $r $l $a @($evidence)
 Assert (@($case.terminations|Where-Object {$_.endpointRef -eq $unexplained})[0].terminationType -eq $kind) 'Evidence-gated termination type'
 $evidence.sourceSnapshot='system-diagram'
 $case=Join-RoutingCorrespondence $r $l $a @($evidence)
 Assert (@($case.terminations|Where-Object {$_.endpointRef -eq $unexplained})[0].terminationType -eq 'unresolved') 'Cannot transplant system diagram DZX to plan'
}
# Crossing and near pairs remain inadmissible even with a corrupted admission flag.
$copy=$a|ConvertTo-Json -Depth 90|ConvertFrom-Json
$copy.relations=@($copy.relations|Where-Object {$_.relationType -in @('crossing_through_representation','segment_ends_near_boundary')})
foreach($q in $copy.relations){$q.attachmentAllowed=$true;$q.status='supported_candidate'}
$negative=Join-RoutingCorrespondence $r $l $copy
Assert ($negative.statistics.deviceTerminatedCandidateCount -eq 0 -and $negative.continuations.Count -eq 0) 'Crossing/near cannot terminate or continue'
$copy=$a|ConvertTo-Json -Depth 90|ConvertFrom-Json
$copy.sourceSnapshot='other-drawing';$blocked=$false;try{Join-RoutingCorrespondence $r $l $copy|Out-Null}catch{$blocked=$true};Assert $blocked 'Cross drawing mismatch'
$r.systemScope='unknown';$blocked=$false;try{Join-RoutingCorrespondence $r $l $a|Out-Null}catch{$blocked=$true};Assert $blocked 'Unknown is not wildcard'
$after=@($rp,$lp,$ap|ForEach-Object {(Get-FileHash $_).Hash})
Assert (($before -join ',') -ceq ($after -join ',')) 'Source mutation'
Write-Host ('PASS RoutingCorrespondence: '+($x.statistics|ConvertTo-Json -Compress))
