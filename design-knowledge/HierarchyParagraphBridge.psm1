Set-StrictMode -Version 2
Import-Module (Join-Path $PSScriptRoot 'BBoxContinuity.psm1')
Import-Module (Join-Path $PSScriptRoot 'LayoutReader.psm1')
function Get-BridgeStyle($r){[regex]::Match($r.rawRecord,'(?m)^TextStyle=(.*)').Groups[1].Value.Trim()}
function Get-BridgeColumns($r,$columns){
 $b=Get-TextLayoutBox $r
 @($columns|Where-Object {
  $c=$_;$insideY=$r.y -ge $c.bounds.minY -and $r.y -le $c.bounds.maxY
  $insideX=if($b){$b.minX -ge $c.bboxXMin -and $b.maxX -le $c.bboxXMax}else{$r.x -ge $c.bounds.minX -and $r.x -le $c.bounds.maxX}
  $insideY -and $insideX
 })
}
function Resolve-HierarchyParagraphBridge($InputResult){
 # Additive overlay: only pre-existing hierarchy gaps are eligible. Original paragraphs stay byte-equivalent.
 $r=$InputResult|ConvertTo-Json -Depth 80|ConvertFrom-Json
 $reader=$r.after;$h=$r.hierarchy;$coverage=$r.coverage
 $eligible=@($coverage.coverageGaps|Where-Object kind -In @('hierarchy_without_paragraph','hierarchy_paragraph_coverage_gap'))
 $allowed=@($eligible.rawEntityRef);$audit=@();$new=@();$pitch=[double]$reader.linePitch
 foreach($gap in $eligible){
  $t=$reader.rawTextRecords|Where-Object id -EQ $gap.rawEntityRef
  $box=Get-TextLayoutBox $t;$cols=@(Get-BridgeColumns $t $reader.textColumns)
  $sections=@($h.sections|Where-Object {$_.fragmentRefs -contains $t.id})
  $subs=@($h.subItems|Where-Object {$_.fragmentRefs -contains $t.id})
  $neighbors=@();$prev=$null;$next=$null
  if($cols.Count -eq 1){
   $neighbors=@($reader.rawTextRecords|Where-Object { $_.entityType -eq 'TEXT' -and $_.y -ge $cols[0].bounds.minY -and $_.y -le $cols[0].bounds.maxY -and $_.x -ge $cols[0].bounds.minX-$pitch -and $_.x -le $cols[0].bboxXMax -and (Get-BoxXOverlap (Get-TextLayoutBox $_) ([pscustomobject]@{minX=$cols[0].bboxXMin;maxX=$cols[0].bboxXMax})) -ge .65 }|Sort-Object @{Expression='y';Descending=$true},x)
   $at=[array]::IndexOf(@($neighbors.id),$t.id)
   if($at -gt 0){$prev=$neighbors[$at-1]};if($at -ge 0 -and $at+1 -lt $neighbors.Count){$next=$neighbors[$at+1]}
  }
  $reasons=@();$layout=@();$continuation=@();$hierarchy=@($sections|ForEach-Object sectionId)+@($subs|ForEach-Object subItemId)
  $classification='unresolved';$notRequired=$false;$groupKey=$t.id;$decision='unresolved'
  $direct=@($reader.paragraphs|ForEach-Object continuationEvidence|Where-Object sourceB -EQ $t.id)
  $stops=@($reader.paragraphs|Where-Object {$p=$_;@($sections|Where-Object {$_.fragmentRefs -contains $p.textFragments[0].id}).Count}|ForEach-Object { [pscustomobject]@{paragraphId=$_.paragraphId;termination=$_.termination} })
  if($t.entityType -ne 'TEXT' -or $t.visibility -eq 'hidden'){$reasons+='not_visible_text_body_candidate'}
  if($cols.Count -ne 1){$reasons+='column_scope_unresolved'}
  if($cols.Count -eq 1 -and @($sections|Where-Object {$_.sourceRegion.regionRefs -contains ($cols[0].id -replace ':column$','')}).Count -eq 0){$reasons+='hierarchy_column_disagreement'}
  if($prev -and $prev.sourceSnapshot -ne $t.sourceSnapshot){$reasons+='snapshot_mismatch'}
  $grid=@($reader.layoutRegions|Where-Object {$_.roleCandidate -eq 'table_grid_candidate' -and $t.x -ge $_.bounds.minX -and $t.x -le $_.bounds.maxX -and $t.y -ge $_.bounds.minY -and $t.y -le $_.bounds.maxY})
  if($grid.Count){$reasons+='grid_blocks_body_bridge'}
  if((Get-LayoutRotation $t) -ne 'horizontal'){$reasons+='nonhorizontal_body'}
  $prevBox=if($prev){Get-TextLayoutBox $prev}else{$null}
  $spacing=($prev -and $prev.y-$t.y -ge .35*$pitch -and $prev.y-$t.y -le 1.65*$pitch)
  $font=($box -and $prevBox -and $box.height -ge .65*$prevBox.height -and $box.height -le 1.4*$prevBox.height -and (Get-BridgeStyle $t) -and (Get-BridgeStyle $t) -eq (Get-BridgeStyle $prev))
  $blocked=$false
  if($prev){$blocked=(Test-LayoutSeparation $prev $t $reader.layoutBoundaries) -or (Test-LayoutSeparation (Get-BoxReferencePoint $prev $prevBox) (Get-BoxReferencePoint $t $box) $reader.layoutBoundaries)}
  $layout+= [pscustomobject]@{sameColumn=($cols.Count -eq 1);columnRefs=@($cols|ForEach-Object id);bbox=$box;previousBBox=$prevBox;fontStyleCompatible=[bool]$font;verticalSpacingConsistent=[bool]$spacing;separatorBlocked=[bool]$blocked;deltaX=if($prev){$t.x-$prev.x}else{$null};deltaY=if($prev){$prev.y-$t.y}else{$null};bboxOverlap=Get-BoxXOverlap $box $prevBox}
  if(!$spacing){$reasons+='spacing_or_inline_order_unresolved'}
  if(!$font){$reasons+='font_or_bbox_unresolved'}
  if($blocked){$reasons+='geometry_boundary'}
  # Pure labels can remain structures, but lack of a body interpretation is not a license to exclude text.
  $pureNumber=$t.rawText -match '^\s*(?:[（(]?\d+[）).、]?|[一二三四五六七八九十]+[.、])\s*$'
  if($pureNumber -and $subs.Count -eq 1 -and $subs[0].status -eq 'supported' -and !$reasons.Count){
   $classification='structural_title_only';$notRequired=$true;$decision='nonparagraph_structure';$reasons+='number_only_with_supported_structure_and_layout'
  }
  elseif($subs.Count -eq 1 -and $subs[0].status -eq 'supported'){
   $u=$subs[0];$siblings=@($h.subItems|Where-Object {$_.parentCandidates.Count -eq 1 -and $u.parentCandidates.Count -eq 1 -and $_.parentCandidates[0] -eq $u.parentCandidates[0]})
   $ordered=@($reader.rawTextRecords|Where-Object {$u.fragmentRefs -contains $_.id}|Sort-Object @{Expression='y';Descending=$true},x)
   $classification=if($ordered[0].id -eq $t.id){'missed_subitem_body'}else{'missed_continuation'}
   $groupKey=$u.subItemId
   if($siblings.Count -lt 2 -or $u.parentCandidates.Count -ne 1){$reasons+='sibling_or_parent_evidence_insufficient'}
   if(@($u.fragmentRefs|Where-Object {$_ -notin $allowed}).Count){$reasons+='subitem_contains_fragments_outside_bridge_scope'}
   if($classification -eq 'missed_continuation' -and (!$prev -or $prev.id -notin $u.fragmentRefs -or $prev.rawText -match '[。；;？！!?]\s*$')){$reasons+='continuation_not_supported'}
   $continuation+= [pscustomobject]@{kind=$classification;previousRef=if($prev){$prev.id}else{$null};subItemRef=$u.subItemId;siblingRefs=@($siblings.subItemId);parentRefs=@($u.parentCandidates);punctuationContinuation=($prev -and $prev.rawText -notmatch '[。；;？！!?]\s*$')}
   if(!$reasons.Count){$decision='supported_candidate'}
  }
  else{
   # Independent field-like prose needs a label, colon, completed sentence, unique section and completed predecessor.
   $labelledBody=$t.rawText -match '^\s*[^:：。；]{2,30}[:：].+[。；]\s*$'
   if($sections.Count -ne 1){$reasons+='multiple_section_parents'}
   if($subs.Count){$reasons+='subitem_relation_not_supported'}
   if($prev -and $prev.rawText -notmatch '[。；;？！!?]\s*$' -and $prev.id -notin $allowed){$reasons+='unfinished_previous_outside_bridge_scope';$classification='missed_continuation'}
   elseif($labelledBody -and $prev -and $prev.rawText -match '[。；;？！!?]\s*$'){
    $classification='independent_structural_body';$continuation+=[pscustomobject]@{kind='independent_body_not_append';previousRef=$prev.id;labelColonEvidence=$true;terminalPunctuation=$true}
    if(!$reasons.Count){$decision='supported_candidate'}
   }else{$reasons+='independent_body_boundary_unresolved'}
  }
  $audit+= [pscustomobject]@{modelType='HierarchyParagraphBridgeCandidate';rawEntityRef=$t.id;handle=$t.handle;rawText=$t.rawText;sheet=$coverage.sheetId;columnScope=@($cols|ForEach-Object id);hierarchyRole=if($subs.Count){'subitem_member'}else{'section_member'};parentSectionRefs=@($sections|ForEach-Object sectionId);parentSubItemRefs=@($subs|ForEach-Object subItemId);previousText=if($prev){$prev|Select-Object id,handle,rawText,x,y}else{$null};nextText=if($next){$next|Select-Object id,handle,rawText,x,y}else{$null};bbox=$box;textHeight=if($box){$box.height}else{$null};textStyle=Get-BridgeStyle $t;currentParagraphRejection=[pscustomobject]@{directDecisions=$direct;ancestorTerminations=$stops;absenceOfDirectDecision='not_evaluated_after_earlier_termination'};classification=$classification;groupKey=$groupKey;hierarchyEvidence=$hierarchy;layoutEvidence=$layout;continuationEvidence=$continuation;status=$decision;paragraphNotRequired=$notRequired;reasons=$reasons;paragraphRefs=@()}
 }
 # Do not partly admit a multiline item if any of its members failed the checks.
 foreach($group in @($audit|Group-Object groupKey)){
  $members=@($group.Group)
  if(@($members|Where-Object status -NE supported_candidate).Count){
   foreach($a in $members|Where-Object status -EQ supported_candidate){$a.status='unresolved';$a.reasons+='group_member_unresolved'};continue
  }
  $fragments=@($reader.rawTextRecords|Where-Object {$members.rawEntityRef -contains $_.id}|Sort-Object @{Expression='y';Descending=$true},x)
  $id='hierarchy-bridge-paragraph:'+$fragments[0].id;$col=$members[0].columnScope[0];$region=$col -replace ':column$',''
  $lastAudit=$members|Where-Object rawEntityRef -EQ $fragments[-1].id
  $p=[pscustomobject]@{modelType='ParagraphCandidate';paragraphId=$id;regionId=$region;sourceSnapshot=$fragments[0].sourceSnapshot;sourceDocument=$fragments[0].sourceDocument;textFragments=$fragments;readingOrderCandidate=[pscustomobject]@{orderedFragmentIds=@($fragments.id);confidence='medium';status='candidate';evidence=@($members.layoutEvidence)+@($members.continuationEvidence);unresolvedAlternatives=@()};status='candidate';semanticStatus='not_processed';atomicStatements=@();conditions=@();exceptions=@();references=@();signalCandidates=@();termination=[pscustomobject]@{terminationReason='hierarchy_item_boundary_candidate';nextFragmentCandidate=if($lastAudit.nextText){$lastAudit.nextText.id}else{$null};rejectionEvidence=@();status='candidate'}}
  $new+=,$p;foreach($a in $members){$a.paragraphRefs=@($id)}
 }
 $reader.paragraphs=@($reader.paragraphs)+$new
 foreach($a in $audit){
  $d=$coverage.rawTextDispositions|Where-Object rawEntityRef -EQ $a.rawEntityRef
  if($a.status -eq 'supported_candidate'){$d.disposition='paragraph_member';$d.paragraphRef=$a.paragraphRefs;$d.status='candidate';$d.exclusionReason=@();$d.supportingEvidence+=@($a.groupKey);$d.columnScopeId=$a.columnScope;$d.columnScopeStatus='candidate'}
  elseif($a.paragraphNotRequired){$d.disposition='structural_fragment';$d.status='candidate';$d.exclusionReason=$a.reasons;$d|Add-Member paragraphNotRequired $true -Force}
 }
 $coverage.coverageGaps=@($coverage.coverageGaps|Where-Object {$_.rawEntityRef -notin $allowed})+@(foreach($a in $audit|Where-Object status -EQ unresolved){[pscustomobject]@{modelType='CoverageGapCandidate';sheetId=$coverage.sheetId;rawEntityRef=$a.rawEntityRef;handle=$a.handle;kind='hierarchy_paragraph_coverage_gap';structureRefs=$a.hierarchyEvidence;status='unresolved';reasons=$a.reasons}})
 $coverage.reviewItems=@($coverage.reviewItems|Where-Object {$_.subject -notin $allowed})+@(foreach($a in $audit|Where-Object status -EQ unresolved){[pscustomobject]@{type='hierarchy_paragraph_coverage_gap';subject=$a.rawEntityRef;status='open';reasons=$a.reasons;automaticRepair=$false}})
 [pscustomobject]@{modelType='HierarchyParagraphBridgeResult';sourceSnapshot=$r.sourceSnapshot;identity=$r.identity;frame=$r.frame;after=$reader;hierarchy=$h;coverage=$coverage;bridgeCandidates=$audit;newParagraphs=$new;scope='existing_hierarchy_coverage_gaps_only';formalEvidence=@();circuits=@();quantities=@()}
}
Export-ModuleMember -Function Resolve-HierarchyParagraphBridge
