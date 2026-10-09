function Find-PlanRoutePath {
 param($Routing,$Termination,$Continuity,$PlanRelations,[string]$RoutingRef,[string]$TerminationRef='input:termination',[string]$PlanRelationsRef='input:plan-relations')
 if($Routing.systemScope -ne 'fire_alarm' -or !$RoutingRef -or $Continuity.sourceSnapshot -cne $Routing.sourceSnapshot -or $Termination.compartmentRef -cne $Routing.compartmentRef){throw 'Routing source/scope mismatch'}
 $nodes=@{};$adj=@{};$edges=@{};$terms=@{};$links=@();$rejected=@();$paths=@();$seen=@{}
 foreach($n in $Routing.nodes){$nodes[$n.nodeId]=$n;$adj[$n.nodeId]=[Collections.Generic.List[object]]::new()}
 foreach($t in $Termination.terminations){if($t.status -eq 'supported_candidate' -and $t.terminationType -eq 'device_terminated_candidate' -and $t.deviceRefs.Count){$terms[$t.endpointRef]=$t}}
 foreach($e in $Routing.edges){
  if($e.systemScope -ne 'fire_alarm'){throw 'Unknown or incompatible edge scope'}
  if(!$nodes.ContainsKey($e.fromNode) -or !$nodes.ContainsKey($e.toNode)){throw 'Missing real node'}
  $length=[math]::Sqrt([math]::Pow($e.endXY[0]-$e.startXY[0],2)+[math]::Pow($e.endXY[1]-$e.startXY[1],2))
  if([double]::IsNaN($length) -or [double]::IsInfinity($length) -or $length -le 0 -or [math]::Abs($length-$e.segmentLength) -gt .001){throw 'Stored segment length inconsistent'}
  $link=[pscustomobject]@{id=$e.edgeId;a=$e.fromNode;b=$e.toNode;kind='geometry';length=$length;rawRef=$e.rawEntityRef}
  $links+=,$link;$adj[$link.a].Add($link);$adj[$link.b].Add($link);$edges[$e.edgeId]=$e
 }
 foreach($j in $Continuity.candidates){
  $reason=@()
  if($j.continuityStatus -ne 'supported' -or $j.crossingConnectionAllowed -or $j.systemScopeCompatibility -ne 'compatible_candidate' -or $j.topologySemantic -ne 'crossing_jump_continuation'){$reason+='jump_not_admitted'}
  $a=$j.beforeEndpointRef;$b=$j.afterEndpointRef
  $ea=$edges[$j.beforeEdgeRef];$eb=$edges[$j.afterEdgeRef]
  if(!$ea -or !$eb -or $a -notin @($ea.fromNode,$ea.toNode) -or $b -notin @($eb.fromNode,$eb.toNode)){$reason+='jump_endpoint_mismatch'}
  if($nodes.ContainsKey($a) -and $nodes.ContainsKey($b)){
   $pa=$nodes[$a].point;$pb=$nodes[$b].point;$gap=[math]::Sqrt([math]::Pow($pa[0]-$pb[0],2)+[math]::Pow($pa[1]-$pb[1],2))
   if([math]::Abs($pa[2]-$pb[2]) -gt .001 -or [math]::Abs($gap-$j.gapDistance) -gt .001){$reason+='jump_coordinates_incompatible'}
  }
  if($terms.ContainsKey($a) -or $terms.ContainsKey($b)){$reason+='device_internal_continuity_unresolved'}
  if(@($Termination.terminations|Where-Object {$_.endpointRef -in @($a,$b) -and $_.terminationType -eq 'terminal_box_boundary_candidate'}).Count){$reason+='terminal_box_internal_unknown'}
  if(!$adj.ContainsKey($a) -or !$adj.ContainsKey($b) -or $adj[$a].Count -ne 1 -or $adj[$b].Count -ne 1){$reason+='jump_end_not_unique'}
  if($reason.Count){$rejected+=,@{ref=$j.candidateId;reasons=$reason};continue}
  $link=[pscustomobject]@{id=$j.candidateId;a=$a;b=$b;kind='visual';length=$j.gapDistance;rawRef=$j.evidenceRefs}
  $links+=,$link;$adj[$a].Add($link);$adj[$b].Add($link)
 }
 foreach($seed in @($nodes.Keys|Sort-Object)){
  if($seen.ContainsKey($seed)){continue}
  $q=[Collections.Generic.Queue[string]]::new();$q.Enqueue($seed);$seen[$seed]=$true;$ns=@();$ls=@{}
  while($q.Count){$n=$q.Dequeue();$ns+=,$n;foreach($l in $adj[$n]){$ls[$l.id]=$l;$other=if($l.a -eq $n){$l.b}else{$l.a};if(!$seen.ContainsKey($other)){$seen[$other]=$true;$q.Enqueue($other)}}}
  $ends=@($ns|Where-Object {$adj[$_].Count -eq 1}|Sort-Object);$branches=@($ns|Where-Object {$adj[$_].Count -gt 2})
  $topology=if($branches.Count){'branched_subgraph'}elseif($ends.Count -eq 2){'simple_path'}else{'cycle_or_unresolved'}
  $eligible=$topology -eq 'simple_path' -and $terms.ContainsKey($ends[0]) -and $terms.ContainsKey($ends[1])
  $orderedEdges=@();$orderedNodes=@();$steps=@();$visual=@()
  if($topology -eq 'simple_path'){
   $current=$ends[0];$prev=$null;$orderedNodes+=,$current
   while($current -ne $ends[1]){
    $next=@($adj[$current]|Where-Object id -ne $prev)
    if($next.Count -ne 1){throw 'Ambiguous ordering'};$l=$next[0];$to=if($l.a -eq $current){$l.b}else{$l.a}
    $steps+=,[pscustomobject]@{kind=$l.kind;ref=$l.id;fromNode=$current;toNode=$to;length=$l.length}
    if($l.kind -eq 'geometry'){$orderedEdges+=,$l.id}else{$visual+=,$l.id}
    $orderedNodes+=,$to;$prev=$l.id;$current=$to
   }
  }
  $rawLength=0.0;$gapLength=0.0;foreach($l in $ls.Values){if($l.kind -eq 'geometry'){$rawLength+=$l.length}else{$gapLength+=$l.length}}
  $devices=@($Termination.endpointContacts|Where-Object endpointRef -in $ns|ForEach-Object deviceRef|Sort-Object -Unique)
  $endDevices=@(foreach($n in $ends){if($terms.ContainsKey($n)){$terms[$n].deviceRefs}})
  $explicit=@($Termination.deviceAttachments|Where-Object {$_.deviceRef -in $endDevices -and $_.roleStatus -eq 'explicit'}).Count
  $reviews=@('route_end_semantics_unresolved','route_logical_identity_unresolved')
  if($branches.Count){$reviews+='route_branch_unresolved'};if($visual.Count){$reviews+='visual_gap_length_unresolved'}
  if(@($Termination.continuations|Where-Object deviceRef -in $devices).Count){$reviews+='device_internal_continuity_unresolved'}
  $qualified=@($orderedEdges|ForEach-Object {$RoutingRef+'#'+$_})
  $pr=@(for($ri=0;$ri -lt $PlanRelations.relations.Count;$ri++){if(@($PlanRelations.relations[$ri].routingEdgeRefs|Where-Object {$_ -cin $qualified}).Count){$PlanRelationsRef+'#relations['+$ri+']'}})
  $paths+=,[pscustomobject]@{modelType='RoutePathCandidate';startTerminationRef=if($eligible){$TerminationRef+'#endpoint:'+ $ends[0]}else{$null};endTerminationRef=if($eligible){$TerminationRef+'#endpoint:'+ $ends[1]}else{$null};startTermination=if($eligible){$terms[$ends[0]]}else{$null};endTermination=if($eligible){$terms[$ends[1]]}else{$null};orderedRoutingEdgeRefs=$qualified;orderedEdgeHandles=@($orderedEdges|ForEach-Object {$edges[$_].rawEntityRef.Split(':')[-1]});orderedNodeRefs=@($orderedNodes|ForEach-Object {$RoutingRef+'#'+$_});orderedSteps=$steps;visualContinuityRefs=$visual;intermediateDeviceRefs=@($devices|Where-Object {$_ -notin $endDevices});branchRefs=$branches;raw2DLength=$rawLength;raw2DLengthDrawingUnits=$rawLength;visualGapLength=$gapLength;lengthEffect='unresolved';INSUNITS=0;pathTopology=$topology;geometryStatus=if($eligible){'supported'}else{'unresolved'};logicalStatus='unresolved';evidenceRefs=@($ls.Values.rawRef);reviewItemRefs=$reviews;eligibleGolden=$eligible;explicitEndDeviceCount=$explicit;realEdgeCount=@($ls.Values|Where-Object kind -eq geometry).Count;planLogicalRelationRefs=$pr;orderingMeaning='deterministic traversal only, no engineering direction';bridgeAllowed=$false;createdRoutingEdges=@()}
 }
 $gold=@($paths|Where-Object eligibleGolden|Sort-Object @{Expression={$_.visualContinuityRefs.Count}},@{Expression={$_.explicitEndDeviceCount};Descending=$true},@{Expression={$_.realEdgeCount};Descending=$true},@{Expression={$_.orderedEdgeHandles -join ','}}|Select-Object -First 1)
 [pscustomobject]@{golden=$gold;selectionPolicy='supported two-device-ended simple component; fewer jumps, more explicit terminal roles, more real edges, stable handle tie-break';eligibleCount=@($paths|Where-Object eligibleGolden).Count;topologyAudit=@($paths|Select-Object pathTopology,eligibleGolden,realEdgeCount,branchRefs);rejectedContinuities=$rejected;deviceBridgeCreated=$false;sourceGraphModified=$false}
}
Export-ModuleMember -Function Find-PlanRoutePath
