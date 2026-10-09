param([switch]$ControlledOnly)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../SheetScope.psm1') -Force
$script:n=0
function Check($v,$why){$script:n++;if(!$v){throw "FAIL: $why"}}
$p=[MepSheet.Geometry]::Transform(@(4,6,0),@(1,2,0),@(10,20,0),@(2,3,1),([math]::PI/2),@(0,0,1))
Check ([math]::Abs($p[0]+2)-lt 1e-8 -and [math]::Abs($p[1]-26)-lt 1e-8) 'base point nonuniform scale rotation translation'
$p=[MepSheet.Geometry]::Transform(@(2,3,0),@(0,0,0),@(0,0,0),@(1,1,1),0,@(0,0,-1))
Check ($p[0]-eq -2 -and $p[1]-eq 3) 'normal orientation is used'
$poly=[MepSheet.Geometry]::Box(@(0,0,10,10))
$frames=@([pscustomobject]@{sheetId='s1';worldOuterPolygon=$poly;worldBounds=@(0,0,10,10)})
$a=Get-SheetAssociation 'x' 'TEXT' (,@(1,1,2,2)) @() $frames .00001
Check ($a.status-eq 'supported') 'bbox inside'
$a=Get-SheetAssociation 'x' 'TEXT' (,@(9,1,11,2)) @() $frames .00001
Check ($a.status-eq 'partial' -and $a.boundaryCrossing) 'crossing is partial review'
$frames+= [pscustomobject]@{sheetId='s2';worldOuterPolygon=[MepSheet.Geometry]::Box(@(10,0,20,10));worldBounds=@(10,0,20,10)}
$a=Get-SheetAssociation 'x' 'TEXT' (,@(9,1,11,2)) @() $frames .00001
Check ($a.status-eq 'ambiguous' -and $a.candidateSheetIds.Count-eq 2) 'no largest overlap selection'
$a=Get-SheetAssociation 'x' 'TEXT' @() (,@(2,2,0)) $frames .00001
Check ($a.status-eq 'partial' -and $a.evidenceBasis-eq 'insertion_fallback') 'missing bbox fallback'
$a=Get-SheetAssociation 'x' 'TEXT' (,@(21,1,22,2)) @() $frames .00001
Check ($a.status-eq 'outside') 'outside after complete spatial test'
$a=Get-SheetAssociation 'x' 'TEXT' @() @() $frames .00001
Check ($a.status-eq 'unresolved') 'missing position is not outside'
$tilted=@(@(0,0,0),@(1,0,0),@(1,1,1),@(0,1,1))
Check (![MepSheet.Geometry]::Valid($tilted,.00001)) 'nonplanar XY frame not silently projected'
$diamond=@(@(0,5,0),@(5,0,0),@(10,5,0),@(5,10,0))
Check ([MepSheet.Geometry]::Relation($diamond,[MepSheet.Geometry]::Box(@(0,0,1,1)),.00001)-eq 'outside') 'polygon not just world bbox'
Check ([MepSheet.Geometry]::Relation($diamond,[MepSheet.Geometry]::Box(@(4,4,6,6)),.00001)-eq 'inside') 'rotated polygon interior'
$caught=$false;try{[MepSheet.Geometry]::Transform(@(1,1,0),@(0,0,0),@(0,0,0),@(0,1,1),0,@(0,0,1))|Out-Null}catch{$caught=$true};Check $caught 'singular transform rejected'
# Entire resolver on synthetic, renamed blocks: no fixture names, sizes or offsets.
function Poly($h,$points){[pscustomobject]@{handle=$h;type='LWPOLYLINE';closed=$true;visibility='0';points=$points;raw="DXF:38=0`nDXF:210=(0 0 1)`nDXF:42=0";sourceRef=('probe:'+ $h)}}
$child=[pscustomobject]@{handle='nested-x';type='INSERT';reference='inner-generic';visibility='0';sourceRef='parent:nested-x';raw="DXF:10=(-2 -3 0)`nDXF:41=2`nDXF:42=1`nDXF:43=1`nDXF:50=0`nDXF:210=(0 0 1)"}
$inner=[pscustomobject]@{name='inner-generic';base=@(1,1,0);entities=@((Poly 'outline' ([MepSheet.Geometry]::Box(@(1,1,11,11)))),(Poly 'inside' ([MepSheet.Geometry]::Box(@(2,2,10,10)))));sourceSnapshot='probe';sourceDocument='synthetic';pathStatus='resolved';parentRaw="ParentReferenceDXF:5=`"nested-x`"`nParentReferenceDXF:2=`"inner-generic`""}
$parent=[pscustomobject]@{name='outer-generic';base=@(0,0,0);entities=@($child);sourceSnapshot='probe';sourceDocument='synthetic'}
$inner.parentRaw+="`n"+($child.raw-replace '(?m)^DXF:','ParentReferenceDXF:')
$top=[pscustomobject]@{handle='top-z';id='s:top-z';name='outer-generic';attributes=@();raw="Insertion_OCS=(50 60 0)`nNormal_DXF210=(0 0 1)`nBlockTransform_or_Array_DXF=(41 . 1)`nBlockTransform_or_Array_DXF=(42 . 1)`nBlockTransform_or_Array_DXF=(43 . 1)`nBlockTransform_or_Array_DXF=(50 . 1.5707963267948966)"}
$snap=[pscustomobject]@{sourceSnapshot='s';sourceDocument='synthetic';inserts=@($top);texts=@()}
$rd=[pscustomobject]@{regions=@();paragraphs=@();layoutBoundaries=@()};$hy=[pscustomobject]@{sections=@()}
$r=Resolve-SheetScope $snap @($parent,$inner) $rd $hy
Check ($r.frames.Count-eq 1) 'generic block names supported'
$inner.entities+=,(Poly 'nested-note' ([MepSheet.Geometry]::Box(@(3,3,4,4))))
$r=Resolve-SheetScope $snap @($parent,$inner) $rd $hy
Check ($r.frames.Count-eq 1 -and $r.frames[0].sourceOuterFrameHandle-eq 'outline') 'inner containing a note box must not compete with outer'
Check ([math]::Abs($r.frames[0].worldBounds[0]-43)-lt 1e-8 -and [math]::Abs($r.frames[0].worldBounds[3]-78)-lt 1e-8) 'both INSERT transforms applied with base point'
Check (@($r.reviewItems|Where-Object type -EQ frame_title_cardinality).Count-eq 1) 'missing title is explicit'
$attrs=@([pscustomobject]@{tag='DRAWING_TITLE';rawText='Synthetic design';flags='0';handle='title-a';box=@(48,68,50,69);point=@(48,68,0)},[pscustomobject]@{tag='DRAWING_NUMBER';rawText='X-9';flags='0';handle='number-a';box=@(48,66,50,67);point=@(48,66,0)})
$label=[pscustomobject]@{handle='label';id='s:label';name='arbitrary-label';attributes=$attrs;point=@(50,70,0);raw=''}
$snap.inserts=@($top,$label);$r=Resolve-SheetScope $snap @($parent,$inner) $rd $hy
Check ($r.identities.Count-eq 1 -and $r.identities[0].identityStatus-eq 'supported') 'rotated frame pairs attribute bundle without fixed offset/name'
$label.point=@(500,700,0);$r=Resolve-SheetScope $snap @($parent,$inner) $rd $hy
Check ($r.identities[0].identityStatus-eq 'ambiguous') 'title insertion contradicts attribute containment'
$snap.inserts=@($top)
$oldParent=$inner.parentRaw;$inner.parentRaw=$inner.parentRaw.Replace('ParentReferenceDXF:41=2','ParentReferenceDXF:41=3')
$r=Resolve-SheetScope $snap @($parent,$inner) $rd $hy
Check ($r.frames.Count-eq 0 -and @($r.reviewItems|Where-Object type -EQ frame_transform_unresolved).Count-eq 1) 'same handle cannot hide cross-probe transform discrepancy'
$inner.parentRaw=$oldParent
$child.visibility='1';$r=Resolve-SheetScope $snap @($parent,$inner) $rd $hy
Check ($r.frames.Count-eq 0 -and $r.failedFrameRefs.Count-eq 1) 'hidden path not silently selected'
$child.visibility='0';$inner.entities[0].closed=$false;$r=Resolve-SheetScope $snap @($parent,$inner) $rd $hy
Check ($r.frames.Count-eq 0) 'open outer cannot become closed sheet'
if($ControlledOnly){Write-Host "PASS: $script:n controlled sheet checks";exit}
$manifest=Join-Path $PSScriptRoot 'sheet-scope-sample.json'
$result=& (Join-Path $PSScriptRoot '../Read-SheetScope.ps1') -ManifestPath $manifest
Check ($result.frames.Count-eq 39) '39 frames'
Check (@($result.frames|Where-Object geometryStatus -NE resolved).Count-eq 0) 'all polygons resolved'
Check ($result.identities.Count-eq 39 -and @($result.identities|Where-Object identityStatus -NE supported).Count-eq 0) '39 distinct paired identities'
Check (@($result.identities.drawingNumber|Sort-Object -Unique).Count-eq 39) 'no fabricated duplicates'
foreach($f in $result.frames){
 if($f.referencedDefinition-eq '*U649'){Check ($f.sourceOuterFrameHandle-eq '5063D' -and ($f.worldBounds[2]-$f.worldBounds[0])-eq 84100) 'U649 actual path not hidden union'}
 elseif($f.referencedDefinition-eq '*U650'){Check ($f.sourceOuterFrameHandle-eq '50648' -and ($f.worldBounds[2]-$f.worldBounds[0])-eq 105100) 'U650 actual path'}
 else{throw 'Unexpected fixture frame'}
}
foreach($pair in @(@('23428','EW-0002'),@('23471','EW-0003'),@('234DB','EW-0004'))){
 $a=@($result.textAssociations|Where-Object {$_.subjectRef.EndsWith(':'+$pair[0])})[0]
 Check ($a.status-eq 'supported' -and ($result.identities|Where-Object sheetId -EQ $a.candidateSheetIds[0]).drawingNumber-eq $pair[1]) 'real text independently assigned'
}
$s=@($result.regionAssociations|Where-Object {$_.subjectType-eq 'SectionCandidate' -and $_.subjectRef.EndsWith(':234DB:section')})[0]
Check ($s.status-eq 'supported' -and ($result.identities|Where-Object sheetId -EQ $s.candidateSheetIds[0]).drawingNumber-eq 'EW-0004') 'whole section including eight items'
Check (($s.fragmentRefs|ForEach-Object {$_.Split(':')[-1]}) -contains '23777') 'eighth subitem not lost in sheet overlay'
Check ($result.coverCandidates.Count-eq 1) 'cover excluded'
Check ($result.circuits.Count-eq 0 -and $result.quantities.Count-eq 0 -and $result.designStatements.Count-eq 0) 'no new semantics or quantities'
foreach($a in @($result.textAssociations|Where-Object {$_.boundaryCrossing-or $_.status-eq 'ambiguous'})){Check (@($result.reviewItems|Where-Object {$_.type-eq 'sheet_boundary_contact'-and $_.sourceRefs-contains $a.subjectRef}).Count-gt 0) 'every observed crossing reviewed; do not assume a real crossing exists'}
$result.sheetSummary|Sort-Object number|Select-Object number,title,frame,regionCount,ambiguousRegionCount|Format-Table -AutoSize|Out-Host
foreach($num in @('EW-0002','EW-0003','EW-0004')){$id=($result.identities|Where-Object drawingNumber -EQ $num).sheetId;$fr=$result.frames|Where-Object sheetId -EQ $id;Write-Host ($num+' bounds='+($fr.worldBounds-join ',')+' columns='+@($result.columns|Where-Object sheetId -EQ $id).Count)}
Write-Host ('ASSOCIATIONS '+(($result.regionAssociations|Group-Object status|ForEach-Object {$_.Name+'='+$_.Count}) -join '; '))
Write-Host ('COLUMNS '+$result.columns.Count+' REVIEWS '+$result.reviewItems.Count)
Write-Host ('REGION TYPES '+(($result.regionAssociations|Group-Object subjectType|ForEach-Object {$_.Name+'='+$_.Count}) -join '; '))
Write-Host ('TEXT '+(($result.textAssociations|Group-Object status|ForEach-Object {$_.Name+'='+$_.Count}) -join '; '))
Write-Host ('REVIEW TYPES '+(($result.reviewItems|Group-Object type|ForEach-Object {$_.Name+'='+$_.Count}) -join '; '))
Write-Host "PASS: $script:n sheet scope checks"
