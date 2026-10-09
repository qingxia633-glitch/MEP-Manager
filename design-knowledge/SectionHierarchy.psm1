Set-StrictMode -Version 2
Import-Module (Join-Path $PSScriptRoot 'BBoxContinuity.psm1')
Import-Module (Join-Path $PSScriptRoot 'LayoutReader.psm1')

function Get-StructureNumber([string]$Text) {
 $forms=@(
  @('dotted','^\s*(\d+(?:\.\d+)+)(?=$|[.、\s\p{IsCJKUnifiedIdeographs}])'),
  @('parenthesized','^\s*([（(]\d+[）)])'),
  @('closing_parenthesis','^\s*(\d+[）)])'),
  @('enumeration','^\s*(\d+、)'),
  @('dot','^\s*(\d+[.．])(?!\d)'),
  @('numeric_space','^\s*(\d+)\s+(?=\S)'),
  @('chinese','^\s*([一二三四五六七八九十]+[.、．])')
 )
 foreach($form in $forms){
  $m=[regex]::Match($Text,$form[1]);if(!$m.Success){continue}
  $raw=$m.Groups[1].Value;$parts=@([regex]::Matches($raw,'\d+')|ForEach-Object {[int]$_.Value})
  return [pscustomobject]@{raw=$raw;pattern=$form[0];parts=$parts;depth=$parts.Count;ordinal=if($parts.Count){$parts[-1]}else{$null}}
 }
 return $null
}

