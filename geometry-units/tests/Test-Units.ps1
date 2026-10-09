param([string]$Report=(Join-Path $PSScriptRoot '../../local_test_data/MEP-entity-report.txt'))
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../GeometryUnits.psm1') -Force
$fixture=Get-Content (Join-Path $PSScriptRoot 'real-sample.json') -Raw | ConvertFrom-Json
$raw=@(Read-LocalEntities -Report $Report -Handles $fixture.selectionHandles)
$script:checks=0
function Check($ok,$message){if(-not $ok){throw $message};$script:checks++}
function Clone($value){$items=ConvertFrom-Json (ConvertTo-Json -InputObject $value -Depth 30);foreach($item in $items){$item}}
function Verify($inputEntities,$label,$edgeCount=12){
 $r=Get-LocalTrayUnits -RawEntities $inputEntities -Tolerance 0.00001
 Check ($r.rawEntities.Count -eq $inputEntities.Count) "$label raw loss"
 Check ($r.geometryEdges.Count -eq $edgeCount) "$label geometry edge count"
 Check ($r.units.Count -eq 3) "$label unit count"
 Check ($r.contours.Count -eq 3) "$label contour count"
 Check ($r.interfaces.Count -eq 2) "$label interface count"
 Check (@($r.units | Where-Object kind -eq 'straight').Count -eq 2) "$label straight units"
 Check (@($r.units | Where-Object kind -eq 'bend').Count -eq 1) "$label bend unit"
 Check (@($r.units | Where-Object closure -eq 'unknown_far_end').Count -eq 1) "$label invented closure"
 Check (@($r.units | Where-Object closure -eq 'closed').Count -eq 2) "$label closed units"
 Check (@($r.interfaces | Where-Object {$_.unitIds.Count -ne 2}).Count -eq 0) "$label fake branch"
 $all=@($r.geometryEdges | ForEach-Object {$_.sourceHandles})
 Check ($all.Count -eq $inputEntities.Count) "$label provenance multiplicity"
 foreach($entity in $inputEntities){Check ($entity.handle -in $all) "$label missing source"}
 $bend=@($r.units | Where-Object kind -eq 'bend')[0]
 Check ($bend.interfaceIds.Count -eq 2) "$label bend ports"
 # Compare full unit memberships, not only counts, after identity changes and copy removal.
 $original=@{};foreach($entity in $inputEntities){$original[$entity.handle]=$entity.entityKey.Split('/')[-1]}
 foreach($u in $r.units){
  $expected=if($u.kind -eq 'bend'){@($fixture.bendBoundary)+@('52CE9','52908')}
   elseif($u.closure -eq 'closed'){@($fixture.closedStraightBoundary)+@('52901')}
   else {@($fixture.openSides)+@('52CE9','52904')}
  $expected=@($expected | Where-Object {$_ -in $original.Values} | Sort-Object -Unique)
  $actual=@($u.sourceHandles | ForEach-Object {$original[$_]} | Sort-Object -Unique)
  Check (($actual -join ',') -eq ($expected -join ',')) "$label wrong unit membership"
  Check ($u.contourId -in $r.contours.id) "$label missing contour reference"
 }
 Check ($r.PSObject.Properties.Name -notcontains 'centerPaths') "$label center path out of scope"
 Check ($r.unassignedEdgeIds.Count -eq 0) "$label unexplained sample edges"
 $json=$r | ConvertTo-Json -Depth 40 | ConvertFrom-Json
 Check ($json.geometryEdges[0].points[0].Count -eq 3) "$label XYZ roundtrip"
 return $r
}
$base=Verify $raw 'real'
foreach($pair in $fixture.duplicates){
 $hits=@($base.geometryEdges | Where-Object {$pair[0] -in $_.sourceHandles -and $pair[1] -in $_.sourceHandles})
 Check ($hits.Count -eq 1) 'duplicate group mismatch'
 Check ($hits[0].coincidence -eq 'exact_report_coordinates') 'exact duplicate status'
 Check ($hits[0].id -in $base.interfaces.geometryEdgeId) 'duplicate is not interface'
}
$bend=@($base.units | Where-Object kind -eq 'bend')[0]
Check ($bend.vertices.Count -eq 7) 'real bend boundary'
foreach($h in $fixture.bendBoundary){Check ($h -in $bend.sourceHandles) 'bend source mismatch'}
$vertical=@($base.units | Where-Object {$_.kind -eq 'straight' -and $_.closure -eq 'closed'})[0]
foreach($h in $fixture.closedStraightBoundary){Check ($h -in $vertical.sourceHandles) 'closed straight source mismatch'}
Check ([math]::Abs($vertical.width-200) -lt 0.00001) 'measured width'
$open=@($base.units | Where-Object closure -eq 'unknown_far_end')[0]
foreach($h in $fixture.openSides){Check ($h -in $open.sourceHandles) 'open side mismatch'}
foreach($i in 0..($raw.Count-1)){
 $copy=Clone $raw;$copy[$i].vertices=@($copy[$i].vertices[1],$copy[$i].vertices[0])
 $null=Verify $copy "reverse-$i"
}
$copy=Clone $raw
for($i=0;$i -lt $copy.Count;$i++){$copy[$i].handle="anonymous-$i";$copy[$i].layer='unrelated-layer'}
$null=Verify $copy 'renamed'
$copy=Clone $raw
foreach($e in $copy){foreach($p in $e.vertices){$p[0]-=556013750.352873;$p[1]-=553163540.265205;$p[2]+=17}}
$null=Verify $copy 'translation'
$angle=0.617
foreach($e in $copy){foreach($p in $e.vertices){$x=$p[0];$y=$p[1];$p[0]=$x*[math]::Cos($angle)-$y*[math]::Sin($angle);$p[1]=$x*[math]::Sin($angle)+$y*[math]::Cos($angle)}}
$null=Verify $copy 'rotation'
foreach($e in $copy){foreach($p in $e.vertices){$p[0]*=1.7;$p[1]*=1.7}}
$scaled=Verify $copy 'width-scale'
Check ([math]::Abs(@($scaled.units | Where-Object {$_.kind -eq 'straight' -and $_.closure -eq 'closed'})[0].width-340) -lt 0.00001) 'scaled width'
foreach($h in @('52CE9','52904','52908','52901')){
 $copy=@(Clone $raw | Where-Object handle -ne $h)
 $null=Verify $copy "remove-$h"
}
$copy=@(Clone $raw | Where-Object {$_.handle -notin @('52CE9','52908')})
$null=Verify $copy 'remove-both-copies'
# Both duplicate pairs have the same direction simultaneously.
$copy=Clone $raw
foreach($pair in $fixture.duplicates){
 $a=@($copy | Where-Object handle -eq $pair[0])[0];$b=@($copy | Where-Object handle -eq $pair[1])[0]
 $b.vertices=@(@($a.vertices[0]),@($a.vertices[1]))
}
$null=Verify $copy 'same-direction-copies'
# Change only the horizontal strip width, not its length; move its inner corner with it.
$copy=Clone $raw
foreach($e in $copy){foreach($p in $e.vertices){
 if([math]::Abs($p[1]-553163740.265205) -lt 0.000001){$p[1]+=60}
}}
$changed=Get-LocalTrayUnits -RawEntities $copy
Check ($changed.units.Count -eq 3 -and $changed.interfaces.Count -eq 2) 'independent width change lost units'
Check ([math]::Abs(@($changed.units | Where-Object closure -eq 'unknown_far_end')[0].width-260) -lt 0.00001) 'independent measured width'
Check (@($changed.units | Where-Object kind -eq 'unknown').Count -eq 1) 'unequal-port transition should remain unresolved'
# A separate six-sided elbow fixture with a non-right-angle turn and arbitrary width.
function Segment($h,$a,$b){[pscustomobject]@{handle=$h;type='LINE';layer='fixture';vertices=@($a,$b);bulges=@();closed=$false}}
$theta=1.13;$w=137.0;$run=430.0;$length=1200.0
$dx=[math]::Cos($theta);$dy=[math]::Sin($theta)
$a=@(0.0,(-$w/2),0.0);$b=@(0.0,($w/2),0.0)
$inner=@(($run-$w/2*[math]::Tan($theta/2)),($w/2),0.0)
$outer=@(($run+$w/2*[math]::Tan($theta/2)),(-$w/2),0.0)
$ip=@(($run+$run*$dx-$w/2*$dy),($run*$dy+$w/2*$dx),0.0)
$op=@(($run+$run*$dx+$w/2*$dy),($run*$dy-$w/2*$dx),0.0)
$fi=@(($ip[0]+$length*$dx),($ip[1]+$length*$dy),0.0)
$fo=@(($op[0]+$length*$dx),($op[1]+$length*$dy),0.0)
$ring=@($a,$b,$inner,$ip,$op,$outer)
$synthetic=@(for($i=0;$i -lt $ring.Count;$i++){Segment "bend-$i" $ring[$i] $ring[(($i+1)%$ring.Count)]})
$synthetic+=@(Segment 'side-a' $a @(-1500.0,(-$w/2),0.0))
$synthetic+=@(Segment 'side-b' $b @(-1500.0,($w/2),0.0))
$synthetic+=@(Segment 'leg-a' $ip $fi)
$synthetic+=@(Segment 'leg-end' $fi $fo)
$synthetic+=@(Segment 'leg-b' $fo $op)
$general=Get-LocalTrayUnits -RawEntities $synthetic
Check ($general.units.Count -eq 3 -and $general.interfaces.Count -eq 2) 'non-right-angle units'
$gBend=@($general.units | Where-Object kind -eq 'bend')
Check ($gBend.Count -eq 1 -and $gBend[0].vertices.Count -eq 6) 'six-sided non-right-angle bend'
Check (@($general.units | Where-Object {$_.kind -eq 'straight' -and [math]::Abs($_.width-$w) -lt 0.00001}).Count -eq 2) 'arbitrary width'
# Verify small residuals are reported, not silently called exact.
$copy=Clone $raw;$edge=@($copy | Where-Object handle -eq '52CE9')[0]
foreach($p in $edge.vertices){$p[0]+=0.000002}
$near=Get-LocalTrayUnits -RawEntities $copy
Check (@($near.geometryEdges | Where-Object coincidence -eq 'within_tolerance').Count -eq 1) 'near-coincidence label'
$copy=Clone $raw;$edge=@($copy | Where-Object handle -eq '52CE9')[0]
$edge.vertices[0][0]-=0.000002
$near=Get-LocalTrayUnits -RawEntities $copy
Check ($near.geometryEdges.Count -eq 12 -and $near.interfaces.Count -eq 2) 'near reverse canonical orientation'
function Reject($items,$message){$failed=$false;try{$null=Get-LocalTrayUnits -RawEntities $items}catch{$failed=$true};Check $failed $message}
$copy=Clone $raw;$copy[0].vertices[0][2]=1;Reject $copy 'mixed elevations accepted'
$copy=Clone $raw;$copy[0].bulges[0]=0.5;Reject $copy 'arc treated as chord'
$copy=Clone $raw;$copy[0].closed=$true;Reject $copy 'closed polyline accepted as segment'
$copy=Clone $raw;$copy[0].handle=$copy[1].handle;Reject $copy 'duplicate identity accepted'
Reject @((Segment 'x' @(-1,0,0) @(1,0,0)),(Segment 'y' @(0,-1,0) @(0,1,0))) 'crossing should be unresolved'
Reject @((Segment 'x' @(0,0,0) @(3,0,0)),(Segment 'y' @(1,0,0) @(4,0,0))) 'partial overlap silently normalized'
$noClosure=Get-LocalTrayUnits -RawEntities @((Segment 'a' @(0,0,0) @(10,0,0)),(Segment 'b' @(0,2,0) @(10,2,0)))
Check ($noClosure.units.Count -eq 0 -and $noClosure.unassignedEdgeIds.Count -eq 2) 'two unsupported sides became closed unit'
$source=Get-Content (Join-Path $PSScriptRoot '../UnitGeometry.cs') -Raw
foreach($h in $fixture.selectionHandles){Check (-not $source.Contains($h)) 'fixture leaked into algorithm'}
Write-Output "PASS: $script:checks checks (real sample and perturbations)."
