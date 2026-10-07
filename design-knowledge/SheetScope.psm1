Set-StrictMode -Version 2
if(!('MepSheet.Geometry' -as [type])){Add-Type -Path (Join-Path $PSScriptRoot 'SheetGeometry.cs')}
function SF($r,$k){[regex]::Match($r,'(?m)^'+[regex]::Escape($k)+'=(.*?)\r?$').Groups[1].Value.Trim('"')}
function Get-SheetPoint($v){,@([regex]::Matches($v,'[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?')|ForEach-Object {[double]::Parse($_.Value,[cultureinfo]::InvariantCulture)})}
function SB($r,$prefix=''){
 if((SF $r ($prefix+'bboxStatus'))-ne 'read' -or (SF $r ($prefix+'bboxFrame'))-ne 'WCS'){return $null}
 $a=Get-SheetPoint (SF $r ($prefix+'bboxMin'));$b=Get-SheetPoint (SF $r ($prefix+'bboxMax'))
 if($a.Count-ne 3 -or $b.Count-ne 3 -or $b[0]-lt $a[0] -or $b[1]-lt $a[1]){return $null}
 ,@($a[0],$a[1],$b[0],$b[1])
}
function Read-SheetSnapshot([string]$Path){
 $s=[IO.File]::ReadAllText((Resolve-Path -LiteralPath $Path));$hash=(Get-FileHash -LiteralPath $Path).Hash
 if((SF $s AcquisitionMode)-ne 'ModelSpaceTopLevelAllLayers' -or $s-notmatch '(?m)^END_OF_REPORT'){throw 'Complete full snapshot required'}
 $inserts=@();$texts=@()
 foreach($m in [regex]::Matches($s,'(?ms)^EntityHandle=.*?(?=^EntityHandle=|^LayerEntityCount=|^LAYER_END|\z)')){
  $r=$m.Value;$h=SF $r EntityHandle;$type=SF $r DXF_Type
  if($type-in @('TEXT','MTEXT')){$texts+=,[pscustomobject]@{id=($hash+':'+$h);handle=$h;rawText=SF $r Text_RAW;entityType=$type;parentHandle=$null;box=(SB $r);point=(Get-SheetPoint (SF $r Insertion_WCS));sourceSnapshot=$hash;layer=SF $r Layer}}
  if($type-ne 'INSERT'){continue}
  $attrs=@(foreach($am in [regex]::Matches($r,'(?ms)^AttributeTag=.*?(?=^AttributeTag=|\z)')){
   $a=$am.Value;$ah=SF $a 'AttributeLayout.LayoutEntityHandle';if(!$ah){continue}
   $at=[pscustomobject]@{id=($hash+':'+$ah);handle=$ah;parentHandle=$h;rawText=SF $a AttributeText_RAW;tag=SF $a AttributeTag;entityType='ATTRIB';box=(SB $a 'AttributeLayout.');point=(Get-SheetPoint (SF $a 'AttributeLayout.Position_WCS'));sourceSnapshot=$hash;flags=SF $a 'AttributeLayout.AttributeFlags_DXF70';layer=SF $a AttributeLayer}
   $texts+=,$at;$at
  })
  $inserts+=,[pscustomobject]@{handle=$h;id=($hash+':'+$h);name=SF $r BlockName;effectiveName=SF $r EffectiveName_RAW;raw=$r;attributes=$attrs;point=(Get-SheetPoint (SF $r Insertion_WCS))}
 }
 [pscustomobject]@{sourceSnapshot=$hash;sourceDocument=SF $s DWG;inserts=$inserts;texts=$texts}
}
function Read-SheetProbe([string]$Path){
 $s=[IO.File]::ReadAllText((Resolve-Path -LiteralPath $Path));$hash=(Get-FileHash -LiteralPath $Path).Hash
 if($s-notmatch '(?m)^END_OF_REPORT' -or (SF $s ReadErrorCount)-ne '0'){throw 'Probe incomplete or has read errors'}
 $blocks=@(foreach($bm in [regex]::Matches($s,'(?ms)^Block_BEGIN=.*?^Block_END')){
  $r=$bm.Value
  $es=@(foreach($em in [regex]::Matches($r,'(?ms)^SourceDefinitionPath=.*?^Entity_END')){
   $e=$em.Value;$pts=@([regex]::Matches($e,'(?m)^DXF:10=(.*?)\r?$')|ForEach-Object {$p=Get-SheetPoint $_.Groups[1].Value;if($p.Count-eq 2){$p+=0.0};,$p})
   [pscustomobject]@{handle=SF $e EntityHandle;type=SF $e DXF_Type;reference=SF $e ReferencedBlockName;visibility=SF $e DXF60;closed=((SF $e Closed_RAW)-eq 'T');points=$pts;raw=$e;sourceRef=($hash+':'+(SF $e EntityHandle))}
  })
  [pscustomobject]@{name=SF $r Block_BEGIN;base=(Get-SheetPoint (SF $r 'DefinitionDXF:10'));entities=$es;sourceSnapshot=$hash;sourceDocument=SF $s DWG;pathStatus=SF $s DefinitionPathStatus;parentRaw=$s;path=$Path}
 })
 return $blocks
}
function Get-SheetTransform($raw,$base,$sourceRef,[switch]$Top){
 $ins=if($Top){Get-SheetPoint (SF $raw Insertion_OCS)}else{Get-SheetPoint (SF $raw 'DXF:10')}
 $normal=if($Top){Get-SheetPoint (SF $raw Normal_DXF210)}else{Get-SheetPoint (SF $raw 'DXF:210')}
 $scale=@();foreach($k in 41..43){$v=if($Top){[regex]::Match($raw,'(?m)^BlockTransform_or_Array_DXF=\('+ $k+' \. ([-\d.]+)\)').Groups[1].Value}else{SF $raw ('DXF:'+$k)};if($v-eq ''){throw 'Missing scale'};$scale+=[double]::Parse($v,[cultureinfo]::InvariantCulture)}
 $angle=if($Top){[regex]::Match($raw,'(?m)^BlockTransform_or_Array_DXF=\(50 \. ([-\d.]+)\)').Groups[1].Value}else{SF $raw 'DXF:50'}
 if($ins.Count-ne 3 -or $normal.Count-ne 3 -or $base.Count-ne 3 -or $angle-eq ''){throw 'Incomplete coordinate transform'}
 [pscustomobject]@{sourceRef=$sourceRef;insertion_OCS=$ins;scaleXYZ=$scale;rotationRadians=[double]::Parse($angle,[cultureinfo]::InvariantCulture);normal=$normal;definitionBase=$base;method='subtract_base_scale_rotate_OCS_basis_translate';status='read'}
}
function Convert-SheetPolygon($polygon,$transform){
 ,@($polygon|ForEach-Object {,[MepSheet.Geometry]::Transform($_,$transform.definitionBase,$transform.insertion_OCS,$transform.scaleXYZ,$transform.rotationRadians,$transform.normal)})
}
function Test-SheetLocalPolygon($e,$tolerance){
 if($e.type-ne 'LWPOLYLINE' -or !$e.closed -or $e.visibility-ne '0'){return $false}
 $normal=Get-SheetPoint (SF $e.raw 'DXF:210');$elevation=SF $e.raw 'DXF:38'
 if($normal.Count-ne 3 -or [math]::Abs($normal[0])-gt $tolerance -or [math]::Abs($normal[1])-gt $tolerance -or [math]::Abs($normal[2]-1)-gt $tolerance){return $false}
 if($elevation-eq '' -or [math]::Abs([double]$elevation)-gt $tolerance){return $false}
 if(@([regex]::Matches($e.raw,'(?m)^DXF:42=(.*)')|Where-Object {[double]$_.Groups[1].Value-ne 0}).Count){return $false}
 return [MepSheet.Geometry]::Valid($e.points,$tolerance)
}
function Get-SheetAssociation {
 param($SubjectRef,$SubjectType,[object[]]$Boxes=@(),[object[]]$Points=@(),[object[]]$Frames=@(),[double]$Tolerance=.00001)
 $hits=@();$boundary=$false;$hasBoxes=$Boxes.Count-gt 0
 foreach($f in $Frames){
  $inside=0;$outside=0;$touch=0
  if($hasBoxes){foreach($b in $Boxes){$rel=[MepSheet.Geometry]::Relation($f.worldOuterPolygon,[MepSheet.Geometry]::Box($b),$Tolerance);switch($rel){inside{$inside++} outside{$outside++} boundary{$touch++}}}}
  foreach($p in $Points){if($p.Count-lt 2){continue};$v=[MepSheet.Geometry]::Point($f.worldOuterPolygon,$p,$Tolerance);if($v-gt 0){$inside++}elseif($v-eq 0){$touch++}else{$outside++}}
  if($inside+$touch-gt 0){$hits+=,[pscustomobject]@{sheetId=$f.sheetId;inside=$inside;outside=$outside;boundary=$touch;containment=if($touch){'boundary'}elseif($outside){'mixed'}else{'inside'}};if($touch-or ($inside-and $outside)){$boundary=$true}}
 }
 $status=if(!$Boxes.Count-and !$Points.Count){'unresolved'}elseif(!$Frames.Count){'unresolved'}elseif($hits.Count-gt 1){'ambiguous'}elseif(!$hits.Count){'outside'}elseif($boundary-or $Points.Count){'partial'}else{'supported'}
 [pscustomobject]@{modelType='RegionToSheetAssociationCandidate';subjectRef=$SubjectRef;subjectType=$SubjectType;candidateSheetIds=@($hits|ForEach-Object {$_.sheetId});status=$status;boundaryCrossing=$boundary;containmentEvidence=$hits;evidenceBasis=if($hasBoxes){'WCS_bbox_polygon_test'}else{'insertion_fallback'};fallbackPointCount=$Points.Count;missingEvidence=@(if($Points.Count){'glyph_extent_unavailable'});geometrySeparatorEvidence=@();titleBlockRelation=@();automaticSemanticInheritance=$false}
}
function Resolve-SheetScope {
 param($Snapshot,[object[]]$Definitions,$Reader,$Hierarchy,[object[]]$AdditionalRegions=@(),[double]$Tolerance=.00001)
 $reviews=New-Object 'Collections.Generic.List[object]'
 function Review($type,$refs,$reason){$reviews.Add([pscustomobject]@{modelType='ReviewItem';type=$type;sourceRefs=@($refs);reason=$reason;status='open';automaticResolution=$false})}
 $defs=@{};foreach($d in $Definitions){if($defs.ContainsKey($d.name)){throw 'Duplicate probe definition input'};if($d.sourceDocument-cne $Snapshot.sourceDocument){throw 'Probe document differs: explicit correspondence required'};$defs[$d.name]=$d}
 $frames=@();$failures=@()
 foreach($top in $Snapshot.inserts){
  if(!$defs.ContainsKey($top.name)){continue};$parent=$defs[$top.name]
  $paths=@()
  foreach($child in $parent.entities){
   if($child.type-ne 'INSERT' -or $child.visibility-ne '0' -or !$defs.ContainsKey($child.reference)){continue}
   $def=$defs[$child.reference]
   if($def.pathStatus-ne 'resolved'){continue}
   if((SF $def.parentRaw 'ParentReferenceDXF:5')-cne $child.handle -or (SF $def.parentRaw 'ParentReferenceDXF:2')-cne $child.reference){throw 'Probe parent correspondence mismatch'}
   $polys=@($def.entities|Where-Object {Test-SheetLocalPolygon $_ $Tolerance})
   # Outer evidence requires a closed containing polygon plus a distinct inner polygon.
   foreach($poly in $polys){
    $contained=@($polys|Where-Object {$_.handle-ne $poly.handle -and [MepSheet.Geometry]::Relation($poly.points,$_.points,$Tolerance)-eq 'inside'})
    $outsideVertices=@(foreach($other in $def.entities){if($other.handle-eq $poly.handle -or $other.type-ne 'LWPOLYLINE' -or $other.visibility-ne '0'){continue};foreach($point in $other.points){if([MepSheet.Geometry]::Point($poly.points,$point,$Tolerance)-lt 0){,$point}}})
    if($contained.Count-and !$outsideVertices.Count){$paths+=,[pscustomobject]@{child=$child;definition=$def;outer=$poly;innerRefs=@($contained.sourceRef)}}
   }
  }
  if($paths.Count-ne 1){$failures+=,$top.id;Review frame_path_unresolved $top.id 'No unique closed containing outer polygon on supplied not-hidden path';continue}
  $path=$paths[0];$id=$top.id+':sheet'
  try{
   $t1=Get-SheetTransform $path.child.raw $path.definition.base $path.child.sourceRef
   $verifiedParentRaw=[regex]::Replace($path.definition.parentRaw,'(?m)^ParentReferenceDXF:','DXF:')
   $verified=Get-SheetTransform $verifiedParentRaw $path.definition.base ($path.definition.sourceSnapshot+':parent_reference')
   foreach($field in @('insertion_OCS','scaleXYZ','normal')){for($k=0;$k-lt 3;$k++){if([math]::Abs($t1.$field[$k]-$verified.$field[$k])-gt $Tolerance){throw 'snapshot/runtime discrepancy in parent transform'}}}
   if([math]::Abs($t1.rotationRadians-$verified.rotationRadians)-gt $Tolerance){throw 'snapshot/runtime discrepancy in parent rotation'}
   $t2=Get-SheetTransform $top.raw $parent.base $top.id -Top
   $local=Convert-SheetPolygon $path.outer.points $t1;$world=Convert-SheetPolygon $local $t2
   if(![MepSheet.Geometry]::Valid($world,$Tolerance)){throw 'Non-horizontal or degenerate polygon: XY sheet containment unsupported'}
   $frames+=,[pscustomobject]@{modelType='SheetFrameCandidate';sheetId=$id;sourceSnapshot=$Snapshot.sourceSnapshot;topLevelFrameHandle=$top.handle;referencedDefinition=$top.name;activeFramePath=@($top.handle,$top.name,$path.child.handle,$path.child.reference,$path.outer.handle);sourceOuterFrameHandle=$path.outer.handle;sourceOuterFrameRef=$path.outer.sourceRef;localOuterPolygon=$path.outer.points;parentLocalOuterPolygon=$local;worldOuterPolygon=$world;worldBounds=[MepSheet.Geometry]::Bounds($world);transformChain=@($t1,$t2);geometryStatus='resolved';closureStatus='closed_raw_polyline';outerEvidence=@('closed_convex_straight_polygon','contains_distinct_closed_inner_polygon')+$path.innerRefs;activeRepresentationCandidate='supported';visibilityEvidence=@(@{source=$path.child.sourceRef;DXF60=$path.child.visibility},@{source=$path.outer.sourceRef;DXF60=$path.outer.visibility},@{limitation='not a general dynamic visibility evaluator'});status='candidate'}
  }catch{$failures+=,$top.id;Review frame_transform_unresolved $top.id $_.Exception.Message}
 }
 $titles=@();$identities=@()
 foreach($i in $Snapshot.inserts){
  $names=@($i.attributes|Where-Object {$_.tag-match '^(图名|图纸名称|DRAWING_TITLE)$' -and $_.rawText -and !([int]$_.flags-band 1)})
  $nums=@($i.attributes|Where-Object {$_.tag-match '^(图号|图纸编号|DRAWING_NUMBER)$' -and $_.rawText -and !([int]$_.flags-band 1)})
  if(!$names.Count-or !$nums.Count){continue}
  $used=@($names)+@($nums);$boxes=@($used|Where-Object {$null-ne $_.box}|ForEach-Object {,$_.box});$points=@($used|Where-Object {$null-eq $_.box -and $_.point.Count-eq 3}|ForEach-Object {,$_.point})
  # Include insertion as independent containment evidence without downgrading available attribute boxes.
  $a=Get-SheetAssociation $i.id TitleBlockCandidate $boxes $points $frames $Tolerance
  $at=@($frames|Where-Object {$a.candidateSheetIds-contains $_.sheetId -and [MepSheet.Geometry]::Point($_.worldOuterPolygon,$i.point,$Tolerance)-ge 0})
  $status=if($a.status-eq 'supported' -and $at.Count-eq 1 -and $names.Count-eq 1 -and $nums.Count-eq 1){'supported'}else{'ambiguous'}
  $titles+=,[pscustomobject]@{modelType='TitleBlockCandidate';id=$i.id+':title';sourceInsert=$i.handle;sourceAttribs=$i.attributes;candidateSheetIds=$a.candidateSheetIds;status=$status;evidence=@($a,'attribute_title_number_bundle','insert_point_containment');relativePlacement=if($at.Count-eq 1){@(($i.point[0]-$at[0].worldBounds[0]),($i.point[1]-$at[0].worldBounds[1]))}else{@()}}
  $identities+=,[pscustomobject]@{modelType='DrawingIdentityCandidate';sheetId=if($status-eq 'supported'){$at[0].sheetId}else{$null};drawingNumber=if($nums.Count-eq 1){$nums[0].rawText}else{@($nums.rawText)};drawingTitle=if($names.Count-eq 1){$names[0].rawText}else{@($names.rawText)};sourceTitleBlock=$i.handle;sourceAttribHandles=@($used.handle);sourceSnapshot=$Snapshot.sourceSnapshot;disciplineCandidate=@($i.attributes|Where-Object tag -EQ '专业'|ForEach-Object {$_.rawText});identityStatus=$status}
  if($status-ne 'supported'){Review title_sheet_ambiguous $i.id 'Attribute extent and insertion do not identify one frame'}
 }
 foreach($f in $frames){$ids=@($identities|Where-Object sheetId -EQ $f.sheetId);if($ids.Count-ne 1){Review frame_title_cardinality $f.sheetId 'Expected one title candidate; no nearest fallback';foreach($i in $ids){$i.identityStatus='ambiguous'}}}
 foreach($g in @($identities|Group-Object drawingNumber|Where-Object Count -GT 1)){Review duplicate_drawing_number @($g.Group.sourceTitleBlock) $g.Name;foreach($identity in $g.Group){$identity.identityStatus='ambiguous'}}
 $textAssoc=@();$textMap=@{};$assocMap=@{}
 foreach($t in $Snapshot.texts){
  $textMap[$t.id]=$t;$bs=@();$ps=@();if($null-ne $t.box){$bs+=,$t.box}elseif($t.point.Count-eq 3){$ps+=,$t.point}
  $a=Get-SheetAssociation $t.id $t.entityType $bs $ps $frames $Tolerance;$textAssoc+=,$a;$assocMap[$t.id]=$a
  if($a.boundaryCrossing-or $a.status-eq 'ambiguous'){Review sheet_boundary_contact $t.id 'Text touches/crosses page boundary or intersects multiple pages; not assigned by area'}
 }
 $subjects=@()
 foreach($r in $Reader.regions){$refs=@($Reader.paragraphs|Where-Object {$r.paragraphIds-contains $_.paragraphId}|ForEach-Object {$_.textFragments.id}|Select-Object -Unique);$subjects+=,[pscustomobject]@{id=$r.regionId;type='DesignTextRegionCandidate';refs=$refs}}
 foreach($r in $Hierarchy.sections){$subjects+=,[pscustomobject]@{id=$r.sectionId;type='SectionCandidate';refs=$r.fragmentRefs}}
 foreach($r in $AdditionalRegions){$subjects+=,[pscustomobject]@{id=$r.id;type=$r.type;refs=$r.refs}}
 $regions=@()
 foreach($r in $subjects){$bs=@();$ps=@();$missing=@();foreach($ref in $r.refs){if(!$textMap.ContainsKey($ref)){$missing+=$ref;continue};$t=$textMap[$ref];if($null-ne $t.box){$bs+=,$t.box}elseif($t.point.Count-eq 3){$ps+=,$t.point}else{$missing+=$ref}}
  $a=Get-SheetAssociation $r.id $r.type $bs $ps $frames $Tolerance;$a|Add-Member fragmentRefs $r.refs;$a.missingEvidence+= $missing
  if($missing.Count-and $a.status-eq 'supported'){$a.status='partial'}
  $a.titleBlockRelation=@($identities|Where-Object {$a.candidateSheetIds-contains $_.sheetId}|ForEach-Object {$_.sourceTitleBlock})
  $regions+=,$a;if($a.status-ne 'supported'){Review region_sheet_unresolved $r.id ('Spatial status: '+$a.status)}
 }
 $columns=@()
 foreach($f in $frames){
  $members=@($regions|Where-Object {$_.subjectType-eq 'DesignTextRegionCandidate' -and $_.status-eq 'supported' -and $_.candidateSheetIds[0]-eq $f.sheetId})
  $ci=0;foreach($m in $members|Sort-Object {($Reader.regions|Where-Object regionId -EQ $_.subjectRef).referenceX}){
   $ci++;$pts=@(foreach($ref in $m.fragmentRefs){$t=$textMap[$ref];if($t.box){[MepSheet.Geometry]::Box($t.box)}else{,$t.point}})
   $bounds=[MepSheet.Geometry]::Bounds($pts)
   $reg=@($Reader.regions|Where-Object regionId -EQ $m.subjectRef)[0]
   $seps=@($Reader.layoutBoundaries|Where-Object {$_.minX-le $bounds[2]-and $_.maxX-ge $bounds[0]-and $_.minY-le $bounds[3]-and $_.maxY-ge $bounds[1]})
   $m.geometrySeparatorEvidence=@($seps|ForEach-Object {$_.id})
   $columns+=,[pscustomobject]@{modelType='ColumnScopeCandidate';id=($f.sheetId+':column:'+ $ci);sheetId=$f.sheetId;bounds=$bounds;columnIndexCandidate=$ci;textRegionRefs=@($m.subjectRef);separatorEvidence=$seps;readingOrderCandidate=@($Reader.paragraphs|Where-Object {$reg.paragraphIds-contains $_.paragraphId}|Sort-Object topY -Descending|ForEach-Object {$_.readingOrderCandidate});status='candidate';scope='existing column segment inside one sheet';crossColumnContinuation='not_attempted'}
  }
 }
 $spatial=@()
 for($i=0;$i-lt $frames.Count;$i++){for($j=$i+1;$j-lt $frames.Count;$j++){
  $a=$frames[$i];$b=$frames[$j]
  if([MepSheet.Geometry]::Intersects($a.worldOuterPolygon,$b.worldOuterPolygon,(-$Tolerance))){Review overlapping_sheet_candidates @($a.sheetId,$b.sheetId) 'Positive polygon overlap; no deduplication'}
 }}
 foreach($a in $frames){$best=[double]::PositiveInfinity;$other=$null;foreach($b in $frames){if($a.sheetId-eq $b.sheetId){continue};$dx=[math]::Max(0,[math]::Max($a.worldBounds[0]-$b.worldBounds[2],$b.worldBounds[0]-$a.worldBounds[2]));$dy=[math]::Max(0,[math]::Max($a.worldBounds[1]-$b.worldBounds[3],$b.worldBounds[1]-$a.worldBounds[3]));$gap=[math]::Sqrt($dx*$dx+$dy*$dy);if($gap-lt $best){$best=$gap;$other=$b.sheetId}}
  $size=[math]::Min($a.worldBounds[2]-$a.worldBounds[0],$a.worldBounds[3]-$a.worldBounds[1]);$spatial+=,[pscustomobject]@{sheetId=$a.sheetId;nearestFrameRef=$other;bboxGap=if($other){$best}else{$null};gapBasis='axis_aligned_bounds';anomalyThreshold=$size;status=if(!$other){'not_applicable'}elseif($best-gt $size){'isolated_candidate'}else{'not_flagged'}};if($other-and $best-gt $size){Review isolated_sheet_candidate $a.sheetId 'Nearest frame bbox gap exceeds own short side; layout clue only'}
 }
 $cover=@($Snapshot.inserts|Where-Object {$_.raw-match '(?m)^VALUE="封面"' -and !$defs.ContainsKey($_.name)}|ForEach-Object {[pscustomobject]@{sourceRef=$_.id;handle=$_.handle;status='unresolved';reason='cover geometry not supplied';includedInOrdinarySheets=$false}})
 $summary=@(foreach($f in $frames){$i=@($identities|Where-Object sheetId -EQ $f.sheetId);[pscustomobject]@{sheetId=$f.sheetId;number=(($i|ForEach-Object {$_.drawingNumber})-join '|');title=(($i|ForEach-Object {$_.drawingTitle})-join '|');frame=$f.topLevelFrameHandle;frameResolved=($f.geometryStatus-eq 'resolved');titleResolved=($i.Count-eq 1-and $i[0].identityStatus-eq 'supported');identityResolved=($i.Count-eq 1-and $i[0].identityStatus-eq 'supported');polygonResolved=$true;regionCount=@($regions|Where-Object {$_.status-eq 'supported'-and $_.candidateSheetIds-contains $f.sheetId}).Count;ambiguousRegionCount=@($regions|Where-Object {$_.status-eq 'ambiguous'-and $_.candidateSheetIds-contains $f.sheetId}).Count}})
 [pscustomobject]@{version='0.1-experimental';sourceSnapshot=$Snapshot.sourceSnapshot;sourceDocument=$Snapshot.sourceDocument;frames=$frames;failedFrameRefs=$failures;titleBlocks=$titles;identities=$identities;sheets=@($frames|ForEach-Object {[pscustomobject]@{modelType='SheetCandidate';id=$_.sheetId;frameRef=$_.topLevelFrameHandle;sourceSnapshot=$Snapshot.sourceSnapshot;status='candidate'}});textAssociations=$textAssoc;regionAssociations=$regions;columns=$columns;reviewItems=$reviews.ToArray();spatialChecks=$spatial;coverCandidates=$cover;sheetSummary=$summary;designStatements=@();circuits=@();quantities=@();limitations=@('supplied probe paths only, no automatic recursive extraction','DXF60 supports representation candidate, not final visibility','horizontal convex frame polygons only','columns remain segments; no automatic cross-column reading','snapshot correspondence explicitly supplied by manifest; no evidence migration')}
}
Export-ModuleMember -Function Read-SheetSnapshot,Read-SheetProbe,Resolve-SheetScope,Get-SheetAssociation,Get-SheetTransform,Convert-SheetPolygon
