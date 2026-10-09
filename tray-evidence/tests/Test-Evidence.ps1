$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../../geometry-units/GeometryUnits.psm1') -Force
Import-Module (Join-Path $PSScriptRoot '../TrayEvidence.psm1') -Force
$root=Join-Path $PSScriptRoot '../..'
$f=Get-Content "$root/geometry-units/tests/real-sample.json" -Raw | ConvertFrom-Json
$g=Get-LocalTrayUnits -RawEntities @(Read-LocalEntities "$root/local_test_data/MEP-entity-report.txt" $f.selectionHandles)
$records=@(Read-AnnotationRegion -Report "$root/local_test_data/MEP-entity-report.txt" -Geometry $g)
$script:n=0
function Assert($ok,$why){if(-not $ok){throw $why};$script:n++}
function CloneEvidence($x){$v=ConvertFrom-Json (ConvertTo-Json -InputObject $x -Depth 60);foreach($i in $v){$i}}
$units=[pscustomobject]@{mmPerDrawingUnit=1;source='independent_test_calibration';independent=$true;annotationLengthUnit='mm';evidence='synthetic independent scale for comparison tests'}
function Run($r=$records,$geo=$g,$u=$units){Get-TrayEvidence -Geometry $geo -Records $r -UnitContext $u}
$r=Run
foreach($h in @('52E67','52E63')){
 $a=@($r.associations | Where-Object {$h -in $_.textHandles -and $_.targetUnitIds.Count -gt 0})
 Assert ($a.Count -eq 1) "$h association"
 Assert ($a[0].strength -eq 'strong_spatial') "$h strength"
}
Assert (@($r.associations | Where-Object {'5303A' -in $_.textHandles -and $_.targetUnitIds.Count -gt 0}).Count -eq 0) 'fire misbound'
$fire=@($r.associations | Where-Object {'5303A' -in $_.textHandles})[0]
Assert ('51903' -in $fire.otherLandingHandles -and '51904' -in $fire.otherLandingHandles) 'fire external geometry landing'
foreach($expected in @(@('52E67','52E68','52E65','52E66','bend'),@('52E63','52E64','52E61','52E62','straight'))){
 $association=@($r.associations|Where-Object {$expected[0] -in $_.textHandles})[0]
 Assert ($expected[1] -in $association.textHandles -and $association.leaderHandle -eq $expected[2] -and $expected[3] -in $association.markerHandles) 'full annotation chain'
 Assert (@($g.units|Where-Object {$_.id -in $association.targetUnitIds})[0].kind -eq $expected[4]) 'landing unit kind'
 Assert ($association.markerResidual -lt 0.001 -and $association.markerResidual -gt 0) 'residual retained'
}
Assert (@($r.conflicts | Where-Object field -eq 'type').Count -eq 2) 'type conflicts'
Assert (@($r.evidence | Where-Object {$_.kind -eq 'width_comparison' -and $_.value.status -eq 'consistent'}).Count -eq 2) 'width checks'
Assert (@($r.unitAssessments | Where-Object {$_.height.status -eq 'annotation_only'}).Count -eq 2) 'height status'
Assert (@($r.unitAssessments | Where-Object {$_.identity -eq 'rejected'}).Count -eq 0) 'conflict rejected tray'
Assert (@($r.unitAssessments | Where-Object {$_.color.status -ne 'not_exported'}).Count -eq 0) 'color inferred'
$parsed=Convert-TrayDeclaration '普通强电桥架200×100'
Assert ($parsed.width -eq 200 -and $parsed.height -eq 100 -and $parsed.type -eq '普通强电' -and $parsed.isTray) 'parse declaration'
foreach($s in @('普通强电桥架 200 X 100','普通强电桥架200*100','普通强电桥架200x100mm')){
 $p=Convert-TrayDeclaration $s;Assert ($p.width -eq 200 -and $p.height -eq 100 -and $p.raw -eq $s) 'variant parse'
}
$p=Convert-TrayDeclaration '梁下100吊装';Assert ($p.installation.reference -eq '梁下' -and $p.installation.offset -eq 100 -and $null -eq $p.height) 'installation parsed independently'
$c=@(CloneEvidence $records);$c=@($c | Where-Object handle -ne '52E66');$q=Run $c
Assert (@($q.associations | Where-Object {'52E67' -in $_.textHandles -and $_.strength -eq 'reduced_no_marker'}).Count -eq 1) 'marker removal'
$c=@(CloneEvidence $records);$c=@($c | Where-Object handle -ne '52E65');$q=Run $c
Assert (@($q.weakCandidates | Where-Object handle -eq '52E67').Count -eq 1) 'no leader must be weak'
$c=@(CloneEvidence $records);foreach($e in $c){$e.handle='renamed-'+$e.handle};$q=Run $c
Assert (@($q.associations | Where-Object {$_.targetUnitIds.Count -gt 0}).Count -eq @($r.associations | Where-Object {$_.targetUnitIds.Count -gt 0}).Count) 'handle dependency'
$c=@(CloneEvidence $records);foreach($e in $c){if($e.handle -in @('52E67','52E68')){$e.insertion[1]+=40;$e.alignment[1]+=40}};$q=Run $c
Assert (@($q.associations | Where-Object {'52E67' -in $_.textHandles -and $_.targetUnitIds.Count -eq 1}).Count -eq 1) 'text layout movement'
$c=@(CloneEvidence $records);$e=@($c|Where-Object handle -eq '5303A')[0];$e.insertion=@(556014251.0,553163541.0,0.0);$q=Run $c
Assert (@($q.associations | Where-Object {'5303A' -in $_.textHandles -and $_.targetUnitIds.Count -gt 0}).Count -eq 0) 'closer fire text misbound'
$gg=CloneEvidence $g;foreach($e in $gg.rawEntities){$e.layer='any-prefix-普通强电桥架'};$q=Run -geo $gg
Assert (@($q.conflicts | Where-Object field -eq 'type').Count -eq 0) 'consistent layer conflict'
$c=@(CloneEvidence $records);foreach($e in $c){if($e.handle -eq '52E67'){$e.text='普通强电桥架300x100'}};$q=Run $c
Assert (@($q.conflicts | Where-Object field -eq 'width').Count -eq 1) 'width conflict missing'
$dependent=[pscustomobject]@{mmPerDrawingUnit=1;source='manual_width_calibration';independent=$false;annotationLengthUnit='mm';evidence='same sample width'}
$q=Run -u $dependent
Assert (@($q.evidence | Where-Object {$_.kind -eq 'width_comparison' -and $_.value.status -eq 'consistent_not_independent'}).Count -eq 2) 'circular validation'
$q=Get-TrayEvidence -Geometry $g -Records $records
Assert (@($q.evidence | Where-Object {$_.kind -eq 'width_comparison' -and $_.value.status -eq 'units_unresolved'}).Count -eq 2) 'unknown units'
Assert ($q.PSObject.Properties.Name -notcontains 'centerPaths') 'phase three output'
$c=@(CloneEvidence $records);foreach($e in $c){if($e.handle -eq '52E67'){$e.text='普通强电桥架200x150'}};$q=Run $c
Assert (@($q.unitAssessments|Where-Object {$_.height.values -contains 150 -and $_.height.geometryVerified -eq $false}).Count -eq 1) 'height changed independently of width'
$c=@(CloneEvidence $records);foreach($e in $c){if($e.handle -eq '52E67'){$e.insertion[1]-=540;$e.alignment[1]-=540};if($e.handle -eq '52E68'){$e.insertion[1]+=540;$e.alignment[1]+=540}};$q=Run $c
Assert (@($q.associations|Where-Object {'52E67' -in $_.textHandles -and '52E68' -in $_.textHandles -and $_.targetUnitIds.Count -eq 1}).Count -eq 1) 'swapped rows'
$raw=@(CloneEvidence $g.rawEntities);foreach($e in $raw){$e.handle='geometry-'+$e.handle};$gg=Get-LocalTrayUnits -RawEntities $raw
$c=@(CloneEvidence $records);foreach($e in $c){$e.handle='annotation-'+$e.handle};$q=Run -r $c -geo $gg
Assert (@($q.unitAssessments|Where-Object identity -eq 'geometry_and_annotation_supported').Count -eq 2) 'all source handles renamed'
Assert (@($q.conflicts|Where-Object field -eq 'type').Count -eq 2) 'renamed conflicts'
$native=Convert-TrayDeclaration '通信桥架175×85'
Assert ($native.type -eq '通信' -and $native.width -eq 175 -and $native.height -eq 85) 'literal unknown category preserved'
$original=ConvertTo-Json -InputObject $records -Depth 60;$null=Run
Assert ((ConvertTo-Json -InputObject $records -Depth 60) -eq $original) 'raw annotation mutated'
$roundtrip=$r|ConvertTo-Json -Depth 60|ConvertFrom-Json
Assert ($roundtrip.associations[0].anchor.Count -eq 3 -and $roundtrip.rawAnnotationRecords.Count -eq $records.Count) 'result provenance roundtrip'
$source=Get-Content (Join-Path $PSScriptRoot '../TrayEvidence.psm1') -Raw -Encoding UTF8
foreach($handle in @('52E67','52E63','52E65','52E61','5303A','51903','52904')){Assert (-not $source.Contains($handle)) 'answer leaked into logic'}
$empty=Get-TrayEvidence -Geometry $g -Records @()
Assert ($empty.associations.Count -eq 0 -and $empty.unitAssessments.Count -eq 3) 'empty evidence degraded safely'
Assert (@($empty.unitAssessments|Where-Object identity -eq 'geometry_supported_only').Count -eq 3) 'missing annotation not rejection'
$gg=CloneEvidence $g;foreach($e in $gg.rawEntities){$e.layer='unclassified'};$q=Run -geo $gg
Assert (@($q.conflicts|Where-Object field -eq 'type').Count -eq 0) 'unknown layer is not contradiction'
$c=@(CloneEvidence $records);$duplicate=CloneEvidence (@($c|Where-Object handle -eq '52E65')[0]);$duplicate.handle='ambiguous-extra-leader';$c+=,$duplicate;$q=Run $c
Assert (@($q.associations|Where-Object {'52E67' -in $_.textHandles -and $_.status -eq 'ambiguous_layout'}).Count -eq 2) 'multiple leaders not resolved by nearest'
Assert (@($q.unitAssessments|Where-Object identity -eq 'geometry_and_annotation_supported').Count -eq 1) 'ambiguous association used as fact'
Assert ((ConvertTo-Json $g -Depth 60) -eq (ConvertTo-Json (Get-LocalTrayUnits -RawEntities @(Read-LocalEntities "$root/local_test_data/MEP-entity-report.txt" $f.selectionHandles)) -Depth 60)) 'geometry mutated'
Write-Output "PASS: $script:n evidence checks."
