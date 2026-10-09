Set-StrictMode -Version Latest
Import-Module (Join-Path $PSScriptRoot '../geometry-units/GeometryUnits.psm1')
Import-Module (Join-Path $PSScriptRoot '../tray-evidence/TrayEvidence.psm1')
function Copy-ContextValue($value){ConvertFrom-Json (ConvertTo-Json -InputObject $value -Depth 70)}
function Unknown-Value {[pscustomobject]@{status='unknown';value=$null;evidenceIds=@()}}
function Same-Set($a,$b){(@($a|Sort-Object -Unique)-join '|') -eq (@($b|Sort-Object -Unique)-join '|')}

function New-LocalDrawingContext {
 param([Parameter(Mandatory)]$Geometry,[Parameter(Mandatory)]$Spec)
 $hashes=@($Geometry.rawEntities|ForEach-Object {$_.reportSHA256}|Sort-Object -Unique)
 if($hashes.Count -ne 1){throw 'One local drawing snapshot is required'}
 if($Spec.drawingSetCompleteness -notin @('unknown','incomplete')){throw 'This minimal single-document registration cannot assert drawing-set completeness'}
 $hash=$hashes[0];$h=$Spec.confirmation
 $active=$h.evidenceType -eq 'HumanConfirmation' -and $hash -eq $Spec.drawingSnapshotId -and $hash -eq $h.drawingSnapshotId -and $Spec.regionId -eq $h.regionId -and $Spec.viewContextId -eq $h.viewContextId -and (Same-Set $Geometry.rawEntities.handle $h.subjectGeometryHandles)
 $active=$active -and $Spec.projectId -eq $h.projectId -and $Spec.drawingSetSnapshotId -eq $h.drawingSetSnapshotId -and $Spec.building -eq $h.building -and $Spec.storey -eq $h.storey -and $Spec.viewType -eq $h.viewType
 $refs=[pscustomobject]@{projectId=$Spec.projectId;drawingSetId=$Spec.drawingSetId;drawingSetSnapshotId=$Spec.drawingSetSnapshotId;documentId=$Spec.documentId;drawingSnapshotId=$hash;regionId=$Spec.regionId;viewContextId=$Spec.viewContextId;coordinateContextId=$Spec.coordinateContextId;analysisRunId=[guid]::NewGuid().ToString()}
 $view=[pscustomobject]@{id=$Spec.viewContextId;regionId=$Spec.regionId;viewType=$Spec.viewType;title=$Spec.viewTitle;building=(Unknown-Value);storey=(Unknown-Value);contextSource=if($active){'HumanConfirmation'}else{'unverified_context_declaration'};scope='selected local representation only';evidenceIds=@()}
 if($active){
  $view.building=[pscustomobject]@{status='human_confirmed';value=$Spec.building;evidenceIds=@($h.id)}
  $view.storey=[pscustomobject]@{status='human_confirmed';value=$Spec.storey;evidenceIds=@($h.id)}
  $view.evidenceIds=@($h.id)
 }
 $scaleDeclaration=if($Spec.PSObject.Properties.Name -contains 'scaleDeclaration'){$Spec.scaleDeclaration}else{$null}
 $unitScale=Unknown-Value
 if($Spec.PSObject.Properties.Name -contains 'unitScale'){
  $candidate=$Spec.unitScale
  if($candidate.status -eq 'confirmed' -and $candidate.independent -is [bool] -and $candidate.independent -eq $true -and $candidate.coordinateContextId -eq $Spec.coordinateContextId -and $candidate.regionId -eq $Spec.regionId -and $candidate.viewContextId -eq $Spec.viewContextId -and $candidate.drawingSnapshotId -eq $hash -and $candidate.factorToMm -gt 0 -and -not [double]::IsNaN($candidate.factorToMm) -and -not [double]::IsInfinity($candidate.factorToMm) -and @($candidate.evidenceIds).Count -gt 0){$unitScale=Copy-ContextValue $candidate}
 }
 [pscustomobject]@{schemaVersion=1;contextRefs=$refs;
  project=[pscustomobject]@{id=$Spec.projectId;status='minimal_registration'};
  drawingSet=[pscustomobject]@{id=$Spec.drawingSetId;snapshotId=$Spec.drawingSetSnapshotId;drawingSetCompleteness=$Spec.drawingSetCompleteness;documentRefs=@($Spec.documentId)};
  documentRef=[pscustomobject]@{id=$Spec.documentId;drawing=$Geometry.rawEntities[0].drawing;snapshotId=$hash};
  drawingSnapshotRef=[pscustomobject]@{id=$hash;reportFingerprint=$hash;source='existing report snapshot';declaredSnapshotMatches=($hash -eq $Spec.drawingSnapshotId)};
  region=[pscustomobject]@{id=$Spec.regionId;documentId=$Spec.documentId;selectedSourceHandles=@($Geometry.rawEntities.handle);membershipStatus=if($active){'local_human_confirmed'}else{'analysis_selection_only'};boundary=(Unknown-Value);scope='selected entities, not surrounding drawing area'};
  viewContext=$view;
  coordinateContext=[pscustomobject]@{id=$Spec.coordinateContextId;drawingUnits='drawing_units';rawFrame='WCS';localFrame=[pscustomobject]@{status='identity_to_raw';transformApplied=$false};unitScale=$unitScale;scaleDeclarations=@(if($Spec.PSObject.Properties.Name -contains 'unitScale'){Copy-ContextValue $Spec.unitScale});plotScale=[pscustomobject]@{status=if($null -eq $scaleDeclaration){'unknown'}else{'unverified_declaration'};value=$scaleDeclaration};grid=(Unknown-Value);buildingDatum=(Unknown-Value)};
  humanEvidence=@((Copy-ContextValue $h));appliedHumanEvidence=@(if($active){$h.id});
  rejectedHumanEvidence=@(if(-not $active){[pscustomobject]@{id=$h.id;reason='snapshot, region, view or exact subject set does not match'}})}
}