function Find-DocumentHierarchyCandidates {
 param([Parameter(Mandatory)]$ReaderResult)
 $pitch=[double]$ReaderResult.linePitch
 if($pitch -le 0){throw 'Positive observed line pitch required'}
 $raw=@($ReaderResult.rawTextRecords)
 $records=@($raw|Where-Object {$_.entityType -eq 'TEXT' -and $_.visibility -ne 'hidden' -and $_.rawText.Trim().Length -gt 0 -and (Get-LayoutRotation $_) -notin @('vertical','other')})
 $idx=@{};$boxes=@{};$numbers=@{};$paragraphMap=@{}
 foreach($r in $records){$idx[$r.id]=$r;$boxes[$r.id]=Get-TextLayoutBox $r;$numbers[$r.id]=Get-StructureNumber $r.rawText}
 foreach($p in $ReaderResult.paragraphs){foreach($f in $p.textFragments){$paragraphMap[$f.id]=@($paragraphMap[$f.id])+@($p.paragraphId)}}
 $bounds=@();if($ReaderResult.PSObject.Properties['layoutBoundaries']){$bounds=@($ReaderResult.layoutBoundaries)}
 $reviews=New-Object 'Collections.Generic.List[object]';$relations=New-Object 'Collections.Generic.List[object]'
 $sections=New-Object 'Collections.Generic.List[object]';$items=New-Object 'Collections.Generic.List[object]'
 function Review($kind,$refs,$why){$reviews.Add([pscustomobject]@{modelType='ReviewItem';type=$kind;sourceRefs=@($refs);reason=$why;status='open';automaticResolution=$false})}
 function SameColumn($a,$b){$a.sourceSnapshot -eq $b.sourceSnapshot -and [math]::Abs($a.x-$b.x) -le 1.5*$pitch}
 function Separated($a,$b){
  if(Test-LayoutSeparation $a $b $bounds){return $true}
  if($boxes[$a.id] -and $boxes[$b.id]){return (Test-LayoutSeparation (Get-BoxReferencePoint $a $boxes[$a.id]) (Get-BoxReferencePoint $b $boxes[$b.id]) $bounds)}
  return $false
 }
 function ParaRefs($ids){@($ids|ForEach-Object {$paragraphMap[$_]}|Where-Object {$null -ne $_}|Select-Object -Unique)}
 $starts=@($records|Where-Object {$numbers[$_.id] -and $numbers[$_.id].pattern -eq 'dotted'}|Sort-Object sourceSnapshot,x,@{e='y';Descending=$true})
 foreach($start in $starts){
  $n=$numbers[$start.id];$id=$start.id+':section'
  $next=@($starts|Where-Object { (SameColumn $start $_) -and $_.y -lt $start.y-.2*$pitch -and $numbers[$_.id].depth -le $n.depth}|Sort-Object y -Descending|Select-Object -First 1)
  $endY=if($next.Count){$next[0].y}else{$start.y-30*$pitch}
  $nextSame=if($next.Count -and $numbers[$next[0].id].depth -eq $n.depth){$next[0].id+':section'}else{$null}
  $candidates=@($records|Where-Object {$_.sourceSnapshot -eq $start.sourceSnapshot -and $_.y -lt $start.y-.12*$pitch -and $_.y -gt $endY+.12*$pitch -and (($_.x -ge $start.x-1.5*$pitch -and $_.x -le $start.x+2*$pitch) -or (Get-BoxXOverlap $boxes[$start.id] $boxes[$_.id]) -ge .65)}|Sort-Object @{e='y';Descending=$true},x)
  $fragments=New-Object 'Collections.Generic.List[string]';$fragments.Add($start.id)
  $last=$start;$stop=if($next.Count){'next_number_boundary'}else{'observation_window_boundary'};$tail=$false
  foreach($c in $candidates){
   if($ReaderResult.PSObject.Properties['coverageClosure'] -and $ReaderResult.coverageClosure -and $numbers[$c.id] -and $numbers[$c.id].pattern -eq 'chinese'){$stop='structural_title_boundary';break}
   if($numbers[$c.id] -and $numbers[$c.id].pattern -eq 'dotted'){continue}
   if($c.rawText -notmatch '[\p{IsCJKUnifiedIdeographs}A-Za-z]' -and !$numbers[$c.id]){continue}
   if(Separated $last $c){$stop='geometry_boundary';$tail=$true;break}
   if($last.y-$c.y -gt 2*$pitch){$stop='spacing_gap';$tail=$true;break}
   if([math]::Abs($last.y-$c.y) -lt .12*$pitch){$stop='same_line_order_ambiguous';$tail=$true;Review hierarchy_ambiguity @($id,$last.id,$c.id) 'Horizontal list or competing column order';break}
   if($boxes[$last.id] -and $boxes[$c.id] -and ($boxes[$c.id].height -gt 1.4*$boxes[$last.id].height -or $boxes[$c.id].height -lt .65*$boxes[$last.id].height)){$stop='text_height_change';$tail=$true;break}
   $fragments.Add($c.id);$last=$c
  }
  $section=[pscustomobject]@{modelType='SectionCandidate';sectionId=$id;numberingRaw=$n.raw;numberingPattern=$n.pattern;numberingParts=$n.parts;titleFragmentRefs=@($start.id);fragmentRefs=$fragments.ToArray();leadingFragmentRefs=@();paragraphRefs=@(ParaRefs $fragments.ToArray());subItemRefs=@();sourceRegion=@{scope='current_snapshot_local_design_text_region';sourceSnapshot=$start.sourceSnapshot;pageAssignment=$null;regionRefs=@($ReaderResult.regions|Where-Object {$_.paragraphIds|Where-Object {$_ -in (ParaRefs $fragments.ToArray())}}|ForEach-Object regionId)};boundaryCandidate=@{nextSameLevelCandidate=$nextSame;nextBoundaryFragmentRef=if($next.Count){$next[0].id}else{$null};basis=$stop};hierarchyStatus='candidate';completeness=$null}
  $sections.Add($section)
  $section|Add-Member readingOrderRefs @($section.paragraphRefs|ForEach-Object {@{paragraphRef=$_;field='readingOrderCandidate'}})
  $section.sourceRegion.anchorRef=$start.id
  $section.sourceRegion.columnBasis='numbered_start_position_and_text_bbox_candidate'
  $section.sourceRegion.observedYRange=@($last.y,$start.y)
  $markers=@($fragments|Where-Object {$numbers[$_] -and $numbers[$_].pattern -ne 'dotted'})
  $local=New-Object 'Collections.Generic.List[object]';$stack=New-Object 'Collections.Generic.List[object]'
  foreach($fid in $markers){
   $f=$idx[$fid];$num=$numbers[$fid];$parent=$id;$parentRec=$start;$alternative=@();$nested=$false
   for($k=$stack.Count-1;$k -ge 0;$k--){if($stack[$k].numberingPattern -eq $num.pattern){$parent=$stack[$k].parentCandidates[0];while($stack.Count -gt $k){$stack.RemoveAt($stack.Count-1)};break}}
   if($stack.Count){
    $prev=$stack[$stack.Count-1];$pr=$idx[$prev.fragmentRefs[0]]
    if($num.ordinal -eq 1 -and $num.pattern -ne $prev.numberingPattern -and $f.x-$pr.x -gt .5*$(if($boxes[$pr.id]){$boxes[$pr.id].height}else{$pitch/2}) -and $pr.rawText -match '[:：]\s*$'){$parent=$prev.subItemId;$parentRec=$pr;$nested=$true}
    elseif($parent -eq $id -and $num.pattern -ne $prev.numberingPattern){$alternative=@($prev.subItemId);Review numbering_format_change @($id,$fid) 'Changed marker style without a proven nested lead-in'}
   }
   if($parent -ne $id){$parentItem=@($local|Where-Object subItemId -EQ $parent);if($parentItem.Count){$parentRec=$idx[$parentItem[0].fragmentRefs[0]]}}
   $family=@($markers|Where-Object {$numbers[$_].pattern -eq $num.pattern})
   $seq=@($family|ForEach-Object {$numbers[$_].ordinal});$sequence=($seq.Count -ge 2 -and $seq[0] -eq 1)
   $overlap=Get-BoxXOverlap $boxes[$start.id] $boxes[$fid]
   $lead=(@($fragments|Where-Object {$idx[$_].y -gt $f.y}|ForEach-Object {$idx[$_].rawText}) -join '') -match '下列|如下|[:：]'
   $supported=($sequence -and ($lead -or $seq.Count -ge 3 -or $nested) -and ($overlap -ge .5 -or [math]::Abs($f.x-$start.x) -le 2*$pitch) -and !$alternative.Count)
   $item=[pscustomobject]@{modelType='SubItemCandidate';subItemId=$fid+':subitem:'+ $id;numberingRaw=$num.raw;numberingPattern=$num.pattern;ordinalCandidate=$num.ordinal;fragmentRefs=@($fid);paragraphRefs=@(ParaRefs @($fid));siblingOrderCandidate=$null;parentCandidates=@($parent)+$alternative;status=if($supported){'supported'}else{'ambiguous'}}
   $local.Add($item);$items.Add($item);$stack.Add($item)
   $evidence=@{numberingPattern=$num.pattern;numberingDepth=$num.depth;indentation=$f.x-$parentRec.x;bboxOverlap=$overlap;textHeight=if($boxes[$fid]){$boxes[$fid].height}else{$null};lineSpacing=$pitch;siblingSequence=$seq;parentPosition=@($parentRec.x,$parentRec.y);lexicalLeadIn=$lead;geometryBoundary='no_crossing_in_observed_fragment_chain';nextSameLevelCandidate=$nextSame;nestedLeadIn=$nested}
   $position=[array]::IndexOf($family,$fid)
   $evidence.previousSiblingRef=if($position -gt 0){$family[$position-1]}else{$null}
   $evidence.nextSiblingRef=if($position+1 -lt $family.Count){$family[$position+1]}else{$null}
   $opposing=@();if(!$sequence){$opposing+=@('no supported sibling series beginning at one')};if($alternative.Count){$opposing+=@('competing parent/style transition')}
   $relations.Add([pscustomobject]@{modelType='ParentChildRelationCandidate';parentRef=$parent;childRef=$item.subItemId;supportingEvidence=@($evidence);contradictingEvidence=$opposing;alternativeParents=$alternative;relationStatus=if($supported){'supported'}else{'ambiguous'}})
   if(!$supported){Review parent_unresolved @($item.subItemId,$parent) 'Marker alone or competing parent is insufficient'}
  }
  $active=$null
  foreach($fid in $fragments){
   $found=@($local|Where-Object {$_.fragmentRefs[0] -eq $fid})
   if($found.Count){$active=$found[0];continue}
   if($active){$active.fragmentRefs+=@($fid)}else{$section.leadingFragmentRefs+=@($fid)}
  }
  foreach($item in $local){$item.paragraphRefs=@(ParaRefs $item.fragmentRefs)}
  $section.subItemRefs=@($local|Where-Object {$_.parentCandidates[0] -eq $id}|ForEach-Object subItemId)
  $missing=@();$invalid=$false
  foreach($g in @($local|Group-Object {$_.parentCandidates[0]+'|'+$_.numberingPattern})){
   $j=0;$previous=0
   foreach($item in $g.Group){$j++;$item.siblingOrderCandidate=$j
    if($null -eq $item.ordinalCandidate){$invalid=$true;continue}
    if($item.ordinalCandidate -ne $previous+1){$invalid=$true;$missing+=,@{after=$previous;observed=$item.ordinalCandidate;parent=$item.parentCandidates[0]};Review numbering_gap @($id,$item.subItemId) 'Observed sequence discontinuity; no renumbering'}
    $previous=$item.ordinalCandidate
   }
  }
  $uncovered=@($fragments|Where-Object {!$paragraphMap.ContainsKey($_)})
  $complete=if($tail){'incomplete'}elseif(!$nextSame -or $invalid -or @($local|Where-Object status -NE supported).Count){'unresolved'}else{'likely_complete'}
  $section.completeness=[pscustomobject]@{modelType='CompletenessCandidate';completeness=$complete;nextSameLevelCandidate=$nextSame;missingSiblingCandidate=$missing;terminationEvidence=@($section.boundaryCandidate);uncertaintyReason=@('local candidate scope, page identity unresolved; not exhaustive CAD coverage');paragraphCoverage=if($uncovered.Count){'incomplete'}else{'covered_by_existing_paragraphs'};uncoveredFragmentRefs=$uncovered;readingOrderIndependent=$true}
  if($tail -or $uncovered.Count){Review suspected_truncation (@($id)+$uncovered) 'Existing paragraph coverage or observed section chain incomplete'}
  if(!$nextSame){Review next_same_level_unresolved @($id) 'No next same-depth section in observed local column'}
 }
 foreach($a in $sections){
  $r=$idx[$a.titleFragmentRefs[0]]
  $duplicates=@($sections|Where-Object {$_.sectionId -ne $a.sectionId -and $_.numberingRaw -eq $a.numberingRaw -and (SameColumn $r $idx[$_.titleFragmentRefs[0]])})
  if($duplicates.Count){Review duplicate_numbering (@($a.sectionId)+@($duplicates.sectionId)) 'Same raw numbering in local column; retained separately';$a.hierarchyStatus='ambiguous';$a.completeness.completeness='unresolved'}
  if($a.numberingParts.Count -gt 2){
   $prefix=($a.numberingParts[0..($a.numberingParts.Count-2)] -join '.')
   $parents=@($sections|Where-Object {
    $pr=$idx[$_.titleFragmentRefs[0]]
    $endRef=$_.boundaryCandidate.nextBoundaryFragmentRef
    $lower=if($endRef){$idx[$endRef].y}else{$pr.y-30*$pitch}
    $_.numberingRaw -eq $prefix -and (SameColumn $r $pr) -and $pr.y -gt $r.y -and $r.y -gt $lower
   }|Sort-Object @{e={$idx[$_.titleFragmentRefs[0]].y}})
   if($parents.Count -eq 1 -and !(Separated $idx[$parents[0].titleFragmentRefs[0]] $r)){
    $relations.Add([pscustomobject]@{modelType='ParentChildRelationCandidate';parentRef=$parents[0].sectionId;childRef=$a.sectionId;supportingEvidence=@('numeric_prefix','greater_depth','same_column','parent_above','no_detected_separator');contradictingEvidence=@();alternativeParents=@();relationStatus='supported'})
   }elseif($parents.Count -gt 1){Review hierarchy_ambiguity (@($a.sectionId)+@($parents.sectionId)) 'Multiple prefix parents'}else{Review parent_unresolved @($a.sectionId) 'Prefix parent not established in this local column'}
  }
 }
 $unassigned=@(foreach($r in $raw){if(!$paragraphMap.ContainsKey($r.id)){[pscustomobject]@{modelType='UnassignedStructureFragmentCandidate';sourceRef=$r.id;sourceSnapshot=$r.sourceSnapshot;status='unassigned_to_paragraph';numberingCandidate=if($numbers.ContainsKey($r.id)){$numbers[$r.id]}else{$null}}}})
 [pscustomobject]@{modelType='DocumentHierarchyCandidate';version='0.1-experimental';scope='current_snapshot_local_design_text_region';sourceSnapshots=@($raw.sourceSnapshot|Select-Object -Unique);sections=$sections.ToArray();subItems=$items.ToArray();relations=$relations.ToArray();unassignedFragments=$unassigned;reviewItems=$reviews.ToArray();designStatements=@();circuits=@();quantities=@();limitations=@('near-horizontal top-level TEXT only','page assignment unresolved','same-line lists require review','no automatic semantic inheritance','completeness never automatically complete')}
}
Export-ModuleMember -Function Get-StructureNumber,Find-DocumentHierarchyCandidates
