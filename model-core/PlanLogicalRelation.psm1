function New-PlanLogicalRelation {
 param([string]$Type,[string]$Level)
 if($Level -notin @('category_to_instance_membership','instance_to_routing_attachment','routed_instance_pair','instance_set_to_routing_subgraph','system_branch_to_plan_relation','system_only_relation')){throw 'Unsupported relation level'}
 if($Type -notin @('category_attachment_candidate','routed_device_pair_candidate','instance_set_to_routing_subgraph','system_branch_to_plan_relation','system_only_relation')){throw 'Control semantics not admitted'}
 [pscustomobject]@{modelType='PlanLogicalRelationCandidate';sourceSystemLogicalRef=$null;logicalCategoryRef=@();sourcePlanInstanceRefs=@();targetPlanInstanceRefs=@();sourceInstanceSetRef=$null;targetInstanceSetRef=$null;routingComponentRefs=@();routingEdgeRefs=@();relationType=$Type;relationLevel=$Level;logicalRelationStatus='unresolved';geometryStatus='no_candidate';correspondenceStatus='unresolved';membershipStatus='unresolved';systemBranchIdentity='unresolved';evidenceRefs=@();reviewItemRefs=@();control='unresolved';signalDirection='unresolved';causeEffect='unresolved';circuitSequence='unresolved';physicalConnection='unresolved'}
}
function Join-PlanLogicalRelation {
 param($Logical,$Routing,$Correspondence,$Selection,[string]$RoutingArtifactRef)
 if($Logical.systemIdentity.systemType -ne 'fire_alarm' -or $Routing.systemScope -ne 'fire_alarm' -or $Logical.compartmentRef -cne $Routing.compartmentRef -or $Correspondence.compartmentRef -cne $Routing.compartmentRef){throw 'System or compartment incompatible'}
 if(!$RoutingArtifactRef){throw 'Routing artifact namespace required'}
 $relations=@();$reviews=@()
 function Qualified($id){$RoutingArtifactRef+'#'+$id}
 function Hits($instance,$rawRef){@($Correspondence.correspondences|Where-Object {$_.deviceRef -ceq $instance -and $_.geometryStatus -eq 'supported_candidate'}|Where-Object {
  $h=$_;$e=@($Routing.edges|Where-Object {$_.edgeId -ceq $h.routingRef -and $_.rawEntityRef -ceq $rawRef -and $_.systemScope -eq 'fire_alarm'})
  $contact=@($Correspondence.endpointContacts|Where-Object {$_.deviceRef -ceq $instance -and $_.edgeRef -ceq $h.routingRef -and $_.attachmentRef -ceq $h.attachmentRef -and $_.status -eq 'supported_candidate' -and $_.relationType -in @('endpoint_on_boundary','endpoint_inside_representation')})
  $member=@($Logical.memberships|Where-Object {$_.instanceRef -ceq $instance -and $_.categoryNodeRef -ceq $h.categoryRef -and $_.systemIdentity.systemType -eq 'fire_alarm'})
  $e.Count -eq 1 -and $contact.Count -gt 0 -and $member.Count -eq 1
 })}
 foreach($s in $Selection){
  if($s.kind -eq 'category_attachment'){
   $m=@($Logical.memberships|Where-Object {$_.instanceRef -ceq $s.instanceRef -and $_.categoryNodeRef -ceq $s.categoryRef -and $_.systemIdentity.systemType -eq 'fire_alarm'})
   $x=New-PlanLogicalRelation 'category_attachment_candidate' 'instance_to_routing_attachment'
   $x.logicalCategoryRef=@($s.categoryRef);$x.sourcePlanInstanceRefs=@($s.instanceRef)
   $hits=@(Hits $s.instanceRef $s.rawRoutingRef)
   if($m.Count -eq 1){$x.membershipStatus=$m[0].status;$x.sourceInstanceSetRef=$m[0].sourceMappingRef;$x.evidenceRefs+=@($m[0].membershipId,$m[0].roleEvidenceRef)}else{$hits=@()}
   if($hits.Count){$x.geometryStatus='supported';$x.correspondenceStatus='partial'}
   $x.routingEdgeRefs=@($hits.routingRef|Sort-Object -Unique|ForEach-Object {Qualified $_});$x.routingComponentRefs=@($hits.componentRef|Sort-Object -Unique|ForEach-Object {Qualified $_});$x.evidenceRefs+=@($hits.attachmentRef)
   $x.reviewItemRefs=@('plan_logical_relation_unresolved','system_branch_plan_target_unresolved');$relations+=,$x
   # One selected category set; no instance-to-instance relation expansion.
   $set=New-PlanLogicalRelation 'instance_set_to_routing_subgraph' 'instance_set_to_routing_subgraph'
   $set.modelType='InstanceSetToRoutingSubgraphCandidate';$set.logicalCategoryRef=@($s.categoryRef);$set.sourceInstanceSetRef=$x.sourceInstanceSetRef
   $set.sourcePlanInstanceRefs=@($Logical.memberships|Where-Object {$_.categoryNodeRef -ceq $s.categoryRef -and $_.systemIdentity.systemType -eq 'fire_alarm'}|ForEach-Object instanceRef)
   $cs=@($Correspondence.correspondences|Where-Object {$_.categoryRef -ceq $s.categoryRef -and $_.deviceRef -cin $set.sourcePlanInstanceRefs -and $_.geometryStatus -eq 'supported_candidate'}|Where-Object {
    $c=$_;$edge=@($Routing.edges|Where-Object edgeId -ceq $c.routingRef)
    $edge.Count -eq 1 -and @(Hits $c.deviceRef $edge[0].rawEntityRef|Where-Object attachmentRef -ceq $c.attachmentRef).Count -gt 0
   })
   $set.routingEdgeRefs=@($cs.routingRef|Sort-Object -Unique|ForEach-Object {Qualified $_});$set.routingComponentRefs=@($cs.componentRef|Sort-Object -Unique|ForEach-Object {Qualified $_})
   $set.geometryStatus=if($cs.Count){'partial'}else{'no_candidate'};$set.correspondenceStatus=if($cs.Count){'partial'}else{'unresolved'};$set.membershipStatus='partial';$set.evidenceRefs=@($cs.attachmentRef)+@($cs.membershipRef|Sort-Object -Unique);$set.reviewItemRefs=@('category_subgraph_correspondence_partial');$relations+=,$set
  }elseif($s.kind -eq 'routed_pair'){
   $x=New-PlanLogicalRelation 'routed_device_pair_candidate' 'routed_instance_pair'
   $x.sourcePlanInstanceRefs=@($s.instanceA);$x.targetPlanInstanceRefs=@($s.instanceB)
   $a=@(Hits $s.instanceA $s.rawRoutingRef);$b=@(Hits $s.instanceB $s.rawRoutingRef)
   $pairs=@(foreach($ha in $a){foreach($hb in $b){if($ha.routingRef -ceq $hb.routingRef -and $s.instanceA -cne $s.instanceB){
    $ca=@($Correspondence.endpointContacts|Where-Object attachmentRef -ceq $ha.attachmentRef)[0];$cb=@($Correspondence.endpointContacts|Where-Object attachmentRef -ceq $hb.attachmentRef)[0]
    if($ca.endpointRef -cne $cb.endpointRef){$ha;$hb}
   }}})
   if($pairs.Count){$x.geometryStatus='supported';$x.correspondenceStatus='partial'}
   $x.logicalCategoryRef=@($pairs.categoryRef|Sort-Object -Unique);$x.routingEdgeRefs=@($pairs.routingRef|Sort-Object -Unique|ForEach-Object {Qualified $_});$x.routingComponentRefs=@($pairs.componentRef|Sort-Object -Unique|ForEach-Object {Qualified $_});$x.evidenceRefs=@($pairs.attachmentRef)+@($pairs.membershipRef);$x.reviewItemRefs=@('routed_pair_without_logical_semantics','plan_logical_relation_unresolved');$relations+=,$x
  }else{throw 'Unknown fixture selection kind'}
 }
 foreach($e in $Logical.edges){
  $type=if($e.relationType -eq 'line_to_line'){'system_only_relation'}elseif($e.relationType -in @('branch_to_bus','line_to_device_representation')){'system_branch_to_plan_relation'}else{throw 'Unreviewed system relation type'}
  $x=New-PlanLogicalRelation $type $type;$x.sourceSystemLogicalRef=$e.edgeId;$x.evidenceRefs=@($e.evidenceRefs)
  if($type -eq 'system_only_relation'){$x.geometryStatus='not_applicable';$x.correspondenceStatus='system_diagram_only';$x.reviewItemRefs=@()}else{$x.reviewItemRefs=@('system_branch_plan_target_unresolved','system_relation_without_plan_geometry')}
  $relations+=,$x
 }
 foreach($x in $relations){foreach($t in $x.reviewItemRefs){$reviews+=,[pscustomobject]@{type=$t;status='open';sourceRefs=@($x.sourceSystemLogicalRef)+@($x.evidenceRefs)}}}
 [pscustomobject]@{modelType='PlanLogicalRelationAudit';relations=$relations;reviewItems=$reviews;upstreamReviewItems=$Logical.reviewItems;createdSystemEdges=@();createdRoutingEdges=@();requirementsModified=$false;bridgeAllowed=$false}
}
Export-ModuleMember -Function New-PlanLogicalRelation,Join-PlanLogicalRelation