function Get-WidthMeasurements {
 param([Parameter(Mandatory)]$Geometry,[Parameter(Mandatory)]$Context,[double]$Tolerance=0.00001)
 foreach($u in $Geometry.units){
  if($u.kind -ne 'straight' -or $u.closure -ne 'closed' -or -not [Mep.Spatial.Polygon]::Valid([double[][]]$u.vertices,$Tolerance)){continue}
  $edges=@($Geometry.geometryEdges|Where-Object {$_.id -in $u.geometryEdgeIds});$pairs=@()
  for($i=0;$i -lt $edges.Count;$i++){for($j=$i+1;$j -lt $edges.Count;$j++){
   $a=$edges[$i];$b=$edges[$j];$p=$a.points[0];$q=$a.points[1];$r=$b.points[0];$s=$b.points[1]
   $x=$q[0]-$p[0];$y=$q[1]-$p[1];$l=[math]::Sqrt($x*$x+$y*$y);$vx=$s[0]-$r[0];$vy=$s[1]-$r[1];$lb=[math]::Sqrt($vx*$vx+$vy*$vy)
   if($l -le $Tolerance -or $lb -le $Tolerance){continue}
   $angular=[math]::Abs($x*$vy-$y*$vx)/($l*$lb);if($angular -gt 0.000001){continue}
   $x/=$l;$y/=$l;$dx=$r[0]-$p[0];$dy=$r[1]-$p[1];$t0=$x*$dx+$y*$dy;$t1=$t0+$x*$vx+$y*$vy
   $lo=[math]::Max(0.0,[math]::Min($t0,$t1));$hi=[math]::Min($l,[math]::Max($t0,$t1));$w=[math]::Abs($x*$dy-$y*$dx)
   if($hi-$lo -le $Tolerance -or $w -le $Tolerance){continue}
   $pairs+= [pscustomobject]@{edgeIds=@($a.id,$b.id);spacing=$w;overlap=$hi-$lo;residual=$angular;sourceHandles=@($a.sourceHandles)+@($b.sourceHandles)}
  }}
  if($pairs.Count -eq 0){continue}
  # On a rectangular straight, longer opposing edges supply the width candidate.
  # No annotation, interface count, cardinal direction or fixed dimension participates.
  $ordered=@($pairs|Sort-Object overlap -Descending);$chosen=$ordered[0]
  $status=if(@($ordered|Where-Object {[math]::Abs($_.overlap-$chosen.overlap) -le $Tolerance}).Count -gt 1){'axis_ambiguous'}else{'supported_parallel_sides'}
  $scale=$Context.coordinateContext.unitScale;$converted=$null;$conversion='units_unresolved';$engineeringUnit=$null
  if($scale.status -eq 'confirmed'){$converted=$chosen.spacing*$scale.factorToMm;$conversion='converted_with_independent_evidence';$engineeringUnit='mm'}
  [pscustomobject]@{id='W-'+$u.id;unitId=$u.id;status=$status;sourceGeometryEdges=$chosen.edgeIds;sourceHandles=$chosen.sourceHandles;
   drawingUnitSpacing=$chosen.spacing;coordinateContextId=$Context.contextRefs.coordinateContextId;contextRefs=$Context.contextRefs;
   conversionStatus=$conversion;engineeringUnitValue=$converted;engineeringUnit=$engineeringUnit;conversionEvidenceRefs=@($scale.evidenceIds);
   method='parallel_opposite_long_sides_of_closed_straight';overlap=$chosen.overlap;angularResidual=$chosen.residual;tolerance=$Tolerance;
   dependencyRefs=@($u.contourId)+@($chosen.edgeIds);evidenceRefs=@();directionPolicy='geometry-only width candidate; square axis remains ambiguous'}
 }
}

