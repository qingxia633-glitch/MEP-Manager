Import-Module (Join-Path $PSScriptRoot 'ModelCore.psm1')
. (Join-Path $PSScriptRoot 'GapBoundary.ps1')

function Get-LocalSegmentRelation {
 param([object[]]$A,[object[]]$B,[double]$Tolerance=0.00001,[double[]]$BulgesA=@(),[double[]]$BulgesB=@())
 if($A.Count-ne 2 -or $B.Count-ne 2 -or $Tolerance-le 0 -or [double]::IsNaN($Tolerance) -or [double]::IsInfinity($Tolerance)){throw 'Two 3D segments and finite positive tolerance required'}
 foreach($point in @($A)+@($B)){if($point.Count-ne 3){throw '3D point required'};foreach($value in $point){if($null-eq $value -or [double]::IsNaN([double]$value) -or [double]::IsInfinity([double]$value)){throw 'Finite coordinate required'}}}
 function OnSegment($p,$s){
  $d=@(0..2|ForEach-Object {[double]$s[1][$_]-[double]$s[0][$_]})
  $l2=0.;$dot=0.;for($i=0;$i-lt 3;$i++){$l2+=$d[$i]*$d[$i];$dot+=([double]$p[$i]-[double]$s[0][$i])*$d[$i]}
  if($l2-le ($Tolerance*$Tolerance)){return $null};$t=$dot/$l2
  if($t-lt 0 -or $t-gt 1){return $null}
  $dist2=0.;for($i=0;$i-lt 3;$i++){$e=[double]$p[$i]-([double]$s[0][$i]+$t*$d[$i]);$dist2+=$e*$e}
  if($dist2-gt ($Tolerance*$Tolerance)){return $null}
  return $t
 }
 if(@($BulgesA+$BulgesB|Where-Object {$_-ne 0}).Count){
  $hits=@()
  for($i=0;$i-lt 2;$i++){for($j=0;$j-lt 2;$j++){$d2=0.;for($k=0;$k-lt 3;$k++){$d2+=[math]::Pow($A[$i][$k]-$B[$j][$k],2)};if($d2-le $Tolerance*$Tolerance){$hits+=,[pscustomobject]@{point=@($A[$i]);endpointA=$i;endpointB=$j}}}}
  if(!@($BulgesB|Where-Object {$_-ne 0}).Count){for($i=0;$i-lt 2;$i++){$t=OnSegment $A[$i] $B;if($null-ne $t -and $t-gt 0 -and $t-lt 1){$hits+=,[pscustomobject]@{point=@($A[$i]);endpointA=$i;endpointB=-1}}}}
  if(!@($BulgesA|Where-Object {$_-ne 0}).Count){for($i=0;$i-lt 2;$i++){$t=OnSegment $B[$i] $A;if($null-ne $t -and $t-gt 0 -and $t-lt 1){$hits+=,[pscustomobject]@{point=@($B[$i]);endpointA=-1;endpointB=$i}}}}
  $type=if(@($hits|Where-Object {$_.endpointA-lt 0 -or $_.endpointB-lt 0}).Count){'endpoint_on_segment'}elseif($hits.Count){'endpoint_coincidence'}else{'unresolved_curve_relation'}
  return [pscustomobject]@{geometryType=$type;contacts=$hits;tolerance=$Tolerance;coordinateFrame='WCS';portMeaning='unresolved';eligibleContact=($hits.Count-gt 0);curveHandling='curve endpoints only; straight segment interior permitted; no chord substitution'}
 }
 $contacts=@()
 for($i=0;$i-lt 2;$i++){
  $t=OnSegment $A[$i] $B
  if($null-ne $t){$contacts+=,[pscustomobject]@{point=@($A[$i]);endpointA=$i;endpointB=if($t-eq 0){0}elseif($t-eq 1){1}else{-1}}}
  $t=OnSegment $B[$i] $A
  if($null-ne $t){$contacts+=,[pscustomobject]@{point=@($B[$i]);endpointA=if($t-eq 0){0}elseif($t-eq 1){1}else{-1};endpointB=$i}}
 }
 $distinct=@($contacts|Group-Object {$_.point -join ','}|ForEach-Object {$_.Group[0]})
 if($distinct.Count-ge 2){$type='collinear_overlap'}
 elseif($distinct.Count){$type=if($distinct[0].endpointA-ge 0 -and $distinct[0].endpointB-ge 0){'endpoint_coincidence'}else{'endpoint_on_segment'}}
 else{
  $type='separate'
  $ax=[double]$A[1][0]-[double]$A[0][0];$ay=[double]$A[1][1]-[double]$A[0][1]
  $bx=[double]$B[1][0]-[double]$B[0][0];$by=[double]$B[1][1]-[double]$B[0][1]
  $det=$ax*$by-$ay*$bx
  if([math]::Abs($det)-gt 1e-12){
   $qx=[double]$B[0][0]-[double]$A[0][0];$qy=[double]$B[0][1]-[double]$A[0][1]
   $t=($qx*$by-$qy*$bx)/$det;$u=($qx*$ay-$qy*$ax)/$det
   if($t-gt 0 -and $t-lt 1 -and $u-gt 0 -and $u-lt 1){
    $za=[double]$A[0][2]+$t*([double]$A[1][2]-[double]$A[0][2]);$zb=[double]$B[0][2]+$u*([double]$B[1][2]-[double]$B[0][2])
    if([math]::Abs($za-$zb)-le $Tolerance){$type='segment_crossing';$distinct=@([pscustomobject]@{point=@(([double]$A[0][0]+$t*$ax),([double]$A[0][1]+$t*$ay),$za);endpointA=-1;endpointB=-1})}
   }
  }
 }
 [pscustomobject]@{geometryType=$type;contacts=$distinct;tolerance=$Tolerance;coordinateFrame='WCS';portMeaning='unresolved';eligibleContact=($type-in @('endpoint_coincidence','endpoint_on_segment'))}
}

