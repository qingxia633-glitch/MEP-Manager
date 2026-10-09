$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../LocalLogicalNetwork.psm1') -Force
Import-Module (Join-Path $PSScriptRoot '../LocalFireNetworkSample.psm1') -Force
$script:n=0
function Check($ok,$why){if(!$ok){throw $why};$script:n++}
function Reject($action){$caught=$false;try{& $action|Out-Null}catch{$caught=$true};Check $caught 'Invalid input accepted'}
$b=Read-LocalFireNetworkBundle
$before=$b|ConvertTo-Json -Depth 90 -Compress
$r=ConvertTo-LocalLogicalNetworkCandidates $b
Check ($r.networks.Count-eq 3) 'Three independent networks'
Check (($r.networks.systemIdentity.systemType -join ',')-eq 'fire_alarm,fire_phone,fire_broadcast') 'Systems distinct'
$a=$r.networks[0];$p=$r.networks[1];$g=$r.networks[2]
$terminalGaps=@($r.networks.gaps|Where-Object boundaryObjectRef -EQ $b.handleIndex.'15E08')
Check ($terminalGaps.Count-eq 3) 'Three terminal boundary gap records'
foreach($gap in $terminalGaps){
 Check ($gap.boundaryRelationStatus-eq 'supported_candidate') 'Two real boundary contacts required'
 Check ($gap.internalContinuityStatus-eq 'unresolved' -and !$gap.bridgeAllowed) 'Contact does not imply conduction'
 Check ($gap.leftBoundaryContact.pointMarkerMatches.Count-eq 0 -and $gap.rightBoundaryContact.pointMarkerMatches.Count-eq 0) 'No terminal POINT hit'
 Check ($gap.gapReason-eq 'internal_terminal_mapping_not_represented') 'Read definition must not remain unread'
 Check ($gap.terminalNumber-eq 'unresolved' -and $gap.portRole-eq 'unresolved' -and $gap.direction-eq 'unresolved') 'No invented terminal role or direction'
}
Check ($p.edges.Count-eq 5) 'Phone continuity includes curved branch endpoint on straight trunk'
Check (@($a.edges|Where-Object relationType -EQ branch_to_bus).Count-eq 14) 'Fourteen exact bus branches'
Check (@($a.excludedRelations|Where-Object {$_.geometryType-eq 'segment_crossing' -and $_.representationRefs-contains $b.handleIndex.'19CE2'}).Count-eq 1) 'Crossing retained without edge'
Check (@($r.networks.edges|Where-Object {$_.representationRefs-contains $b.handleIndex.'19CE2'}).Count-eq 0) 'Crossing does not enter network'
Check ($r.crossSystemAssociations.Count-eq 2) 'Two explicit cross-system interfaces'
foreach($cross in $r.crossSystemAssociations){Check (!$cross.networkMergeAllowed -and $cross.direction-eq 'unresolved' -and $cross.portMapping-eq 'unresolved') 'No merge or direction'}
foreach($handle in @('15DF5','15DFF')){
 $nodes=@($r.networks.nodes|Where-Object representationRef -EQ $b.handleIndex.$handle)
 Check ($nodes.Count-eq 2 -and @($nodes.nodeId|Select-Object -Unique).Count-eq 2) 'Shared raw representation has distinct system nodes'
}
Check ($a.gaps.Count-eq 2 -and $p.gaps.Count-eq 1 -and $g.gaps.Count-eq 1) 'Four independent gaps'
foreach($gap in $r.networks.gaps){
 Check (!$gap.bridgeAllowed -and $gap.status-eq 'unresolved') 'Gap never filled'
 Check (@($r.networks.edges|Where-Object {($_.fromNode-eq $gap.fromNode -and $_.toNode-eq $gap.toNode)-or ($_.toNode-eq $gap.fromNode -and $_.fromNode-eq $gap.toNode)}).Count-eq 0) 'No edge across gap'
 $expected=if($gap.probableBoundaryObject-eq $b.handleIndex.'15E03'){469.470299}else{404.386364}
 Check ([math]::Abs($gap.separationDrawingUnits-$expected)-lt 1e-5) 'Raw gap distance verified'
}
foreach($net in $r.networks){
 Check ($net.completenessStatus-eq 'partial' -and !$net.isActualNetwork -and !$net.automaticRoutingEnabled) 'Local incomplete candidate only'
 foreach($node in $net.nodes){Check ($node.systemIdentity.systemType-eq $net.systemIdentity.systemType -and $node.portRole-eq 'unresolved') 'Node isolation and unresolved ports'}
 foreach($edge in $net.edges){
  Check ($edge.systemIdentity.systemType-eq $net.systemIdentity.systemType -and $edge.admissionStatus-eq 'candidate_only' -and $edge.physicalConnection-eq 'unresolved' -and $edge.direction-eq 'unresolved') 'Candidate edge boundaries'
  Check (@($net.nodes|Where-Object {$_.nodeId-in @($edge.fromNode,$edge.toNode)}).Count-eq 2) 'Endpoints local to one network'
  Check ($edge.evidenceRefs.Count-gt 0 -and $edge.representationRefs.Count-ge 2) 'Edge provenance'
 }
 Check ($net.openEnds.Count-gt 0 -and $net.boundaries.Count-gt 0) 'Explicit open ends and region boundaries'
}
Check (@($g.edges|Where-Object relationType -EQ line_to_device_representation).Count-eq 3) 'Module two sides and speaker contact'
$line=$r.sourceReferences.($b.handleIndex.'15DEC')
$layer='WIRE-'+[char]0x6D88+[char]0x9632
Check ($line.rawLayer-ceq $layer) 'Raw layer retained'
$pathNode=@($g.nodes|Where-Object representationRef -EQ $b.handleIndex.'15DEC')[0]
Check ($pathNode.scopeBasis-eq 'endpoint roles + local system context') 'Broadcast scope not inferred from layer'
Check (($r.requirements.status -join ',')-eq 'missing,missing,partial') 'Requirements unchanged'
Check ($r.requirementSupports.Count-eq 3 -and @($r.requirementSupports|Where-Object canSatisfyRequirement).Count-eq 0) 'Investigation support only'
Check (($r.routing.Count+$r.actualNetworks.Count+$r.physicalConnections.Count+$r.circuits.Count+$r.quantities.Count)-eq 0) 'No routing or engineering outputs'
Check (($b|ConvertTo-Json -Depth 90 -Compress)-ceq $before) 'Input not mutated'
$x=$before|ConvertFrom-Json
$x.networks[0].gaps[0].toPoint[0]+=20
$one=ConvertTo-LocalLogicalNetworkCandidates $x
Check ($one.networks[0].gaps[0].boundaryRelationStatus-eq 'partial') 'One side contact cannot support complete boundary relation'
Check (!$one.networks[0].gaps[0].bridgeAllowed -and $one.networks[0].edges.Count-eq $a.edges.Count) 'No shortest-path gap bridge'
$x=$before|ConvertFrom-Json
$x.networks[0].gaps[0].fromPoint=@($x.networks[0].gaps[0].boundaryEvidence.pointMarkers[3].position)
$pointHit=ConvertTo-LocalLogicalNetworkCandidates $x
Check ($pointHit.networks[0].gaps[0].leftBoundaryContact.pointMarkerMatches.Count-eq 1) 'Synthetic marker hit detected geometrically'
Check ($pointHit.networks[0].gaps[0].terminalNumber-eq 'unresolved' -and $pointHit.networks[0].gaps[0].portRole-eq 'unresolved') 'POINT does not define a terminal or port'
Check (($r.networks.edges.Count)-eq 29 -and $r.crossSystemAssociations.Count-eq 2) 'DZX creates neither conduction edges nor cross-system links'
Check (@($r.summary|Where-Object boundarySupportedGaps -EQ 1).Count-eq 3) 'Three independent boundary-supported gaps in summary'
Check (($r.summary.unresolvedPureGaps -join ',')-eq '1,0,0') 'Isolator gap remains unresolved'
Check (@($r.capabilityCoverage|Where-Object status -EQ validated_sample).Count-eq 2) 'Bounded capabilities validated only on this sample'
Check (@($r.reviewItems|Where-Object {$_.type-eq 'unresolved_dual_semantics' -and $_.status-eq 'open'}).Count-ge 1) 'Hidden semantics stays open'
# Geometry tests have no project IDs or Handles.
$lineA=@(@(0,0,0),@(10,0,0));$lineB=@(@(5,-2,0),@(5,2,0));$branch=@(@(5,0,0),@(5,2,0))
Check ((Get-LocalSegmentRelation $lineA $lineB).geometryType-eq 'segment_crossing') 'Interior crossing excluded'
Check ((Get-LocalSegmentRelation $lineA $branch).geometryType-eq 'endpoint_on_segment') 'T contact'
Check ((Get-LocalSegmentRelation $lineA @(@(10,0,0),@(11,1,0))).geometryType-eq 'endpoint_coincidence') 'Endpoint contact'
Check ((Get-LocalSegmentRelation $lineA @(@(5,0,1),@(5,2,1))).geometryType-eq 'separate') 'Different elevations rejected'
Check ((Get-LocalSegmentRelation $lineA @(@(10.01,0,0),@(11,0,0))).geometryType-eq 'separate') 'Near is not contact'
Check ((Get-LocalSegmentRelation $lineA @(@(5,0,0),@(15,0,0))).geometryType-eq 'collinear_overlap') 'Overlap not silently connected'
Check ((Get-LocalSegmentRelation $lineA $branch 0.00001 @() @(0.414214,0)).geometryType-eq 'endpoint_on_segment') 'Curved endpoint on straight trunk is valid'
Check ((Get-LocalSegmentRelation $lineA $lineB 0.00001 @(0.414214,0) @()).geometryType-eq 'unresolved_curve_relation') 'No chord crossing inference'
$x=$before|ConvertFrom-Json;$x.networks[1].system='unknown';Reject {ConvertTo-LocalLogicalNetworkCandidates $x}
$x=$before|ConvertFrom-Json;$x.networks[1].nodes[0].systemIdentity='fire_alarm';Reject {ConvertTo-LocalLogicalNetworkCandidates $x}
$x=$before|ConvertFrom-Json;$x.networks[0].relations[0].systemIdentity='fire_phone';Reject {ConvertTo-LocalLogicalNetworkCandidates $x}
$x=$before|ConvertFrom-Json;$x.networks[0].relations[0].geometryStatus='unresolved'
$q=ConvertTo-LocalLogicalNetworkCandidates $x
Check ($q.networks[0].edges.Count-eq $a.edges.Count-1) 'Unsupported relation not admitted'
$x=$before|ConvertFrom-Json;foreach($ref in $x.references.PSObject.Properties){$ref.Value.handle='renamed'}
$q=ConvertTo-LocalLogicalNetworkCandidates $x
Check (($q.networks.edges.Count)-eq ($r.networks.edges.Count)) 'No Handle keyed policy'
$x=$before|ConvertFrom-Json;$x.networks[0].relations[0].fromRef=$x.networks[0].gaps[0].fromRef;$x.networks[0].relations[0].toRef=$x.networks[0].gaps[0].toRef
$q=ConvertTo-LocalLogicalNetworkCandidates $x
Check (@($q.networks[0].excludedRelations|Where-Object reason -EQ 'gap_cannot_be_bridged').Count-eq 1) 'Even claimed supported contact cannot bridge declared gap'
Check (($r|ConvertTo-Json -Depth 90)-notmatch '"value"\s*:') 'No nested reference array serialization wrapper'
foreach($net in $r.networks){foreach($edge in $net.edges){foreach($reference in $edge.evidenceRefs){Check ($reference-is [string] -and $null-ne $r.sourceReferences.PSObject.Properties[$reference]) 'Serialized references resolve to source catalogue'}}}
Reject {Get-LocalSegmentRelation @(@(0,0),@(1,1)) $lineA}
Reject {Get-LocalSegmentRelation $lineA @(@([double]::NaN,0,0),@(1,1,0))}
$x=$before|ConvertFrom-Json;$x.references.($x.networks[0].nodes[0].representationRef).sourceSnapshot='foreign-snapshot'
Reject {ConvertTo-LocalLogicalNetworkCandidates $x}
# Existing admission remains blocked for actual edges despite local candidate overlay.
Import-Module (Join-Path $PSScriptRoot '../../design-knowledge/EvidenceAdmission.psm1') -Force
. (Join-Path $PSScriptRoot '../../design-knowledge/tests/Read-RelationChainFixture.ps1')
$cb=Read-RelationChainFixture;$cr=Get-RelationChainAdmission $cb
Check (!(Test-RelationChainEvidenceUse $cr create_logical_network_edge $cb.scopeId fire_broadcast)) 'Local overlay does not relax existing actual edge gate'
Write-Host "PASS: $script:n local logical network checks"
$r.summary|Format-Table -AutoSize
