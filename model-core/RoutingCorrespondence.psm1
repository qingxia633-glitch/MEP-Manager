function Join-RoutingCorrespondence {
 param($Routing,$Logical,$Attachment,[object[]]$TerminationEvidence=@())
 if($Routing.systemScope -ne 'fire_alarm' -or $Logical.systemIdentity.systemType -ne 'fire_alarm' -or $Routing.compartmentRef -cne $Logical.compartmentRef){throw 'System/compartment scope mismatch'}
 if($Attachment.sourceSnapshot -cne $Routing.sourceSnapshot){throw 'Attachment drawing mismatch'}
 $components=@{}; $edges=@{}; $geometry=@{}; $members=@{}
 foreach($c in $Routing.components){foreach($e in $c.edgeRefs){$components[$e]=$c.componentId}}
 foreach($e in $Routing.edges){$edges[$e.edgeId]=$e}
 foreach($g in $Attachment.geometry){if($g.geometryStatus -eq 'supported_candidate'){$geometry[$g.instanceRef]=$g}}
 foreach($m in $Logical.memberships){if($m.systemIdentity.systemType -eq 'fire_alarm'){$members[$m.instanceRef]=$m}}
 $contacts=@();$reviews=@();$correspondences=@();$aggregates=@();$continuations=@();$terminations=@();$edgeResults=@()
 foreach($r in $Attachment.relations){
  if(!$r.attachmentAllowed -or $r.status -ne 'supported_candidate' -or $r.relationType -notin @('endpoint_on_boundary','endpoint_inside_representation') -or !$geometry.ContainsKey($r.deviceInstanceRef) -or !$edges.ContainsKey($r.routingEdgeRef)){continue}
  $e=$edges[$r.routingEdgeRef];if($e.systemScope -ne 'fire_alarm'){continue};if($r.rawRoutingRef -cne $e.rawEntityRef){throw 'Raw routing evidence mismatch'}
  for($i=0;$i -lt 2;$i++){
   if($r.endpointTypes[$i] -notin @('endpoint_on_boundary','endpoint_inside_representation')){continue}
   $node=@($e.fromNode,$e.toNode)[$i]
   if($r.routingEndpointRef[$i] -cne $node){throw 'Endpoint reference mismatch'}
   $contacts+=,[pscustomobject]@{deviceRef=$r.deviceInstanceRef;endpointRef=$node;edgeRef=$e.edgeId;componentRef=$components[$e.edgeId];relationType=$r.endpointTypes[$i];status='supported_candidate';evidenceRefs=@($r.evidenceRefs);attachmentRef=($r.deviceInstanceRef+'|'+$e.edgeId+'|'+$node)}
  }
 }
 foreach($o in $Routing.openEndpoints){
  $hits=@($contacts|Where-Object endpointRef -CEQ $o.nodeRef)
  $type=if($hits.Count){'device_terminated_candidate'}else{'unresolved'}
  $support=@($TerminationEvidence|Where-Object {$_.endpointRef -ceq $o.nodeRef -and $_.sourceSnapshot -ceq $Routing.sourceSnapshot -and $_.systemScope -eq 'fire_alarm' -and $_.status -eq 'supported_candidate' -and $_.evidenceRefs.Count -gt 0 -and $_.terminationType -in @('terminal_box_boundary_candidate','drawing_open_end','missing_geometry_candidate')})
  if(!$hits.Count -and @($support.terminationType|Sort-Object -Unique).Count -eq 1){$type=$support[0].terminationType}
  $terminations+=,[pscustomobject]@{modelType='RoutingTerminationCandidate';endpointRef=$o.nodeRef;rawOpenEndpoint=$true;terminationType=$type;status=$(if($type -ne 'unresolved'){'supported_candidate'}else{'unresolved'});deviceRefs=@($hits.deviceRef|Sort-Object -Unique);evidenceRefs=@($hits.attachmentRef);electricalTermination='unresolved';physicalTerminal='unresolved'}
  $terminations[-1].evidenceRefs+=@($support.evidenceRefs)
  if($type -in @('unresolved','missing_geometry_candidate')){$reviews+=,[pscustomobject]@{type='unexplained_open_endpoint';status='open';sourceRefs=@($o.nodeRef)}}
 }
 foreach($group in @($contacts|Group-Object deviceRef)){
  $ref=$group.Name;$g=$geometry[$ref];$m=$members[$ref];$ep=@($group.Group.endpointRef|Sort-Object -Unique);$er=@($group.Group.edgeRef|Sort-Object -Unique);$cr=@($group.Group.componentRef|Sort-Object -Unique)
  $aggregates+=,[pscustomobject]@{deviceRef=$ref;roleCandidate=$(if($m){$m.roleEvidenceRef}else{$g.evidenceRefs});roleStatus=$g.roleStatus;attachedRoutingEndpoints=$ep;attachedRoutingEdges=$er;routingComponentRefs=$cr;attachmentCount=$ep.Count;evidenceRefs=@($group.Group.attachmentRef)}
  if($ep.Count -ge 2){
   $continuations+=,[pscustomobject]@{modelType='DeviceMediatedContinuationCandidate';deviceRef=$ref;endpointRefs=$ep;routingComponentRefs=$cr;systemScope='fire_alarm';status='partial';internalContinuity='unresolved';bridgeAllowed=$false;evidenceRefs=@($group.Group.attachmentRef);logicalMembershipRef=$(if($m){$m.membershipId}else{$null})}
   $reviews+=,[pscustomobject]@{type='device_internal_continuity_unresolved';status='open';sourceRefs=@($ref)+$ep}
  }
  if($m){foreach($c in $group.Group){
   $correspondences+=,[pscustomobject]@{modelType='RoutingLogicalCorrespondenceCandidate';logicalRef=$m.instanceNodeRef;categoryRef=$m.categoryNodeRef;membershipRef=$m.membershipId;routingRef=$c.edgeRef;componentRef=$c.componentRef;deviceRef=$ref;representationRef=$g.blockDefinitionRef;attachmentRef=$c.attachmentRef;correspondenceType='logical_instance_via_membership_to_attached_route';status='partial';roleStatus=$m.roleStatus;membershipStatus=$m.status;geometryStatus='supported_candidate';evidenceRefs=@($m.roleEvidenceRef,$m.sourceMappingRef,$c.attachmentRef)+@($g.evidenceRefs);physicalConnection='unresolved'}}}
 }
 $categorySets=@($correspondences|Group-Object categoryRef|ForEach-Object {[pscustomobject]@{modelType='RoutingLogicalCorrespondenceCandidate';logicalRef=$_.Name;routingRef=@($_.Group.componentRef|Sort-Object -Unique);deviceRef=@($_.Group.deviceRef|Sort-Object -Unique);correspondenceType='logical_category_to_routing_attached_instance_set';status='partial';evidenceRefs=@($_.Group.membershipRef|Sort-Object -Unique)}})
 foreach($le in $Logical.edges){
  # A layout-only branch target can nominate a search candidate, never a verified route.
  $ur=@($Logical.unresolvedRelations|Where-Object {$_.lineRef -cin $le.representationRefs -and $_.systemIdentity -eq 'fire_alarm'})
  $cats=@($Logical.nodes|Where-Object {$_.representationRef -cin @($ur.deviceRef)}|ForEach-Object nodeId)
  $candidates=@($correspondences|Where-Object {$_.categoryRef -cin $cats})
  $edgeResults+=,[pscustomobject]@{modelType='RoutingLogicalCorrespondenceCandidate';logicalRef=$le.edgeId;routingRef=@($candidates.routingRef|Sort-Object -Unique);deviceRef=@($candidates.deviceRef|Sort-Object -Unique);correspondenceType='logical_edge_to_route';status=$(if($candidates.Count){'unresolved'}else{'no_candidate'});reason=$(if($candidates.Count){'system_diagram_branch_target_unresolved'}else{'no_cross_drawing_route_evidence'});evidenceRefs=@($le.evidenceRefs)+@($ur.evidenceRefs);createsRoute=$false}
  $reviews+=,[pscustomobject]@{type='logical_without_route';status='open';sourceRefs=@($le.edgeId)}
 }
 foreach($c in $Routing.components){$reviews+=,[pscustomobject]@{type='route_without_logical_target';status='open';sourceRefs=@($c.componentId);reason='actual_network_target_unresolved'}}
 foreach($cs in $categorySets){$reviews+=,[pscustomobject]@{type='logical_routing_correspondence_partial';status='open';sourceRefs=@($cs.logicalRef)}}
 foreach($gap in $Routing.upstreamLogicalGaps){if($gap.bridgeAllowed){throw 'Upstream bridge prohibited'};if($gap.boundaryRelationStatus -eq 'supported_candidate'){$reviews+=,[pscustomobject]@{type='terminal_box_internal_unknown';status='open';sourceRefs=@($gap.gapId);sourceScope='system_diagram_not_plan_endpoint'}}}
 $golden=@($correspondences|Sort-Object @{Expression={if($_.roleStatus -eq 'explicit'){0}else{1}}},deviceRef,routingRef|Select-Object -First 1)
 [pscustomobject]@{modelType='RoutingLogicalCorrespondenceAudit';systemScope='fire_alarm';compartmentRef=$Routing.compartmentRef;endpointContacts=$contacts;terminations=$terminations;deviceAttachments=$aggregates;continuations=$continuations;correspondences=$correspondences;categoryCorrespondences=$categorySets;logicalEdgeCorrespondences=$edgeResults;golden=$golden;reviewItems=$reviews;upstreamReviewItems=$Logical.reviewItems;upstreamGaps=$Routing.upstreamLogicalGaps;bridgeAllowed=$false;originalComponentCount=$Routing.components.Count;resultComponentCount=$Routing.components.Count;createdRoutingEdges=@();confirmedConnections=@();requirementsModified=$false;statistics=[pscustomobject]@{rawOpenEndpointCount=$terminations.Count;deviceTerminatedCandidateCount=@($terminations|Where-Object terminationType -eq device_terminated_candidate).Count;terminalBoxBoundaryCount=@($terminations|Where-Object terminationType -eq terminal_box_boundary_candidate).Count;unexplainedOpenEndpointCount=@($terminations|Where-Object {$_.terminationType -in @('unresolved','missing_geometry_candidate')}).Count;attachedDevices=$aggregates.Count;oneAttachment=@($aggregates|Where-Object attachmentCount -eq 1).Count;twoAttachments=@($aggregates|Where-Object attachmentCount -eq 2).Count;moreAttachments=@($aggregates|Where-Object attachmentCount -gt 2).Count}}
}
Export-ModuleMember -Function Join-RoutingCorrespondence