function ConvertTo-LocalLogicalNetworkCandidates {
 param([Parameter(Mandatory)]$Bundle)
 $b=$Bundle
 function Trace($ids){
  if(!@($ids).Count){throw 'Missing evidence references'}
  foreach($id in $ids){if(!$id){throw 'Empty evidence reference'};$p=$b.references.PSObject.Properties[$id];if(!$p -or !$p.Value.resolved -or !$p.Value.sourceSnapshot -or !$p.Value.sourceDocument -or !$p.Value.handle){throw "Unresolved evidence reference: $id"}}
 }
 Trace @($b.sourceRegion.reference)
 $networks=@();$reviews=@($b.reviewItems|ForEach-Object {$_|ConvertTo-Json -Depth 40|ConvertFrom-Json})
 foreach($spec in $b.networks){
  $scope=New-SystemScope $b.projectId (New-SystemIdentity $spec.system)
  $id=$b.sampleId+':'+$spec.system
  $checked=New-LogicalNetwork $id $scope
  Trace $spec.evidenceRefs
  $nodes=@();$edges=@();$lookup=@{}
  foreach($n in $spec.nodes){
   if($n.systemIdentity-cne $spec.system){throw 'Node system mismatch'};Trace @($n.representationRef);Trace $n.evidenceRefs
   if($b.references.($n.representationRef).sourceSnapshot-cne $b.sourceRegion.sourceSnapshot){throw 'Node representation outside source snapshot'}
   $nodeId=$id+':'+$n.representationRef
   $checked=Add-LogicalNetworkElement $checked (New-NetworkElement NodeCandidate $nodeId LogicalNetwork $n.evidenceRefs -SystemScope $scope)
   if($lookup.ContainsKey($n.representationRef)){throw 'Duplicate representation in one network'};$lookup[$n.representationRef]=$nodeId
   $nodes+=,[pscustomobject]@{modelType='LogicalNodeCandidate';nodeId=$nodeId;systemIdentity=$scope.systemIdentity;systemScope=$scope;representationRef=$n.representationRef;nodeKind=$n.nodeKind;roleCandidate=$n.roleCandidate;roleStatus=$n.roleStatus;scopeBasis=$n.scopeBasis;evidenceRefs=@($n.evidenceRefs);status='candidate';portRole='unresolved';loopIdentity='unresolved';addressIdentity='unresolved';controllerMembership='unresolved'}
  }
  $gaps=@();$boundaries=@()
  foreach($gap in $spec.gaps){
   Trace @($gap.fromRef,$gap.toRef,$gap.probableBoundaryObject)
   if(!$lookup.ContainsKey($gap.fromRef) -or !$lookup.ContainsKey($gap.toRef)){throw 'Gap endpoints outside network'}
   $gapId=$id+':gap:'+($gaps.Count+1)
   $gaps+=,[pscustomobject]@{modelType='NetworkGapCandidate';gapId=$gapId;systemIdentity=$scope.systemIdentity;fromNode=$lookup[$gap.fromRef];toNode=$lookup[$gap.toRef];fromPoint=$gap.fromPoint;toPoint=$gap.toPoint;separationDrawingUnits=$gap.separationDrawingUnits;probableBoundaryObject=$gap.probableBoundaryObject;gapReason=$gap.reason;reasonStatus='candidate';status='unresolved';bridgeAllowed=$false;evidenceRefs=@($gap.fromRef,$gap.toRef,$gap.probableBoundaryObject)}
   $boundaries+=,[pscustomobject]@{modelType='NetworkBoundaryCandidate';boundaryId=$gapId+':boundary';systemIdentity=$scope.systemIdentity;boundaryType='unread_interface';representationRef=$gap.probableBoundaryObject;gapRef=$gapId;status='unresolved';evidenceRefs=@($gap.probableBoundaryObject)}
   $item=$gaps[-1]
   foreach($entry in @{originalGapDistance=$gap.separationDrawingUnits;boundaryObjectRef=$gap.probableBoundaryObject;leftRepresentationRef=$gap.fromRef;rightRepresentationRef=$gap.toRef;leftBoundaryContact=$null;rightBoundaryContact=$null;boundaryRelationStatus='unresolved';internalContinuityStatus='unresolved';terminalNumber='unresolved';portRole='unresolved';direction='unresolved';physicalConnection='unresolved'}.GetEnumerator()){$item|Add-Member $entry.Key $entry.Value}
   if($gap.boundaryEvidence){
    $proof=$gap.boundaryEvidence
    if(!$proof.definitionRead -or $proof.objectRef-cne $gap.probableBoundaryObject){throw 'Boundary proof instance mismatch'}
    Trace $proof.evidenceRefs;Trace $proof.instanceAttributeRefs
    $left=Get-GapBoundaryContact $gap.fromPoint $proof
    $right=Get-GapBoundaryContact $gap.toPoint $proof
    $both=($left.status-eq 'supported_candidate' -and $right.status-eq 'supported_candidate')
    $item.leftBoundaryContact=$left;$item.rightBoundaryContact=$right
    $item.gapReason='internal_terminal_mapping_not_represented'
    $item|Add-Member missingEvidence @('internal_terminal_mapping_not_represented','internal_continuity_not_represented','port_semantics')
    $item.boundaryRelationStatus=if($both){'supported_candidate'}else{'partial'}
    $item|Add-Member boundaryRelation $(if($both -and $proof.roleCandidate-eq 'terminal_box'){'probable terminal-box boundary relation'}else{'incomplete boundary relation'})
    $item|Add-Member representationContact $(if($both){'supported_candidate'}else{'partial'})
    $item|Add-Member boundaryGeometryEvidence $proof
    $item.evidenceRefs+=@($proof.evidenceRefs)+@($proof.instanceAttributeRefs)
    $boundaries[-1].boundaryType='terminal_box_boundary_candidate'
    $boundaries[-1].status=$item.boundaryRelationStatus
    $boundaries[-1].evidenceRefs=$item.evidenceRefs
    $boundaries[-1]|Add-Member roleCandidate $proof.roleCandidate
    $boundaries[-1]|Add-Member internalContinuityStatus 'unresolved'
   }
  }
  $excluded=@($spec.excludedRelations)
  foreach($rel in $spec.relations){
   if($rel.systemIdentity-cne $spec.system){throw 'Edge system mismatch'}
   if(!$lookup.ContainsKey($rel.fromRef) -or !$lookup.ContainsKey($rel.toRef) -or $rel.fromRef-ceq $rel.toRef){throw 'Two distinct edge endpoints required within local network'}
   Trace $rel.evidenceRefs
   $bridgesGap=@($gaps|Where-Object {($_.fromNode-eq $lookup[$rel.fromRef] -and $_.toNode-eq $lookup[$rel.toRef])-or ($_.toNode-eq $lookup[$rel.fromRef] -and $_.fromNode-eq $lookup[$rel.toRef])}).Count-gt 0
   $eligible=($rel.geometryStatus-eq 'supported' -and $rel.semanticStatus-eq 'supported_candidate' -and $rel.geometryType-in @('endpoint_coincidence','endpoint_on_segment','boundary_contact','boundary_crossing') -and !$bridgesGap)
   if(!$eligible){$excluded+=,[pscustomobject]@{representationRefs=@($rel.fromRef,$rel.toRef);geometryType=$rel.geometryType;reason=if($bridgesGap){'gap_cannot_be_bridged'}else{'geometry_or_semantic_support_insufficient'};evidenceRefs=$rel.evidenceRefs};continue}
   $edgeId=$id+':edge:'+($edges.Count+1)
   $checked=Add-LogicalNetworkElement $checked (New-NetworkElement EdgeCandidate $edgeId LogicalNetwork $rel.evidenceRefs -SystemScope $scope -EndpointRefs @($lookup[$rel.fromRef],$lookup[$rel.toRef]))
   $edges+=,[pscustomobject]@{modelType='LogicalEdgeCandidate';edgeId=$edgeId;fromNode=$lookup[$rel.fromRef];toNode=$lookup[$rel.toRef];representationRefs=@($rel.fromRef,$rel.toRef);systemIdentity=$scope.systemIdentity;systemScope=$scope;relationType=$rel.relationType;geometryStatus=$rel.geometryStatus;geometryType=$rel.geometryType;geometryEvidence=$rel.geometryEvidence;semanticStatus=$rel.semanticStatus;admissionStatus='candidate_only';blockingReasons=@('port_semantics_unresolved','physical_connection_unresolved','actual_network_membership_unresolved','signal_direction_unresolved');evidenceRefs=@($rel.evidenceRefs);status='candidate';direction='unresolved';portRole='unresolved';physicalConnection='unresolved';formalNetworkAdmission='blocked';routingAdmission='blocked'}
  }
  foreach($boundary in $spec.regionBoundaries){Trace @($boundary.representationRef);$boundaries+=,[pscustomobject]@{modelType='NetworkBoundaryCandidate';boundaryId=$id+':window:'+($boundaries.Count+1);systemIdentity=$scope.systemIdentity;boundaryType='investigation_window_exit';representationRef=$boundary.representationRef;point=$boundary.point;status='unresolved';evidenceRefs=@($boundary.representationRef);meaning='window limit, not engineering boundary'}}
  $open=@($spec.openEnds|ForEach-Object {$_|ConvertTo-Json -Depth 30|ConvertFrom-Json})
  $unresolvedRoles=@($nodes|Where-Object {$_.roleStatus-eq 'unresolved' -or $_.roleCandidate-eq 'unknown'}|ForEach-Object nodeId)
  $networks+=,[pscustomobject]@{modelType='LocalLogicalNetworkCandidate';networkId=$id;systemIdentity=$scope.systemIdentity;systemScope=$scope;sourceRegion=$b.sourceRegion;evidenceRefs=@($spec.evidenceRefs);networkStatus='candidate';completenessStatus=if($gaps.Count -or $open.Count -or $boundaries.Count){'partial'}elseif($edges.Count){'locally_supported'}else{'unresolved'};nodes=$nodes;edges=$edges;gaps=$gaps;boundaries=$boundaries;openEnds=$open;excludedRelations=$excluded;unresolvedEndpointAssociations=@($spec.unresolvedEndpointAssociations);unresolvedRoles=$unresolvedRoles;crossSystemInterfaceRefs=@();missingInformation=@('loop_identity','address_identity','controller_membership','port_semantics','upstream_downstream_continuation');upstreamSourceCandidate=$b.upstreamSourceCandidate;isActualNetwork=$false;automaticRoutingEnabled=$false}
 }
 if(@($networks.systemIdentity.systemType|Select-Object -Unique).Count-ne $networks.Count){throw 'Duplicate system inventory; explicit separation required'}
 $crosses=@()
 foreach($cross in $b.crossSystems){
  Trace $cross.evidenceRefs
  if($cross.systems.Count-ne 2 -or $cross.systems[0]-ceq $cross.systems[1]){throw 'Cross-system interface requires two distinct systems'}
  $ends=@()
  foreach($type in $cross.systems){
   $matches=@($networks|Where-Object {$_.systemIdentity.systemType-ceq $type})
   if($matches.Count-ne 1){throw 'Cross-system endpoint network absent'}
   $node=@($matches[0].nodes|Where-Object representationRef -CEQ $cross.representationRef)
   if($node.Count-ne 1){throw 'Cross-system representation absent'}
   $ends+=,[pscustomobject]@{networkRef=$matches[0].networkId;nodeRef=$node[0].nodeId;systemIdentity=$matches[0].systemIdentity}
  }
  $crossId=$b.sampleId+':cross:'+($crosses.Count+1)
  $crosses+=,[pscustomobject]@{modelType='CrossSystemAssociationCandidate';associationId=$crossId;representationRef=$cross.representationRef;endpoints=$ends;evidenceRefs=$cross.evidenceRefs;status='supported_candidate';meaning='two system interface expressions only';networkMergeAllowed=$false;direction='unresolved';portMapping='unresolved';internalConduction='unresolved';controlLogic='unresolved';physicalConnection='unresolved'}
  foreach($net in $networks|Where-Object {$_.networkId-in $ends.networkRef}){$net.crossSystemInterfaceRefs+=@($crossId)}
 }
 $supports=@()
 foreach($req in $b.requirements){
  $matches=@($networks|Where-Object {$_.systemIdentity.systemType-ceq $req.systemIdentity})
  if($req.projectId-cne $b.projectId -or $req.sourceRegionRef-cne $b.sourceRegion.reference -or $matches.Count-ne 1 -or !$matches[0].edges.Count){continue}
  $supports+=,[pscustomobject]@{modelType='RequirementSupportCandidate';requirementRef=$req.requirementId;networkCandidateRef=$matches[0].networkId;systemIdentity=$matches[0].systemIdentity;evidenceRefs=$matches[0].evidenceRefs;supportTypes=@('indicates_relation','narrows_search','indicates_missing_parameter');status='supported_candidate';canSatisfyRequirement=$false}
 }
 foreach($net in $networks){
  foreach($gap in $net.gaps){$reviews+=,[pscustomobject]@{modelType='ReviewItem';reviewId=$gap.gapId+':review';type='network_gap';status='open';sourceRefs=$gap.evidenceRefs;networkRef=$net.networkId;missingEvidence=if($gap.missingEvidence){$gap.missingEvidence}else{@($gap.gapReason,'port_semantics')}}}
  $reviews+=,[pscustomobject]@{modelType='ReviewItem';reviewId=$net.networkId+':membership';type='local_network_membership_unresolved';status='open';sourceRefs=$net.evidenceRefs;missingEvidence=$net.missingInformation}
 }
 $summary=@($networks|ForEach-Object {[pscustomobject]@{system=$_.systemIdentity.systemType;nodes=$_.nodes.Count;edges=$_.edges.Count;gaps=$_.gaps.Count;boundarySupportedGaps=@($_.gaps|Where-Object boundaryRelationStatus -EQ supported_candidate).Count;unresolvedPureGaps=@($_.gaps|Where-Object boundaryRelationStatus -EQ unresolved).Count;partialBoundaryGaps=@($_.gaps|Where-Object boundaryRelationStatus -EQ partial).Count;openEnds=$_.openEnds.Count;interfaces=$_.crossSystemInterfaceRefs.Count;unresolvedRoles=$_.unresolvedRoles.Count;unresolvedDeviceRelations=$_.unresolvedEndpointAssociations.Count;completeness=$_.completenessStatus}})
 [pscustomobject]@{modelType='LocalLogicalNetworkInventory';version='experimental-1.1';sourceRegion=$b.sourceRegion;networks=$networks;crossSystemAssociations=$crosses;sourceReferences=$b.references;requirements=@($b.requirements|ForEach-Object {$_|ConvertTo-Json -Depth 40|ConvertFrom-Json});requirementSupports=$supports;reviewItems=$reviews;summary=$summary;capabilityCoverage=@($b.capabilityCoverage);actualNetworks=@();routing=@();physicalConnections=@();circuits=@();quantities=@()}
}
Export-ModuleMember -Function Get-LocalSegmentRelation,ConvertTo-LocalLogicalNetworkCandidates
