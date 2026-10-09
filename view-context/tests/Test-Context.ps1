$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../ViewContext.psm1') -Force
$root=Join-Path $PSScriptRoot '../..'
$spec=Get-Content (Join-Path $PSScriptRoot 'confirmed-local.json') -Raw -Encoding UTF8|ConvertFrom-Json
$report=Join-Path $root 'local_test_data/MEP-entity-report.txt'
$g=Get-LocalTrayUnits -RawEntities @(Read-LocalEntities -Report $report -Handles $spec.selectionHandles)
$records=@(Read-AnnotationRegion -Report $report -Geometry $g|Where-Object {$_.handle -in $spec.annotationHandles})
function CloneValue($x){$v=ConvertFrom-Json (ConvertTo-Json -InputObject $x -Depth 70);foreach($item in $v){$item}}
$script:n=0
function Assert($ok,$why){if(-not $ok){throw $why};$script:n++}
$r=Invoke-LocalViewAnalysis -Geometry $g -Records $records -Spec $spec
$a=$r.evidence.associations[0]
Assert ($a.spatialRelation -eq 'interior_hit') 'real marker interior'
Assert ($a.associationStatus -eq 'human_confirmed' -and $a.automaticAssociationStatus -eq 'supported') 'human plus automatic support'
Assert ($r.widthMeasurements.Count -eq 1 -and [math]::Abs($r.widthMeasurements[0].drawingUnitSpacing-300) -lt 0.00001) 'isolated rectangle width'
Assert ($g.interfaces.Count -eq 0 -and $null -eq $g.units[0].width) 'kernel remains unchanged'
Assert ($r.widthMeasurements[0].conversionStatus -eq 'units_unresolved' -and $null -eq $r.widthMeasurements[0].engineeringUnitValue) 'no circular unit calibration'
Assert ($r.evidence.unitAssessments[0].height.values[0] -eq 150 -and $r.evidence.unitAssessments[0].height.status -eq 'annotation_only') 'height annotation only'
Assert (@($r.evidence.conflicts|Where-Object field -eq 'type').Count -eq 0) 'broad electrical category not conflict'
Assert ($r.context.drawingSet.drawingSetCompleteness -eq 'unknown' -and $r.context.drawingSet.documentRefs.Count -eq 1) 'one document not complete'
Assert ($r.context.viewContext.building.value -eq '4#楼' -and $r.context.viewContext.storey.value -eq '夹层') 'confirmed local building floor'
Assert ($r.measurementEligibility[0].status -in @('conditional','unresolved')) 'not eligible for quantity'
Assert ($r.context.region.boundary.status -eq 'unknown' -and $r.context.coordinateContext.grid.status -eq 'unknown' -and $r.context.coordinateContext.buildingDatum.status -eq 'unknown') 'unknown context explicit'
$point=$a.anchor
$outside=Get-UnitSpatialRelations -Point @(($point[0]+10000),$point[1],$point[2]) -Geometry $g
Assert ($outside[0].relation -eq 'outside') 'true outside'
$v=$g.units[0].vertices[0];$hits=Get-UnitSpatialRelations -Point $v -Geometry $g
Assert ($hits[0].relation -eq 'vertex_hit') 'vertex priority'
$mid=@((($g.units[0].vertices[0][0]+$g.units[0].vertices[1][0])/2),(($g.units[0].vertices[0][1]+$g.units[0].vertices[1][1])/2),0)
Assert ((Get-UnitSpatialRelations -Point $mid -Geometry $g)[0].relation -eq 'boundary_hit') 'boundary hit'
$gg=CloneValue $g;$gg.units[0].closure='unknown_far_end'
Assert ((Get-UnitSpatialRelations -Point $point -Geometry $gg)[0].relation -eq 'unknown') 'open contour no interior'
$gg=CloneValue $g;$duplicate=CloneValue $gg.units[0];$duplicate.id='overlapping-unit';$gg.units+=,$duplicate
$over=Get-TrayEvidence -Geometry $gg -Records $records
Assert ($over.associations[0].associationStatus -eq 'ambiguous' -and $over.associations[0].targetUnitIds.Count -eq 2) 'overlap ambiguity'
foreach($view in @('legend','detail','unknown')){
 $s=CloneValue $spec;$s.viewType=$view;$s.viewContextId='test-'+$view
 $q=Invoke-LocalViewAnalysis -Geometry $g -Records $records -Spec $s
 Assert ($q.measurementEligibility[0].status -ne 'eligible') "view $view cannot count"
 if($view -eq 'legend'){Assert ($q.measurementEligibility[0].status -eq 'excluded') 'legend excluded'}
 if($view -eq 'detail'){Assert ($q.measurementEligibility[0].quantityKind -eq 'installed_plan_length' -and $q.measurementEligibility[0].status -eq 'excluded') 'detail CAD length excluded'}
 Assert ($q.context.appliedHumanEvidence.Count -eq 0) 'confirmation cannot cross view'
}
foreach($field in @('regionId','drawingSnapshotId')){
 $s=CloneValue $spec;$s.$field='different-scope'
 $q=Invoke-LocalViewAnalysis -Geometry $g -Records $records -Spec $s
 Assert ($q.context.appliedHumanEvidence.Count -eq 0) "confirmation crossed $field"
 Assert ($q.context.viewContext.building.status -eq 'unknown') 'unconfirmed building not copied'
}
$rec=@(CloneValue $records);foreach($e in $rec){if($e.handle -eq '52CCA'){$e.text='住宅强电桥架450x150'}}
$q=Invoke-LocalViewAnalysis -Geometry $g -Records $rec -Spec $spec
Assert ($q.widthMeasurements[0].drawingUnitSpacing -eq $r.widthMeasurements[0].drawingUnitSpacing) 'annotation changed geometry measurement'
Assert ($q.evidence.associations[0].associationStatus -eq 'supported') 'changed declaration cannot inherit human confirmation'
$rawBefore=ConvertTo-Json -InputObject $g.rawEntities -Depth 50
$s=CloneValue $spec;$s|Add-Member scaleDeclaration '1:50';$null=Invoke-LocalViewAnalysis -Geometry $g -Records $records -Spec $s
$s.scaleDeclaration='1:100';$null=Invoke-LocalViewAnalysis -Geometry $g -Records $records -Spec $s
Assert ((ConvertTo-Json -InputObject $g.rawEntities -Depth 50) -eq $rawBefore) 'view scale changed raw coordinates'
$s=CloneValue $spec;$s|Add-Member unitScale ([pscustomobject]@{status='confirmed';independent=$true;factorToMm=2;coordinateContextId=$s.coordinateContextId;regionId=$s.regionId;viewContextId=$s.viewContextId;drawingSnapshotId=$s.drawingSnapshotId;evidenceIds=@('controlled-independent-calibration')})
$scaled=Invoke-LocalViewAnalysis -Geometry $g -Records $records -Spec $s
Assert ($scaled.widthMeasurements[0].engineeringUnitValue -eq 600 -and $scaled.widthMeasurements[0].drawingUnitSpacing -eq 300) 'valid scoped scale converts only derived measurement'
$s.unitScale.independent=$false;$unscaled=Invoke-LocalViewAnalysis -Geometry $g -Records $records -Spec $s
Assert ($null -eq $unscaled.widthMeasurements[0].engineeringUnitValue) 'dependent scale not certified'
$s.unitScale.independent=$true;$s.coordinateContextId='different-coordinates';$unscaled=Invoke-LocalViewAnalysis -Geometry $g -Records $records -Spec $s
Assert ($null -eq $unscaled.widthMeasurements[0].engineeringUnitValue) 'scale cannot cross coordinate contexts'
foreach($field in @('projectId','drawingSetSnapshotId','building','storey','viewType')){
 $s=CloneValue $spec;$s.$field='different-declaration';$c=New-LocalDrawingContext -Geometry $g -Spec $s
 Assert ($c.appliedHumanEvidence.Count -eq 0) "confirmation crossed $field"
}
$s=CloneValue $spec;$s.drawingSetCompleteness='complete';$failed=$false
try{$null=New-LocalDrawingContext -Geometry $g -Spec $s}catch{$failed=$true};Assert $failed 'single registration asserted completeness'
$gg=CloneValue $g;$gg.units[0].vertices=@(@(0,0,0),@(10,10,0),@(0,10,0),@(10,0,0))
Assert ((Get-UnitSpatialRelations -Point @(5,5,0) -Geometry $gg)[0].relation -eq 'unknown') 'self-intersection not valid polygon'
$gg.units[0].vertices=@(@(0,0,0),@(6,0,0),@(6,2,0),@(2,2,0),@(2,6,0),@(0,6,0))
Assert ((Get-UnitSpatialRelations -Point @(4,4,0) -Geometry $gg)[0].relation -eq 'outside') 'concave notch bounding box trap'
Assert ((Get-UnitSpatialRelations -Point @(1,4,0) -Geometry $gg)[0].relation -eq 'interior_hit') 'concave interior'
Assert ((Get-UnitSpatialRelations -Point @(1,4,1) -Geometry $gg)[0].relation -eq 'unknown') 'noncoplanar point not flattened'
$gg.units[0]|Add-Member holes @('unsupported-hole')
Assert ((Get-UnitSpatialRelations -Point @(1,4,0) -Geometry $gg)[0].relation -eq 'unknown') 'holes explicitly unsupported'
$near=@(($v[0]+0.0001),$v[1],$v[2])
Assert ((Get-UnitSpatialRelations -Point $near -Geometry $g)[0].relation -eq 'vertex_hit') 'vertex tolerance'
Assert ((ConvertTo-Json -InputObject $g.rawEntities -Depth 50) -eq $rawBefore) 'measurements never alter raw'
$generic=(Get-Content "$root/view-context/ViewContext.psm1" -Raw)+(Get-Content "$root/tray-evidence/SpatialRelations.psm1" -Raw)+(Get-Content "$root/tray-evidence/SpatialRelations.cs" -Raw)
foreach($answer in @('5216A','52CC9','555835','4#楼')){Assert (-not $generic.Contains($answer)) 'human answer leaked into generic implementation'}
foreach($name in @('projectId','drawingSetId','drawingSetSnapshotId','documentId','drawingSnapshotId','regionId','viewContextId','coordinateContextId','analysisRunId')){Assert ($r.geometry.contextRefs.PSObject.Properties.Name -contains $name) "missing context $name"}
$old=Get-Content "$root/geometry-units/tests/real-sample.json" -Raw|ConvertFrom-Json
$og=Get-LocalTrayUnits -RawEntities @(Read-LocalEntities -Report $report -Handles $old.selectionHandles)
$or=@(Read-AnnotationRegion -Report $report -Geometry $og|Where-Object {$_.handle -in @('52E67','52E68','52E65','52E66','52E63','52E64','52E61','52E62')})
$oe=Get-TrayEvidence -Geometry $og -Records $or
Assert (@($oe.associations|Where-Object {'52E67' -in $_.textHandles})[0].spatialRelation -eq 'vertex_hit') 'old outer corner'
Assert (@($oe.associations|Where-Object {'52E63' -in $_.textHandles})[0].spatialRelation -eq 'boundary_hit') 'old side landing'
Assert ($r.PSObject.Properties.Name -notcontains 'quantities' -and $r.PSObject.Properties.Name -notcontains 'centerPaths') 'scope exceeded'
Write-Output "PASS: $script:n local context checks."
