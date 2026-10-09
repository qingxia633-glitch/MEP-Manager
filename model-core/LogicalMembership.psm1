# Compose existing reviewed logical relations and spatial sets. No geometry inference.
function Join-LogicalNetworkMembership {
 param([Parameter(Mandatory)]$Network,[Parameter(Mandatory)][string]$CompartmentRef,
       [Parameter(Mandatory)][string]$RegionRef,[object[]]$Mappings=@(),[object[]]$ReviewItems=@())
 if($Network.systemIdentity.systemType -ne 'fire_alarm' -or $Network.sourceRegion.reference -cne $RegionRef){throw 'Explicit alarm region required'}
 $n=$Network|ConvertTo-Json -Depth 90|ConvertFrom-Json
 $nodes=@($n.nodes);$edges=@($n.edges);$members=@();$reviews=@($ReviewItems|ForEach-Object {$_|ConvertTo-Json -Depth 60|ConvertFrom-Json});$coverage=@();$seen=@{}
 foreach($node in $nodes){$node.nodeKind=if($node.nodeKind -eq 'device_category_candidate'){'category_node'}else{'representation_node'}}
 foreach($e in $edges){
  if($e.systemIdentity.systemType -ne 'fire_alarm' -or $e.geometryStatus -ne 'supported' -or $e.semanticStatus -ne 'supported_candidate' -or $e.geometryType -notin @('endpoint_coincidence','endpoint_on_segment','boundary_contact','boundary_crossing') -or !$e.evidenceRefs.Count -or $e.routingAdmission -ne 'blocked'){throw 'Unadmitted logical edge'}
  $e|Add-Member relationStatus 'supported';$e|Add-Member isPhysicalConnection $false
 }
 # Existing layout associations remain unresolved; do not turn them into admitted edges.
 foreach($u in $n.unresolvedEndpointAssociations){
  $reviews+=,[pscustomobject]@{type='branch_target_unresolved';status='open';sourceRefs=$u.evidenceRefs}
 }
 foreach($m in $Mappings){
  if($m.systemIdentity -cne 'fire_alarm' -or $m.compartmentRef -cne $CompartmentRef){throw 'Membership system or compartment mismatch'}
  $cat=@($nodes|Where-Object representationRef -CEQ $m.systemCategoryNodeRef)
  if($cat.Count -ne 1 -or $cat[0].nodeKind -ne 'category_node'){throw 'Category reference must resolve to this network'}
  if($seen.ContainsKey($m.systemCategoryNodeRef)){throw 'Duplicate category mapping'};$seen[$m.systemCategoryNodeRef]=$true
  $reviews+=@($m.reviewItems)
  $count=0;$memberSeen=@{}
  if($m.membershipStatus -in @('supported','partial') -and $m.polygonRef -and $m.coordinateTransformRef){
   foreach($tier in @('membersExplicit','membersInherited','membersPartial')){foreach($ref in $m.$tier){
    if(!$ref -or $memberSeen.ContainsKey($ref)){throw 'Duplicate or empty member reference'};$memberSeen[$ref]=$true
    $a=@($m.assessments|Where-Object instanceRef -CEQ $ref)
    $expected=if($tier -eq 'membersInherited'){'inherited_candidate'}else{'explicit'}
    if($a.Count -ne 1 -or $a[0].classification -ne 'inside' -or !$a[0].roleRef -or $a[0].confirmedRole -or $a[0].roleStatus -notin @('explicit','inherited_candidate') -or ($tier -ne 'membersPartial' -and $a[0].roleStatus -ne $expected)){throw 'Inconsistent source membership evidence'}
    if($ref -in @($m.outside)+@($m.onBoundary)+@($m.unresolved)){throw 'Conflicting spatial disposition'}
    $id=$n.networkId+':instance:'+ $ref
    if(!@($nodes|Where-Object nodeId -CEQ $id).Count){$nodes+=,[pscustomobject]@{modelType='LogicalNodeCandidate';nodeId=$id;nodeKind='instance_node';representationRef=$ref;systemIdentity=$n.systemIdentity;roleStatus=$a[0].roleStatus;evidenceRefs=@($ref,$a[0].roleRef,$m.polygonRef,$m.coordinateTransformRef);status='candidate';confirmed=$false;portRole='unresolved'}}
    $members+=,[pscustomobject]@{modelType='NetworkMembershipCandidate';systemIdentity=$n.systemIdentity;membershipId=$id+':'+$cat[0].nodeId;categoryNodeRef=$cat[0].nodeId;instanceNodeRef=$id;instanceRef=$ref;sourceMappingRef=$m.systemCategoryNodeRef;polygonRef=$m.polygonRef;coordinateTransformRef=$m.coordinateTransformRef;roleEvidenceRef=$a[0].roleRef;roleStatus=$a[0].roleStatus;membershipTier=$tier;status='partial';actualNetworkMembership='unresolved';confirmed=$false;physicalConnection='unresolved';routingAdmission='blocked'}
    $count++
   }}
  }
  $coverage+=,[pscustomobject]@{categoryRef=$m.systemCategoryNodeRef;role=$m.roleCandidate;members=$count;explicit=@($members|Where-Object {$_.sourceMappingRef -eq $m.systemCategoryNodeRef -and $_.membershipTier -eq 'membersExplicit'}).Count;inherited=@($members|Where-Object {$_.sourceMappingRef -eq $m.systemCategoryNodeRef -and $_.membershipTier -eq 'membersInherited'}).Count;quantityConsistency=$m.quantityConsistencyStatus;quantityDelta=$m.quantityDelta;completenessStatus=$m.completenessStatus}
  $reviews+=,[pscustomobject]@{type='category_instance_binding_partial';status='open';sourceRefs=@($m.systemCategoryNodeRef,$m.polygonRef)}
 }
 foreach($g in $n.gaps){if($g.bridgeAllowed){throw 'Gap bridging prohibited'};$reviews+=,[pscustomobject]@{type=$(if($g.boundaryRelationStatus -eq 'supported_candidate'){'terminal_box_internal_unknown'}else{'network_gap'});status='open';sourceRefs=$g.evidenceRefs}}
 $reviews+=,[pscustomobject]@{type='network_membership_unresolved';status='open';sourceRefs=$n.evidenceRefs}
 if($n.crossSystemInterfaceRefs.Count){$reviews+=,[pscustomobject]@{type='cross_system_boundary';status='open';sourceRefs=$n.crossSystemInterfaceRefs}}
 $connected=@($edges.fromNode)+@($edges.toNode)
 [pscustomobject]@{modelType='LogicalNetworkCandidate';networkId=$n.networkId;systemIdentity=$n.systemIdentity;sourceRegion=$n.sourceRegion;compartmentRef=$CompartmentRef;nodes=$nodes;edges=$edges;memberships=$members;gaps=$n.gaps;boundaries=$n.boundaries;openEnds=$n.openEnds;unresolvedRelations=$n.unresolvedEndpointAssociations;excludedRelations=$n.excludedRelations;crossSystemInterfaceRefs=$n.crossSystemInterfaceRefs;reviewItems=$reviews;categoryMembershipCoverage=$coverage;knownNodes=$nodes.Count;knownEdges=$edges.Count;partialEdges=0;unresolvedEdges=@($n.unresolvedEndpointAssociations).Count;isolatedCandidates=@($nodes|Where-Object {$_.nodeId -notin $connected}|ForEach-Object nodeId);networkCompletenessStatus='useful_but_partial';actualNetwork=$false;routingEdges=@();circuits=@();quantities=@();formalBinding=$false}
}
Export-ModuleMember -Function Join-LogicalNetworkMembership
