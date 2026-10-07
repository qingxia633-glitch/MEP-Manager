Set-StrictMode -Version 2
Import-Module (Join-Path $PSScriptRoot 'ProjectDesignKnowledge.psm1')

Import-Module (Join-Path $PSScriptRoot 'LayoutReader.psm1')
Import-Module (Join-Path $PSScriptRoot 'BBoxContinuity.psm1')
Import-Module (Join-Path $PSScriptRoot 'ParagraphSemantics.psm1')
function Read-DesignTextSnapshot {
 param([Parameter(Mandatory)][string]$Path)
 $text=[IO.File]::ReadAllText((Resolve-Path -LiteralPath $Path));$hash=(Get-FileHash -LiteralPath $Path).Hash
 function F($r,$k){[regex]::Match($r,'(?m)^'+$k+'=(.*?)\r?$').Groups[1].Value.Trim('"')}
 if((F $text AcquisitionMode) -ne 'ModelSpaceTopLevelAllLayers' -or $text -notmatch '(?m)^END_OF_REPORT'){throw 'Complete all-layer snapshot required'}
 $doc=F $text DWG;$items=@()
 foreach($m in [regex]::Matches($text,'(?ms)^EntityHandle=.*?(?=^EntityHandle=|^LayerEntityCount=|^LAYER_END|\z)')){
  $r=$m.Value;$type=F $r DXF_Type;$h=F $r EntityHandle
  if($type -in @('TEXT','MTEXT')){
   $p=[regex]::Match($r,'(?m)^Insertion_WCS=\(([-\d.]+) ([-\d.]+) ([-\d.]+)\)')
   if($p.Success){$items+=,[pscustomobject]@{id=($hash+':'+$h);handle=$h;parentHandle=$null;entityType=$type;rawText=(F $r Text_RAW);x=[double]::Parse($p.Groups[1].Value,[cultureinfo]::InvariantCulture);y=[double]::Parse($p.Groups[2].Value,[cultureinfo]::InvariantCulture);layer=(F $r Layer);coordinateRaw=$p.Value;sourceDocument=$doc;sourceSnapshot=$hash;rawRecord=$r;visibility='unknown';formattingStatus=if($type -eq 'MTEXT'){'not_evaluated'}else{'plain_candidate'}}}
  }
  if($type -eq 'INSERT'){
   foreach($a in [regex]::Matches($r,'(?m)^Attribute_DXF=(.*)')){
    $d=$a.Groups[1].Value;$p=[regex]::Match($d,'\(10 ([-\d.]+) ([-\d.]+) ([-\d.]+)\)');$ah=[regex]::Match($d,'\(5 \. "([^"]+)"\)').Groups[1].Value
    if($p.Success -and $ah){$items+=,[pscustomobject]@{id=($hash+':'+$ah);handle=$ah;parentHandle=$h;entityType='ATTRIB';rawText=[regex]::Match($d,'\(1 \. "([^"]*)"\)').Groups[1].Value;x=[double]::Parse($p.Groups[1].Value,[cultureinfo]::InvariantCulture);y=[double]::Parse($p.Groups[2].Value,[cultureinfo]::InvariantCulture);layer=[regex]::Match($d,'\(8 \. "([^"]*)"\)').Groups[1].Value;coordinateRaw=$p.Value;sourceDocument=$doc;sourceSnapshot=$hash;rawRecord=$d;visibility=if([regex]::Match($d,'\(70 \. (\d+)\)').Success -and ([int][regex]::Match($d,'\(70 \. (\d+)\)').Groups[1].Value -band 1)){'hidden'}else{'not_flagged_hidden'};formattingStatus='plain_candidate'}}
   }
  }
 }
 [pscustomobject]@{sourceDocument=$doc;sourceSnapshot=$hash;readErrorCount=(F $text ReadErrorCount);textRecords=$items;geometryRecords=@(Read-LayoutGeometry $text $hash);coverage='top_level_text_and_attached_attributes_only'}
}
function Find-DesignStatementCandidates {
 param([Parameter(Mandatory)][object[]]$Records,[string]$ProjectId='local-project',[object[]]$LocalConflicts=@(),[object[]]$Geometry=@(),[switch]$LayoutAware,[switch]$CoverageClosure)
 if($CoverageClosure -and !$LayoutAware){throw 'CoverageClosure requires LayoutAware'}
 $reviews=New-Object 'Collections.Generic.List[object]'
 function Review($kind,$subject,$facts){$reviews.Add([pscustomobject]@{modelType='ReviewItem';type=$kind;subject=$subject;sourceEvidence=$facts;status='open';humanDecision='pending';invalidationDependencies=@($subject);automaticResolution=$false})}
 $body=@($Records|Where-Object {$_.visibility -ne 'hidden' -and $_.rawText.Length -ge 12 -and $_.rawText -match '[\p{IsCJKUnifiedIdeographs}]' -and $_.formattingStatus -eq 'plain_candidate'})
 if($LayoutAware){$body=@($body|Where-Object {$_.entityType -ne 'ATTRIB' -and (Get-LayoutRotation $_) -notin @('vertical','other')})}
 $gaps=@(foreach($g in ($body|Group-Object {($_.sourceSnapshot+':'+[math]::Round($_.x,3))})){
  $ys=@($g.Group.y|Sort-Object -Descending -Unique);for($i=1;$i -lt $ys.Count;$i++){if($ys[$i-1]-$ys[$i] -gt 0){[math]::Round($ys[$i-1]-$ys[$i],3)}}
 })
 if(!$gaps.Count){return [pscustomobject]@{regions=@();paragraphs=@();reviewItems=@([pscustomobject]@{type='line_spacing_unresolved';status='open'});rawTextRecords=$Records;circuits=@();quantities=@()}}
 $pitch=[double](($gaps|Group-Object|Sort-Object Count -Descending|Select-Object -First 1).Name)
 $boundaries=@();if($LayoutAware){$boundaries=@(Get-LayoutBoundaries $Geometry $pitch)}
 if($CoverageClosure){
  $layoutSeed=Complete-LayoutResult ([pscustomobject]@{regions=@();paragraphs=@();linePitch=$pitch;version='coverage'}) $Records $boundaries
  $grids=@($layoutSeed.layoutRegions|Where-Object roleCandidate -EQ table_grid_candidate)
  $body=@($Records|Where-Object {
   $t=$_
   $inGrid=@($grids|Where-Object {$b=$_.bounds;$t.x -ge $b.minX -and $t.x -le $b.maxX -and $t.y -ge $b.minY -and $t.y -le $b.maxY}).Count -gt 0
   $t.entityType -eq 'TEXT' -and $t.visibility -ne 'hidden' -and $t.rawText.Trim().Length -gt 0 -and $t.rawText -match '[\p{IsCJKUnifiedIdeographs}]' -and (Get-LayoutRotation $t) -notin @('vertical','other') -and !$inGrid
  })
 }
 $boxIndex=@{};if($LayoutAware){foreach($r in $body){$boxIndex[$r.id]=Get-TextLayoutBox $r}}
 $starts=@($body|Where-Object {$_.rawText -match '^\s*\d+(?:\.\d+)+(?:[.、\s]|[\p{IsCJKUnifiedIdeographs}])'})
 $paragraphs=@();$index=0
 foreach($start in ($starts|Sort-Object sourceSnapshot,x,@{e='y';Descending=$true})){
  $startBox=$boxIndex[$start.id]
  $column=@($body|Where-Object {$_.sourceSnapshot -eq $start.sourceSnapshot -and $_.y -le $start.y -and (($_.x -ge $start.x-1.4*$pitch -and $_.x -le $start.x+0.2*$pitch) -or ($LayoutAware -and $startBox -and (Get-BoxXOverlap $startBox $boxIndex[$_.id]) -ge .65))}|Sort-Object @{e='y';Descending=$true},x)
  $continuations=New-Object 'Collections.Generic.List[object]'
  $members=New-Object 'Collections.Generic.List[object]';$members.Add($start);$last=$start;$ambiguous=$false;$endBasis='observation_boundary';$nextFragment=$null
  foreach($r in $column){
   if($r.id -eq $start.id){continue}
   $nextFragment=$r.id
   $ce=$null
   if($LayoutAware){
    $prevBox=$boxIndex[$last.id];$nextBox=$boxIndex[$r.id]
    $ce=New-ContinuationEvidence $start $last $r $startBox $prevBox $nextBox $pitch $false
    $continuations.Add($ce)
    if(!$ce.legacyInsertionCompatible -and !$ce.acceptedBBoxExtension){
     $ce.decision='excluded_bbox_extension'
     continue
    }
    $blocked=Test-LayoutSeparation $last $r $boundaries
    if(!$blocked -and $prevBox -and $nextBox){$blocked=Test-LayoutSeparation (Get-BoxReferencePoint $last $prevBox) (Get-BoxReferencePoint $r $nextBox) $boundaries}
    $ce.separatorBlocked=$blocked;$ce.separatorCrossing=$blocked
    if($blocked){$ce.acceptedBBoxExtension=$false}
    if($blocked){$ce.decision='separator_blocked';$endBasis='geometry_separator';break}
    if($ce.bboxAvailable -and (!$ce.fontSizeCompatible -or $ce.titleCandidate)){$ce.decision='title_or_size_boundary';$endBasis='bbox_title_or_size_boundary';break}
   }
   if([math]::Abs($r.y-$last.y) -lt 0.12*$pitch){if($ce){$ce.decision='competing_same_line'};$ambiguous=$true;$endBasis='competing_same_line';break}
   if($r.rawText -match '^\s*(?:\d+(?:\.\d+)+(?:[.、\s]|[\p{IsCJKUnifiedIdeographs}])|[一二三四五六七八九十]+[.、])'){if($ce){$ce.decision='next_numbered_item'};$endBasis='next_numbered_item';break}
   if($last.y-$r.y -gt 1.65*$pitch){if($ce){$ce.decision='spacing_break'};$endBasis='spacing_break';break}
   if($CoverageClosure -and $r.rawText.Trim().Length -lt 12){
    $styleA=[regex]::Match($last.rawRecord,'(?m)^TextStyle=(.*)').Groups[1].Value
    $styleB=[regex]::Match($r.rawRecord,'(?m)^TextStyle=(.*)').Groups[1].Value
    $heightA=[regex]::Match($last.rawRecord,'(?m)^TextHeight=([\d.]+)').Groups[1].Value
    $heightB=[regex]::Match($r.rawRecord,'(?m)^TextHeight=([\d.]+)').Groups[1].Value
    $sizeKnown=$heightA -and $heightB -and [double]$heightB -ge .65*[double]$heightA -and [double]$heightB -le 1.4*[double]$heightA
    $shortOK=$ce.verticalSpacingConsistent -and $ce.indentationCompatible -and $ce.fontSizeCompatible -and $sizeKnown -and $ce.punctuationContinuation -and $ce.lexicalContinuation -and !$ce.separatorBlocked -and $styleA -and $styleB -and $styleA -eq $styleB -and $r.rawText -match '[。；;]\s*$'
    $ce|Add-Member shortContinuationCandidate $shortOK
    $ce|Add-Member shortContinuationEvidence @{columnBasis=$start.id;fontHeightCompatible=[bool]$sizeKnown;styleA=$styleA;styleB=$styleB;status='candidate';rule='spacing_layout_font_unfinished_previous_terminal_suffix_no_separator'}
    if(!$shortOK){$ce.decision='short_continuation_unresolved';$endBasis='unresolved';break}
   }
   if($r.x -gt $start.x-0.25*$pitch -and $last.rawText -match '[。；]\s*$'){if($ce){$ce.decision='new_indented_paragraph'};$endBasis='new_indented_paragraph';break}
   if($ce){$ce.decision='accepted'}
   $members.Add($r);$last=$r;$nextFragment=$null
  }
  if($CoverageClosure -and $members.Count -eq 1 -and $start.rawText.Trim().Length -lt 12){continue}
  if($members.Count -eq 1 -and $start.rawText -notmatch '[，。；：应宜可不得见]'){continue}
  $index++;$id='paragraph:'+ $index
  $confidence=if($ambiguous){'low'}elseif($endBasis -in @('next_numbered_item','new_indented_paragraph') -and $last.rawText -match '[。；]\s*$'){'high'}else{'medium'}
  $order=[pscustomobject]@{modelType='ReadingOrderCandidate';orderedFragmentIds=@($members.id);confidence=$confidence;evidence=@('vertical_descending','first_line_indentation','observed_repeated_X_line_pitch',('end:'+ $endBasis),('terminal_punctuation:'+ [bool]($last.rawText -match '[。；]\s*$')));unresolvedAlternatives=@();linePitch=$pitch}
  for($j=1;$j -lt $members.Count;$j++){$order.evidence+=@([pscustomobject]@{from=$members[$j-1].id;to=$members[$j].id;deltaX=$members[$j].x-$members[$j-1].x;deltaY=$members[$j-1].y-$members[$j].y;lineGapResidual=[math]::Abs(($members[$j-1].y-$members[$j].y)-$pitch);lexicalContinuationCandidate=($members[$j-1].rawText -notmatch '[。；]\s*$' -and $members[$j].rawText -match '^[\p{IsCJKUnifiedIdeographs}\d-]')})}
  if($ambiguous){$order.unresolvedAlternatives=@('same-line ordering or overlapping representation unresolved');Review 'multiple_reading_orders' $id @($members.ToArray(),$r)}
  if($confidence -ne 'high'){Review 'paragraph_boundary_uncertain' $id @($members.ToArray(),$endBasis)}
  $p=[pscustomobject]@{modelType='ParagraphCandidate';paragraphId=$id;number_RAW=[regex]::Match($start.rawText,'^\s*(\d+(?:\.\d+)+)').Groups[1].Value;startX=$start.x;topY=$start.y;bottomY=$last.y;layer=$start.layer;sourceDocument=$start.sourceDocument;sourceSnapshot=$start.sourceSnapshot;textFragments=$members.ToArray();readingOrderCandidate=$order;groupCandidate=$null;atomicStatements=@();conditions=@();exceptions=@();references=@();signalCandidates=@();status='candidate';regionId=$null}
  $p|Add-Member continuationEvidence $continuations.ToArray()
  if($CoverageClosure){
   $reason=switch($endBasis){'geometry_separator'{'geometry_boundary'}'spacing_break'{'vertical_gap'}'new_indented_paragraph'{'explicit_end_punctuation'}'observation_boundary'{'column_boundary'}'bbox_title_or_size_boundary'{'incompatible_indent'}'next_numbered_item'{'next_numbered_item'}default{'unresolved'}}
   $p|Add-Member termination ([pscustomobject]@{terminationReason=$reason;nextFragmentCandidate=$nextFragment;rejectionEvidence=@($continuations|Where-Object decision -NE accepted);rawReason=$endBasis;status='candidate'})
  }
  if(@($continuations|Where-Object {$_.acceptedBBoxExtension -and $_.decision -eq 'accepted'}).Count){Review 'bbox_continuity_candidate' $id @($continuations|Where-Object acceptedBBoxExtension)}
  $paragraphs+=,$p
 }
 # Regions are coherent column segments, not complete sheets or building contexts.
 $regions=New-Object 'Collections.Generic.List[object]'
 foreach($p in ($paragraphs|Sort-Object sourceSnapshot,startX,@{e='topY';Descending=$true})){
  $matches=@($regions|Where-Object {$_.sourceSnapshot -eq $p.sourceSnapshot -and [math]::Abs($_.referenceX-$p.startX) -lt 0.4*$pitch -and $p.topY -ge $_.bottomY-15*$pitch -and $p.bottomY -le $_.topY+15*$pitch})
  if($LayoutAware){$matches=@($matches|Where-Object {!(Test-LayoutSeparation ([pscustomobject]@{x=$_.referenceX;y=$_.bottomY;sourceSnapshot=$_.sourceSnapshot}) ([pscustomobject]@{x=$p.startX;y=$p.topY;sourceSnapshot=$p.sourceSnapshot}) $boundaries)})}
  if($matches.Count -eq 1){$reg=$matches[0];$reg.paragraphIds+=@($p.paragraphId);$reg.bottomY=[math]::Min($reg.bottomY,$p.bottomY);$reg.topY=[math]::Max($reg.topY,$p.topY)}
  else{$reg=[pscustomobject]@{modelType='DesignTextRegionCandidate';regionId=('text-region:'+($regions.Count+1));sourceSnapshot=$p.sourceSnapshot;sourceDocument=$p.sourceDocument;referenceX=$p.startX;topY=$p.topY;bottomY=$p.bottomY;paragraphIds=@($p.paragraphId);confidence='low';evidence=@();scope='unresolved';boundaryStatus='column_segment_candidate'};$regions.Add($reg)}
  $p.regionId=$reg.regionId
 }
 foreach($reg in $regions){
  $ps=@($paragraphs|Where-Object regionId -EQ $reg.regionId)
  $reg.confidence=if($ps.Count -ge 2){'medium'}else{'low'}
  $reg.evidence=@(@{kind='numbered_paragraph_count';value=$ps.Count},@{kind='aligned_text_count';value=@($ps|ForEach-Object {$_.textFragments}).Count},@{kind='observed_line_pitch';value=$pitch},@{kind='layer_clues_only';value=@($ps.layer|Select-Object -Unique)})
  $titles=@($Records|Where-Object {$_.sourceSnapshot -eq $reg.sourceSnapshot -and $_.rawText -match '(设计|施工).*说明' -and [math]::Abs($_.x-$reg.referenceX) -lt 25*$pitch -and $_.y -ge $reg.bottomY-10*$pitch -and $_.y -le $reg.topY+10*$pitch})
  $reg.evidence+=@(@{kind='title_or_titleblock_candidates';value=$titles;association='unresolved_not_nearest_assignment'},@{kind='table_frame_support';value='not_evaluated'})
  if($reg.confidence -eq 'low'){Review 'region_scope_uncertain' $reg.regionId $reg.evidence}
  $previous=$null
  foreach($p in ($ps|Sort-Object topY -Descending)){
   if($previous -and $p.number_RAW.Split('.').Count -gt $previous.number_RAW.Split('.').Count -and !$p.number_RAW.StartsWith($previous.number_RAW+'.')){Review 'section_number_hierarchy_mismatch' $p.paragraphId @($previous.textFragments[0],$p.textFragments[0])}
   $previous=$p
  }
 }
 $semantics=Invoke-ParagraphSemanticCandidates $paragraphs
 $paragraphs=@($semantics.paragraphs)
 foreach($review in $semantics.reviewItems){$reviews.Add($review)}
 foreach($r in $Records|Where-Object formattingStatus -EQ not_evaluated){Review 'formatted_text_unresolved' $r.id @($r)}
 foreach($conflict in $LocalConflicts){Review 'design_vs_local_conflict' 'external_conflict_input' @($conflict)}
 $result=[pscustomobject]@{modelType='DesignStatementReaderResult';version='0.1';projectId=$ProjectId;rawTextRecords=$Records;linePitch=$pitch;regions=$regions.ToArray();paragraphs=$paragraphs;reviewItems=$reviews.ToArray();circuits=@();connections=@();quantities=@();limitations=@('experimental column segmentation, not drawing-region truth','formatted MTEXT needs review','language signals are not rule semantics','no external reference resolution')}
 $result|Add-Member coverageClosure ([bool]$CoverageClosure)
 if($LayoutAware){
  Review 'rotation_coverage_unresolved' 'snapshot' @('Missing rotation fields are not verified horizontal')
  $result.reviewItems=$reviews.ToArray()
  Complete-LayoutResult $result $Records $boundaries
 }else{$result}
}
Export-ModuleMember -Function Read-DesignTextSnapshot,Find-DesignStatementCandidates