function Get-MeasurementEligibility {
 param([Parameter(Mandatory)]$Geometry,[Parameter(Mandatory)]$Context)
 foreach($u in $Geometry.units){
  $view=$Context.viewContext.viewType;$missing=@('independent unit calibration','drawing-set completeness','measurement rules and duplicate-expression review');$reasons=@();$state='unresolved'
  if($Context.coordinateContext.unitScale.status -eq 'confirmed'){$missing=@($missing|Where-Object {$_ -ne 'independent unit calibration'})}
  if($view -in @('legend','detail','installation_detail','system_diagram','design_notes')){$state='excluded';$reasons=@('This view does not directly supply installed plan CAD line length');$missing=@()}
  elseif($view -in @('power_lighting_plan','plan')){
   $state='conditional';$reasons=@('Candidate plan representation; no quantities computed')
   if($Context.appliedHumanEvidence.Count -eq 0){$state='unresolved';$missing+= 'verified local view membership'}
  }else{$missing+='known view type';$reasons=@('Unknown view cannot enter confirmed quantity')}
  [pscustomobject]@{id='Q-'+$u.id;subject=[pscustomobject]@{unitId=$u.id;analysisRunId=$Context.contextRefs.analysisRunId};quantityKind='installed_plan_length';status=$state;
   reasons=$reasons;missingPrerequisites=$missing;evidenceRefs=@($Context.appliedHumanEvidence);viewContextId=$Context.viewContext.id;contextRefs=$Context.contextRefs;
   supportedStates=@('eligible','conditional','excluded','unresolved');scopeNote='detail explicit dimensions may support other future tasks; CAD sketch length is excluded'}
 }
}

function Invoke-LocalViewAnalysis {
 param([Parameter(Mandatory)]$Geometry,[Parameter(Mandatory)][object[]]$Records,[Parameter(Mandatory)]$Spec)
 $context=New-LocalDrawingContext -Geometry $Geometry -Spec $Spec
 if(@($Records|Where-Object {$_.reportSHA256 -ne $context.contextRefs.drawingSnapshotId}).Count -gt 0){throw 'Annotation/geometry snapshot mismatch'}
 $g=Copy-ContextValue $Geometry
 $g|Add-Member contextRefs $context.contextRefs -Force
 foreach($collection in @('geometryEdges','contours','units','interfaces')){foreach($item in $g.$collection){$item|Add-Member contextRefs $context.contextRefs -Force}}
 $measurements=@(Get-WidthMeasurements -Geometry $g -Context $context)
 $g|Add-Member widthMeasurements $measurements -Force
 $scopeRecords=@($Records|Where-Object {$_.handle -in $Spec.annotationHandles})
 $e=Get-TrayEvidence -Geometry $g -Records $scopeRecords
 $e|Add-Member contextRefs $context.contextRefs -Force
 foreach($collection in @('evidence','conflicts','unitAssessments','associations')){foreach($item in $e.$collection){$item|Add-Member contextRefs $context.contextRefs -Force}}
 foreach($a in $e.associations){
  $a|Add-Member automaticAssociationStatus $a.associationStatus
  $a|Add-Member humanEvidenceIds @()
  $h=$Spec.confirmation
  $sameText=$true
  foreach($handle in $h.textHandles){$record=@($scopeRecords|Where-Object handle -eq $handle);if($record.Count -ne 1 -or $record[0].text -cne $h.expectedTextByHandle.$handle){$sameText=$false}}
  if($context.appliedHumanEvidence.Count -gt 0 -and $sameText -and $a.associationStatus -eq 'supported' -and $h.markerHandle -in $a.markerHandles -and (Same-Set $a.textHandles $h.textHandles)){
   $a.associationStatus='human_confirmed';$a.humanEvidenceIds=@($h.id)
  }
 }
 # Human evidence is appended, never substituted for original drawing or automatic evidence.
 foreach($h in $context.humanEvidence){if($h.id -in $context.appliedHumanEvidence){
  $e.evidence+=,[pscustomobject]@{id=$h.id;evidenceType='HumanConfirmation';kind='human_confirmation';value=$h;contextRefs=$context.contextRefs;sourceHandles=$h.sourceHandles;dependencies=@()}
 }}
 foreach($m in $measurements){
  $m.evidenceRefs=@($e.evidence|Where-Object {$_.PSObject.Properties.Name -contains 'unitId' -and $_.unitId -eq $m.unitId -and $_.kind -eq 'geometry'}|ForEach-Object {$_.id})
 }
 [pscustomobject]@{schemaVersion=1;context=$context;contextRefs=$context.contextRefs;geometry=$g;evidence=$e;widthMeasurements=$measurements;
  contextualSourceRefs=@($Geometry.rawEntities|ForEach-Object {[pscustomobject]@{handle=$_.handle;reportFingerprint=$_.reportSHA256;entityKey=$_.entityKey;contextRefs=$context.contextRefs}});
  unassignedAnnotationHandles=@($Records|Where-Object {$_.handle -notin $Spec.annotationHandles}|ForEach-Object {$_.handle});
  measurementEligibility=@(Get-MeasurementEligibility -Geometry $g -Context $context);
  limitations=@('explicit local membership only','no project completeness inference','raw WCS retained; engineering scale unknown','simple closed XY polygons only; holes unsupported','no quantities or paths')}
}
Export-ModuleMember -Function New-LocalDrawingContext,Get-WidthMeasurements,Get-MeasurementEligibility,Invoke-LocalViewAnalysis,Read-LocalEntities,Get-LocalTrayUnits,Read-AnnotationRegion,Get-TrayEvidence,Get-UnitSpatialRelations
