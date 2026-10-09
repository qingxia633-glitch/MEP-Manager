Set-StrictMode -Version 2
Import-Module (Join-Path $PSScriptRoot '../tray-evidence/SpatialRelations.psm1')
if(-not ('MepSheet.Geometry' -as [type])){Add-Type -Path (Join-Path $PSScriptRoot '../design-knowledge/SheetGeometry.cs')}
function F($x,$k){if($null -eq $x){return $null};if($x -is [System.Collections.IDictionary]){return $x[$k]};if($x.PSObject.Properties[$k]){return $x.$k};return $null}
function Resolve-CategoryToPlanInstanceSet {
 param([Parameter(Mandatory)]$Category,[Parameter(Mandatory)]$Compartment,[Parameter(Mandatory)]$Correspondence,
 [AllowEmptyCollection()][object[]]$Instances=@(),[AllowEmptyCollection()][object[]]$Roles=@(),[double]$Tolerance=0.001)
 if($Tolerance -le 0 -or [double]::IsNaN($Tolerance) -or [double]::IsInfinity($Tolerance)){throw 'Invalid tolerance'}
 $reviews=[Collections.Generic.List[object]]::new();$gates=@()
 $node=F $Category nodeRef;$zone=F $Compartment compartmentRef;$polygon=F $Compartment polygonRef
 $role=F $Category roleCandidate;$system=F $Category systemIdentity
 if(!$node -or !$zone -or !$polygon){throw 'Source references required'}
 if((F $Correspondence status) -ne 'supported' -or !(F $Correspondence transformRef) -or (F $Correspondence polygonRef) -cne $polygon -or !(F $Compartment frameRef) -or (F $Correspondence targetFrameRef) -cne (F $Compartment frameRef) -or (F $Category compartmentRef) -cne $zone){$gates+='coordinate_scope_unresolved'}
 $vertices=[double[][]]@(F $Compartment vertices)
 $valid=$vertices.Count -ge 3 -and (F $Compartment closed) -eq $true -and (F $Compartment boundaryStatus) -eq 'supported' -and @((F $Compartment holes) | Where-Object { $null -ne $_ }).Count -eq 0
 foreach($v in $vertices){if($v.Count -lt 2){$valid=$false};foreach($q in $v){if([double]::IsNaN($q) -or [double]::IsInfinity($q)){$valid=$false}}}
 if($valid){
  # Validate the supplied planar ring; membership remains the existing XY predicate.
  $ring=[double[][]]@($vertices|ForEach-Object { ,@($_[0],$_[1],0.0) })
  $valid=[Mep.Spatial.Polygon]::Valid($ring,$Tolerance)
 }
 if(!$valid){$gates+='compartment_boundary_unresolved'}
 $lists=@{};foreach($k in @('membersExplicit','membersInherited','membersPartial','outside','onBoundary','unresolved')){$lists[$k]=[Collections.Generic.List[string]]::new()}
 $assessments=[Collections.Generic.List[object]]::new();$seen=@{}
 foreach($i in $Instances){
  $ref=F $i instanceRef;if(!$ref -or $seen.ContainsKey($ref)){throw 'Instances require unique source references'};$seen[$ref]=$true
  $issues=@($gates);$rs=@($Roles|Where-Object {(F $_ instanceRef) -ceq $ref});$r=$null
  if($rs.Count -eq 1){$r=$rs[0]}else{$issues+='instance_role_unresolved'}
  $tier=F $r roleStatus;$st=F $r status
  if(!$role -or $role -in @('unknown','unresolved') -or $role -notin @(F $r roles) -or @(F $r roles).Count -ne 1 -or $tier -notin @('explicit','inherited_candidate') -or $st -notin @('supported','partial') -or !(F $r roleRef) -or !@((F $r sourceRefs)|Where-Object {$_}).Count){$issues+='instance_role_unresolved'}
  if(!$system -or $system -in @('unknown','unresolved') -or (F $r systemIdentity) -cne $system){$issues+='system_scope_mismatch'}
  if((F $i frameRef) -cne (F $Compartment frameRef)){$issues+='coordinate_scope_unresolved'}
  if((F $i compartmentRef) -and (F $i compartmentRef) -cne $zone){$issues+='compartment_scope_mismatch'}
  $point=@(F $i position);if($point.Count -lt 2){$issues+='coordinate_scope_unresolved'}
  foreach($q in $point){if($null -eq $q -or [double]::IsNaN([double]$q) -or [double]::IsInfinity([double]$q)){$issues+='coordinate_scope_unresolved'}}
  $classification='unresolved';$distance=$null;$bucket='unresolved'
  if(!$issues.Count){
   $distance=Get-PolygonBoundaryDistanceXY -Point $point -Vertices $vertices
   $p=[MepSheet.Geometry]::Point($vertices,[double[]]$point,$Tolerance)
   if($p -eq 0){$classification='on_boundary';$bucket='onBoundary';$issues+='boundary_membership_ambiguous'}
   elseif($p -lt 0){$classification='outside';$bucket='outside'}
   else{$classification='inside';$bucket=if($st -eq 'partial'){'membersPartial'}elseif($tier -eq 'inherited_candidate'){'membersInherited'}else{'membersExplicit'}}
   if($tier -eq 'inherited_candidate'){$issues+='role_inheritance_partial'}
  }
  $lists[$bucket].Add($ref)
  $assessments.Add([pscustomobject]@{instanceRef=$ref;roleRef=(F $r roleRef);roleStatus=$tier;classification=$classification;boundaryDistanceXY=$distance;tolerance=$Tolerance;reasons=@($issues|Sort-Object -Unique);confirmedRole=$false})
 }
 foreach($reason in @(@($gates)+@($assessments|ForEach-Object reasons)|Sort-Object -Unique)){
  $reviews.Add([pscustomobject]@{reviewId="$node/$zone/$reason";reason=$reason;status='open';instanceRefs=@($assessments|Where-Object {$reason -in $_.reasons}|ForEach-Object instanceRef);sourceRefs=@($node,$polygon)})
 }
 # Quantity is consulted only after the spatial membership lists are final.
 $count=$lists.membersExplicit.Count+$lists.membersInherited.Count
 $quantity=F $Category systemQuantityCandidate;$delta=$null;$consistency='comparison_unavailable';$number=0.0
 if(!$gates.Count -and $null -ne $quantity -and [double]::TryParse([string]$quantity,[ref]$number) -and ![double]::IsInfinity($number) -and ![double]::IsNaN($number) -and $number -ge 0 -and $number -eq [math]::Floor($number)){
  $delta=$number-$count;$consistency=if($delta -eq 0){'consistent_candidate'}else{'mismatch_candidate'}
  if($delta -ne 0){$reviews.Add([pscustomobject]@{reviewId="$node/$zone/quantity_mismatch";reason='quantity_mismatch';status='open';cause='unresolved';sourceRefs=@($node,(F $Category quantityRef),$polygon)})}
 }
 $complete=if($gates.Count){'unresolved'}elseif($lists.unresolved.Count -or $lists.onBoundary.Count -or $lists.membersPartial.Count -or $lists.membersInherited.Count -or $consistency -ne 'consistent_candidate'){'partial'}else{'complete_candidate'}
 [pscustomobject]@{modelType='CategoryToPlanInstanceSetCandidate';version='1.0';systemCategoryNodeRef=$node;roleCandidate=$role;scopeCandidate=(F $Category compartmentRef);systemIdentity=$system;systemQuantityCandidate=$quantity;quantityRef=(F $Category quantityRef);compartmentRef=$zone;polygonRef=$polygon;coordinateTransformRef=(F $Correspondence transformRef);candidateUniverse=@($Instances|ForEach-Object {F $_ instanceRef});membersExplicit=@($lists.membersExplicit);membersInherited=@($lists.membersInherited);membersPartial=@($lists.membersPartial);outside=@($lists.outside);onBoundary=@($lists.onBoundary);unresolved=@($lists.unresolved);mappingGranularity='category_to_instance_set';membershipStatus=$(if($gates.Count){'unresolved'}elseif($lists.unresolved.Count -or $lists.onBoundary.Count -or $lists.membersPartial.Count){'partial'}else{'supported'});completenessStatus=$complete;quantityConsistencyStatus=$consistency;quantityDelta=$delta;roleSupportedExpressionCount=$count;assessments=@($assessments);reviewItemRefs=@($reviews|ForEach-Object reviewId);reviewItems=@($reviews);confirmedBinding=$false;allowedUses=@('candidate_investigation');rawMutation='not_performed'}
}
Export-ModuleMember -Function Resolve-CategoryToPlanInstanceSet

