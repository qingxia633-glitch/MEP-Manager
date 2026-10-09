Set-StrictMode -Version 2
Import-Module (Join-Path $PSScriptRoot 'SectionHierarchy.psm1')
Import-Module (Join-Path $PSScriptRoot 'LayoutReader.psm1')
function Get-ParagraphCoverage {
 param($Reader,$Hierarchy,[string]$SheetId,[object[]]$Columns=@(),[object[]]$LegendRegions=@(),[string[]]$TitleBlockHandles=@())
 $items=@();$gaps=@();$reviews=@()
 $grids=@($Reader.layoutRegions|Where-Object roleCandidate -EQ table_grid_candidate)
 foreach($r in $Reader.rawTextRecords){
  $ps=@($Reader.paragraphs|Where-Object {$_.textFragments.id -contains $r.id})
  $ss=@($Hierarchy.sections|Where-Object {$_.fragmentRefs -contains $r.id}|ForEach-Object sectionId)
  $sub=@($Hierarchy.subItems|Where-Object {$_.fragmentRefs -contains $r.id}|ForEach-Object subItemId)
  $cols=@($Columns|Where-Object {$c=$_;@($ps|Where-Object {$c.textRegionRefs -contains $_.regionId}).Count -gt 0}|ForEach-Object id)
  $grid=@($grids|Where-Object {$b=$_.bounds;$r.x -ge $b.minX -and $r.x -le $b.maxX -and $r.y -ge $b.minY -and $r.y -le $b.maxY})
  $legend=@($LegendRegions|Where-Object {$_.sourceHandles -contains $r.handle})
  $num=Get-StructureNumber $r.rawText;$reason=@();$evidence=@();$status='candidate'
  if($r.entityType -eq 'ATTRIB'){$d=if($TitleBlockHandles -contains $r.parentHandle){'title_block_metadata'}else{'excluded_with_reason'};$reason=@('attached_attribute_not_body');$evidence=@($r.parentHandle)}
  elseif(!$r.rawText.Trim()){$d='excluded_with_reason';$reason=@('empty_raw_text_preserved')}
  elseif($r.visibility -eq 'hidden'){$d='excluded_with_reason';$reason=@('hidden_not_body')}
  elseif($grid.Count){$d='table_content';$evidence=@($grid.id);$reason=@('grid_position_candidate_not_cell_semantics')}
  elseif($legend.Count){$d='legend_content';$evidence=@($legend.regionId)}
  elseif($ps.Count){$d='paragraph_member';$evidence=@($ps|ForEach-Object paragraphId);if($ps.Count -gt 1){$status='unresolved';$reason=@('multiple_paragraph_memberships')}}
  elseif($num -and $num.pattern -in @('chinese','dotted')){$d='section_title';$evidence=@($num);$reason=@('structural_fragment_not_forced_into_body')}
  elseif($num -and $r.rawText.Trim().Length -lt 12 -and $r.rawText -notmatch '[。；]'){$d='subitem_title';$evidence=@($num);$reason=@('numbered_fragment_parent_requires_evidence')}
  elseif((Get-LayoutRotation $r) -in @('vertical','other')){$d='non_body_annotation';$reason=@('rotated_text_separate_reading_flow')}
  else{$d='unresolved_body_candidate';$status='unresolved';$reason=@(if($r.entityType -eq 'MTEXT'){'mtext_body_support_not_expanded'}else{'no_supported_paragraph_or_structural_role'})}
  $item=[pscustomobject]@{modelType='RawTextDisposition';sheetId=$SheetId;columnScopeId=$cols;columnScopeStatus=if($cols.Count -eq 1){'candidate'}else{'unresolved'};rawEntityRef=$r.id;handle=$r.handle;rawText=$r.rawText;sourceSnapshot=$r.sourceSnapshot;disposition=$d;paragraphRef=@($ps|ForEach-Object paragraphId);structureRef=@($ss)+@($sub);supportingEvidence=$evidence;exclusionReason=$reason;status=$status}
  $items+=,$item
  if(($ss.Count -or $sub.Count) -and !$ps.Count -and $d -notin @('section_title','subitem_title','table_content','title_block_metadata','legend_content')){
   $gaps+=,[pscustomobject]@{modelType='CoverageGapCandidate';sheetId=$SheetId;rawEntityRef=$r.id;handle=$r.handle;kind='hierarchy_without_paragraph';structureRefs=@($ss)+@($sub);status='unresolved'}
  }
  elseif($d -eq 'unresolved_body_candidate'){$gaps+=,[pscustomobject]@{modelType='CoverageGapCandidate';sheetId=$SheetId;rawEntityRef=$r.id;handle=$r.handle;kind='body_role_unresolved';structureRefs=@();status='unresolved'}}
 }
 foreach($p in $Reader.paragraphs){foreach($a in $p.atomicStatements){if(!$a.rawText.Trim()){$reviews+=,[pscustomobject]@{type='empty_atomic_candidate';subject=$a.statementId;status='open';sourceParagraph=$p.paragraphId;automaticRepair=$false}}}}
 foreach($g in $gaps){$reviews+=,[pscustomobject]@{type='paragraph_coverage_gap';subject=$g.rawEntityRef;status='open';sourceGap=$g.kind;automaticRepair=$false}}
 [pscustomobject]@{modelType='ParagraphCoverageCandidate';sheetId=$SheetId;rawTextDispositions=$items;coverageGaps=$gaps;reviewItems=$reviews;dispositionCoverage=if($items.Count -eq $Reader.rawTextRecords.Count){'all_records_accounted_for'}else{'incomplete'};semanticCompleteness='not_asserted';formalEvidence=@();circuits=@();quantities=@()}
}
Export-ModuleMember -Function Get-ParagraphCoverage
