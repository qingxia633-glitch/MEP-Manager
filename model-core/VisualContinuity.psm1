function New-RoutingContinuityView {
 param($Routing,[object[]]$Pairs,[object[]]$CrossedGeometry,$Pattern)
 if($Routing.systemScope -ne 'fire_alarm' -or $Pattern.sourceSnapshot -cne $Routing.sourceSnapshot){throw 'Explicit same-snapshot system scope required'}
 foreach($key in @('minGap','maxGap','tolerance','angleToleranceDegrees')){if($null -eq $Pattern.$key -or [double]::IsNaN([double]$Pattern.$key) -or [double]::IsInfinity([double]$Pattern.$key)){throw 'Finite pattern parameters required'}}
 if($Pattern.tolerance -le 0 -or $Pattern.minGap -le 0 -or $Pattern.angleToleranceDegrees -le 0){throw 'Positive pattern parameters required'}
 function Distance($a,$b){[math]::Sqrt([math]::Pow($a[0]-$b[0],2)+[math]::Pow($a[1]-$b[1],2))}
 function Cross($a,$b){$a[0]*$b[1]-$a[1]*$b[0]}
 function Delta($a,$b){,@(($a[0]-$b[0]),($a[1]-$b[1]))}
 function Dot($a,$b){$a[0]*$b[0]+$a[1]*$b[1]}
 $edges=@{};$ends=@{};$component=@{};$raw=@{};$results=@();$reviews=@()
 foreach($e in $Routing.edges){$edges[$e.edgeId]=$e}
 foreach($e in $Routing.openEndpoints){$ends[$e.nodeRef]=$e}
 foreach($c in $Routing.components){foreach($e in $c.edgeRefs){$component[$e]=$c.componentId}}
 foreach($g in $CrossedGeometry){$raw[$g.handle]=$g}
 foreach($p in $Pairs){
  $reasons=@();$a=$edges[$p.beforeEdgeRef];$b=$edges[$p.afterEdgeRef]
  if(!$a -or !$b -or $a.edgeId -eq $b.edgeId -or $p.endpointRefs.Count -ne 2){throw 'Invalid edge pair'}
  $ea=$ends[$p.endpointRefs[0]];$eb=$ends[$p.endpointRefs[1]]
  if(!$ea -or !$eb -or $ea.edgeRef -cne $a.edgeId -or $eb.edgeRef -cne $b.edgeId){throw 'Pair must reference real open ends'}
  $pa=$ea.coordinates;$pb=$eb.coordinates
  $oa=if($ea.nodeRef -eq $a.fromNode){$a.endXY}else{$a.startXY};$ob=if($eb.nodeRef -eq $b.fromNode){$b.endXY}else{$b.startXY}
  $u=Delta $pa $oa;$v=Delta $ob $pb;$gap=Delta $pb $pa;$la=Distance $pa $oa;$lb=Distance $ob $pb;$distance=Distance $pa $pb
  if($la -le 0 -or $lb -le 0 -or $distance -le $Pattern.tolerance){throw 'Degenerate pair'}
  $u=@(($u[0]/$la),($u[1]/$la));$v=@(($v[0]/$lb),($v[1]/$lb))
  $angle=[math]::Atan2([math]::Abs((Cross $u $v)),(Dot $u $v))*180/[math]::PI
  $alignment=[math]::Max([math]::Abs((Cross $u $gap)),[math]::Abs((Cross $v $gap)))
  $sameLayer=$a.layer -ceq $b.layer;$scope=$a.systemScope -eq 'fire_alarm' -and $b.systemScope -eq 'fire_alarm'
  if(!$scope){$reasons+='system_scope_incompatible'}
  if(!$sameLayer){$reasons+='layer_incompatible'}
  if([math]::Abs($pa[2]-$pb[2]) -gt $Pattern.tolerance -or [math]::Abs($pa[2]-$oa[2]) -gt $Pattern.tolerance -or [math]::Abs($pb[2]-$ob[2]) -gt $Pattern.tolerance){$reasons+='z_incompatible'}
  if((Dot $u $gap) -le 0 -or (Dot $v $gap) -le 0 -or $angle -gt $Pattern.angleToleranceDegrees -or $alignment -gt $Pattern.tolerance){$reasons+='direction_or_alignment_incompatible'}
  if($distance -lt ($Pattern.minGap-$Pattern.tolerance) -or $distance -gt ($Pattern.maxGap+$Pattern.tolerance)){$reasons+='outside_reviewed_pattern_range'}
  if($Pattern.status -ne 'supported_candidate' -or @($Pattern.evidenceRefs|Select-Object -Unique).Count -lt 3){$reasons+='repeated_pattern_evidence_missing'}
  $crossings=@();$mid=@((($pa[0]+$pb[0])/2),(($pa[1]+$pb[1])/2))
  foreach($ref in $p.crossedEdgeRef){
   if(!$raw.ContainsKey($ref)){continue};$g=$raw[$ref]
   if($g.sourceSnapshot -cne $Routing.sourceSnapshot -or $g.rawEntityRef -cin @($a.rawEntityRef,$b.rawEntityRef) -or @($g.bulges|Where-Object {$_ -ne 0}).Count){continue}
   for($i=1;$i -lt $g.vertices.Count;$i++){
    $c=$g.vertices[$i-1];$d=$g.vertices[$i];$w=Delta $d $c;$len=Distance $c $d;$det=Cross $gap $w
    if($len -le 0 -or [math]::Abs($det)/($distance*$len) -lt .1){continue}
    $q=Delta $c $pa;$t=(Cross $q $w)/$det;$s=(Cross $q $gap)/$det
    if($t -le 0 -or $t -ge 1 -or $s -lt 0 -or $s -gt 1){continue}
    $pt=@(($pa[0]+$t*$gap[0]),($pa[1]+$t*$gap[1]));$z=$c[2]+$s*($d[2]-$c[2]);$res=Distance $pt $mid
    if($res -le $Pattern.tolerance -and [math]::Abs($z-$pa[2]) -le $Pattern.tolerance){$crossings+=,[pscustomobject]@{ref=$g.rawEntityRef;point=$pt;centerResidual=$res;layer=$g.layer;systemScopeUnchanged=$true}}
   }
  }
  if(!$crossings.Count){$reasons+='jump_without_crossed_geometry'}
  if(@($crossings.ref|Select-Object -Unique).Count -gt 1){$reasons+='ambiguous_crossed_geometry'}
  $status=if(!$reasons.Count){'supported'}elseif($crossings.Count -and $scope -and $sameLayer){'partial'}else{'unresolved'}
  $id='visual-continuity:'+ $a.edgeId+':'+$b.edgeId
  $ri=@('crossing_connection_forbidden','jump_length_effect_unresolved')
  if($status -ne 'supported'){$ri+='visual_jump_continuity_partial';$ri+='ambiguous_gap'}
  if(!$crossings.Count){$ri+='jump_without_crossed_geometry'}
  foreach($r in $ri){$reviews+=,[pscustomobject]@{reviewId=$id+':'+$r;type=$r;status='open';sourceRefs=@($a.rawEntityRef,$b.rawEntityRef)}}
  $results+=,[pscustomobject]@{modelType='VisualContinuityCandidate';candidateId=$id;beforeEdgeRef=$a.edgeId;afterEdgeRef=$b.edgeId;beforeHandle=$a.rawEntityRef.Split(':')[-1];afterHandle=$b.rawEntityRef.Split(':')[-1];beforeEndpointRef=$ea.nodeRef;afterEndpointRef=$eb.nodeRef;crossedEdgeRefs=@($crossings.ref|Select-Object -Unique);gapDistance=$distance;crossingPoint=@($crossings.point);directionBefore=$u;directionAfter=$v;angleDifference=$angle;alignmentResidual=$alignment;centerResidual=$(if($crossings.Count){($crossings|Measure-Object centerResidual -Maximum).Maximum}else{$null});sameLayer=$sameLayer;systemScopeCompatibility=$(if($scope){'compatible_candidate'}else{'incompatible'});representationPattern=$Pattern.patternId;continuityStatus=$status;topologySemantic=$(if($status -eq 'supported'){'crossing_jump_continuation'}else{'unresolved'});crossingConnectionAllowed=$false;physicalContinuity='unresolved';quantityLengthEffect='unresolved';componentRefs=@($component[$a.edgeId],$component[$b.edgeId]);evidenceRefs=@($a.rawEntityRef,$b.rawEntityRef)+@($crossings.ref)+@($Pattern.evidenceRefs);reviewItemRefs=@($ri|ForEach-Object {$id+':'+$_});blockingReasons=$reasons}
 }
 # Only unambiguous supported proposals enter this separate view. Never mutate raw components.
 $used=@{};foreach($r in $results|Where-Object continuityStatus -eq supported){foreach($ep in @($r.beforeEndpointRef,$r.afterEndpointRef)){if(!$used.ContainsKey($ep)){$used[$ep]=0};$used[$ep]++}}
 foreach($r in $results|Where-Object continuityStatus -eq supported){if($used[$r.beforeEndpointRef] -gt 1 -or $used[$r.afterEndpointRef] -gt 1){$r.continuityStatus='partial';$r.topologySemantic='unresolved';$r.blockingReasons+='ambiguous_endpoint_pairing';$reviewId=$r.candidateId+':ambiguous_gap';$r.reviewItemRefs+=$reviewId;$reviews+=,[pscustomobject]@{reviewId=$reviewId;type='ambiguous_gap';status='open';sourceRefs=$r.evidenceRefs}}}
 $parent=@{};foreach($c in $Routing.components){$parent[$c.componentId]=$c.componentId}
 function Find($x){while($parent[$x] -ne $x){$x=$parent[$x]};$x}
 foreach($r in $results|Where-Object continuityStatus -eq supported){$aa=Find $r.componentRefs[0];$bb=Find $r.componentRefs[1];$parent[$bb]=$aa}
 $groups=@($Routing.components|Group-Object {Find $_.componentId}|ForEach-Object {[pscustomobject]@{modelType='ContinuityGroupCandidate';groupRef=$_.Name;rawComponentRefs=@($_.Group.componentId);status='candidate';quantityLengthEffect='unresolved'}})
 foreach($group in $groups){$group|Add-Member continuityRefs @($results|Where-Object {$_.continuityStatus -eq 'supported' -and $_.componentRefs[0] -in $group.rawComponentRefs -and $_.componentRefs[1] -in $group.rawComponentRefs}|ForEach-Object candidateId)}
 [pscustomobject]@{modelType='RoutingContinuityViewCandidate';sourceSnapshot=$Routing.sourceSnapshot;affectedOpenEndpointRefs=@($results|Where-Object continuityStatus -eq supported|ForEach-Object {$_.beforeEndpointRef;$_.afterEndpointRef}|Sort-Object -Unique);affectedRawComponentRefs=@($results|Where-Object continuityStatus -eq supported|ForEach-Object componentRefs|Sort-Object -Unique);potentialMergedGroups=@($groups|Where-Object {$_.rawComponentRefs.Count -gt 1}).Count;pattern=$Pattern;candidates=$results;groups=$groups;reviewItems=$reviews;rawComponentCount=$Routing.components.Count;continuityAdjustedGroupCountCandidate=$groups.Count;rawEdgeCount=$Routing.edges.Count;rawOpenEndpointCount=$Routing.openEndpoints.Count;createdRoutingEdges=@();crossingConnections=@();quantityLengthEffect='unresolved';topologySemantics=@('junction','crossing_without_connection','crossing_jump_continuation','true_gap');rawGraphModified=$false}
}
Export-ModuleMember -Function New-RoutingContinuityView

