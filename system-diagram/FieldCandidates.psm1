Set-StrictMode -Version 2

function Get-FieldVisibility($Statement) {
 if($Statement.rawRecord -match '(?m)^AttributeTag='){
  $m=[regex]::Match($Statement.rawRecord,'\(70 \. (\d+)\)')
  if($m.Success){
   $flag=[int]$m.Groups[1].Value
   return [pscustomobject]@{state=if(($flag -band 1) -ne 0){'hidden_flag'}else{'not_flagged_hidden'};source='ATTRIB_DXF70';rawFlag=$flag;renderedVisibility='not_verified'}
  }
  return [pscustomobject]@{state='unknown';source='ATTRIB_missing_flags';rawFlag=$null;renderedVisibility='not_verified'}
 }
 # Current TEXT report does not export an evaluated display state. Never call
 # top-level TEXT human-confirmed visible merely because it was exported.
 if($Statement.rawRecord -match '(?m)^DXF_Type="(?:TEXT|MTEXT)"'){
  return [pscustomobject]@{state='text_visibility_not_exported';source='top_level_text';rawFlag=$null;renderedVisibility='not_verified'}
 }
 [pscustomobject]@{state='unknown';source='insufficient_record';rawFlag=$null;renderedVisibility='not_verified'}
}
function Get-FieldPoint($Statement) {
 # Only use ATTRIB alignment when the exported OCS is proven XY and the raw
 # justification codes make the alignment point meaningful. Keep old fields.
 if($Statement.rawRecord -match '(?m)^AttributeTag='){
  $n=[regex]::Match($Statement.rawRecord,'\(210 ([^)]+)\)').Groups[1].Value
  $xyz=@($n -split ' '|Where-Object {$_ -ne ''}|ForEach-Object {[double]::Parse($_,[cultureinfo]::InvariantCulture)})
  $h=[regex]::Match($Statement.rawRecord,'\(72 \. (\d+)\)')
  $v=[regex]::Match($Statement.rawRecord,'\(74 \. (\d+)\)')
  if($xyz.Count -eq 3 -and $xyz[0] -eq 0 -and $xyz[1] -eq 0 -and $xyz[2] -eq 1 -and $Statement.alignment.Count -eq 3 -and (($h.Success -and [int]$h.Groups[1].Value -ne 0) -or ($v.Success -and [int]$v.Groups[1].Value -ne 0))){
   return [pscustomobject]@{point=$Statement.alignment;type='ATTRIB_alignment_OCS_equal_WCS_XY';status='supported'}
  }
  return [pscustomobject]@{point=@();type='unsupported_attribute_coordinate_frame';status='unknown'}
 }
 [pscustomobject]@{point=$Statement.insertion;type='Insertion_WCS';status=if($Statement.insertion.Count -eq 3){'supported'}else{'unknown'}}
}
function Field-Distribution([object[]]$Samples,[string]$Property) {
 $values=@($Samples|ForEach-Object {$_.$Property}|Sort-Object)
 if(!$values.Count){return [pscustomobject]@{min=$null;max=$null;median=$null;distribution=@()}}
 $mid=[int][math]::Floor($values.Count/2)
 $median=if($values.Count % 2){$values[$mid]}else{($values[$mid-1]+$values[$mid])/2}
 [pscustomobject]@{min=$values[0];max=$values[-1];median=$median;distribution=@($Samples|ForEach-Object {[pscustomobject]@{sampleId=$_.id;value=$_.$Property}})}
}
function Field-Source($View,$Statement){
 [pscustomobject]@{localViewId=$View.localViewId;statementId=$Statement.id;handle=$Statement.handle;parentHandle=$Statement.parentHandle;rawText=$Statement.rawText;layer=$Statement.layer;sourceSnapshot=$Statement.sourceSnapshot}
}
function Get-DiagramFieldCandidates {
 [CmdletBinding()]
 param([object[]]$Views,[object[]]$Rules,[object[]]$Variants,[string]$ScopeId)
 if(!$Views.Count -or [string]::IsNullOrWhiteSpace($ScopeId)){throw 'Explicit views and scope required'}
 if(@($Views|Group-Object localViewId|Where-Object Count -gt 1).Count){throw 'Duplicate local view scope'}
 $source=$Views[0].sourceSnapshot;$fields=@();$samples=@();$layouts=@();$hypotheses=@();$columns=@();$unclassified=@()
 foreach($view in $Views){
  if($view.sourceSnapshot.sha256 -ne $source.sha256){throw 'Cannot pool different snapshots'}
  foreach($s in $view.statements){
   if($s.sourceSnapshot.sha256 -ne $source.sha256){throw 'Statement snapshot mismatch'}
   $visibility=Get-FieldVisibility $s;$point=Get-FieldPoint $s;$matched=$false
   foreach($rule in $Rules){
    if($s.rawText -notmatch $rule.pattern){continue};$matched=$true
    $id='F'+($fields.Count+1);$layout=@();$conflicts=@()
    foreach($rowId in $s.candidateRowIds){
     $row=@($view.rows|Where-Object rowId -eq $rowId)
     if($row.Count -ne 1){throw 'Invalid row reference'}
     $row=$row[0]
     if($point.status -eq 'supported'){
      $layout+=,[pscustomobject]@{localViewId=$view.localViewId;rowId=$rowId;rowAnchorHandle=$row.rowBasis.handle;referenceBasis='statement_point_minus_outer_INSERT_WCS_XY';referencePointType=$point.type;deltaX=($point.point[0]-$row.baselinePoint[0]);deltaY=($point.point[1]-$row.rowBaselineY);deltaZ_RAW=($point.point[2]-$row.baselinePoint[2]);alignmentEvidenceRefs=@($view.alignmentEvidence|Where-Object {$_.rowId -eq $rowId -and $_.sourceB -eq $s.handle}|ForEach-Object id)}
     }
    }
    if($s.candidateRowIds.Count -gt 1){$conflicts+=,'multiple_row_layout_candidates'}
    if($visibility.state -eq 'hidden_flag'){$conflicts+=,'hidden_attribute_not_visible_field_support'}
    $eligible=$visibility.state -in @('not_flagged_hidden','text_visibility_not_exported')
    $field=[pscustomobject]@{id=$id;modelType='FieldRoleCandidate';sourceStatement=(Field-Source $view $s);role=$rule.role;patternBasis=@();layoutEvidence=$layout;textPatternEvidence=@{ruleId=$rule.id;pattern=$rule.pattern;matchedRawText=$s.rawText;scope=$ScopeId;meaning='lexical_candidate_not_design_rule'};visibility=$visibility;visibleFieldSupport=$eligible;confidence=@{basis='lexical_match_plus_available_layout';probability=$null};status=if($conflicts.Count){'ambiguous'}else{'candidate'};conflicts=$conflicts}
    $fields+=,$field
    if($rule.band){foreach($l in $layout){
     $samples+=,[pscustomobject]@{id='P'+($samples.Count+1);fieldRoleId=$id;band=$rule.band;localViewId=$view.localViewId;rowId=$l.rowId;rowAnchorHandle=$l.rowAnchorHandle;sourceStatement=$field.sourceStatement;referencePointType=$l.referencePointType;deltaX=$l.deltaX;deltaY=$l.deltaY;layoutVariant='unresolved';usable=($eligible -and $s.candidateRowIds.Count -eq 1);exceptionReasons=$conflicts}
    }}
   }
   if(!$matched){$unclassified+=,(Field-Source $view $s)}
  }
 }
 # Layout variants are descriptive conditions supplied for the surveyed scope.
 foreach($view in $Views){foreach($row in $view.rows){
  $rf=@($fields|Where-Object {$_.sourceStatement.localViewId -eq $view.localViewId -and @($_.layoutEvidence|Where-Object rowId -eq $row.rowId).Count -gt 0})
  $variantNames=@()
  foreach($variant in $Variants){
   $ok=$true
   foreach($condition in $variant.conditions){
    $c=@($rf|Where-Object role -eq $condition.role)
    if($condition.PSObject.Properties.Name -contains 'textPattern'){$c=@($c|Where-Object {$_.sourceStatement.rawText -match $condition.textPattern})}
    if($condition.PSObject.Properties.Name -contains 'visibility'){$c=@($c|Where-Object {$_.visibility.state -eq $condition.visibility})}else{$c=@($c|Where-Object visibleFieldSupport)}
    # Multiple role rules must not multiply the same source statement count.
    $count=@($c|ForEach-Object {$_.sourceStatement.statementId}|Sort-Object -Unique).Count
    if($count -lt $condition.min -or $count -gt $condition.max){$ok=$false}
   }
   if($ok){$variantNames+=,$variant.name}
  }
  $name=if($variantNames.Count -eq 1){$variantNames[0]}elseif($variantNames.Count -gt 1){'ambiguous'}else{'unclassified'}
  $layouts+=,[pscustomobject]@{localViewId=$view.localViewId;rowId=$row.rowId;rowAnchorHandle=$row.rowBasis.handle;layoutVariant=$name;alternativeVariants=$variantNames;status='candidate';absenceMeaning='not_observed_in_supplied_window_not_engineering_absence'}
  foreach($sample in @($samples|Where-Object {$_.localViewId -eq $view.localViewId -and $_.rowId -eq $row.rowId})){$sample.layoutVariant=$name}
 }}
 foreach($band in @($samples|ForEach-Object band|Sort-Object -Unique)){
  $bs=@($samples|Where-Object band -eq $band);$support=@($bs|Where-Object usable);$exceptions=@($bs|Where-Object {-not $_.usable})
  $variantStats=@(foreach($g in @($support|Group-Object layoutVariant)){
   [pscustomobject]@{layoutVariant=$g.Name;deltaX=(Field-Distribution $g.Group 'deltaX');deltaY=(Field-Distribution $g.Group 'deltaY');sampleCount=$g.Count}
  })
  $p=[pscustomobject]@{id='C'+($columns.Count+1);modelType='ColumnPatternCandidate';sourceSnapshot=$source;scope=@{id=$ScopeId;localViewIds=@($Views|ForEach-Object localViewId);kind='explicit_survey_not_whole_project_rule'};normalizedReferenceBasis='statement_point_minus_each_outer_INSERT_WCS_XY_in_drawing_units';candidateRole=$band;deltaX=(Field-Distribution $support 'deltaX');deltaY=(Field-Distribution $support 'deltaY');frequency=@{statementCount=@($support|ForEach-Object {$_.sourceStatement.handle}|Sort-Object -Unique).Count;rowCount=@($support|ForEach-Object {$_.localViewId+'/'+$_.rowId}|Sort-Object -Unique).Count;totalSuppliedRows=$layouts.Count};horizontalOrder=$null;layoutVariant=$variantStats;supportingSamples=$support;exceptionSamples=$exceptions;exceptionPolicy='hidden_or_ambiguous_layout; numeric_spread_retained_not_clipped';confidence=@{basis='observed_distribution_only';probability=$null};status='candidate'}
  $columns+=,$p
  foreach($f in @($fields|Where-Object {$_.id -in $bs.fieldRoleId})){$f.patternBasis+=,$p.id}
 }
 $ordered=@($columns|Where-Object {$null -ne $_.deltaX.median}|Sort-Object {$_.deltaX.median})
 for($i=0;$i -lt $ordered.Count;$i++){$ordered[$i].horizontalOrder=[pscustomobject]@{rank=($i+1);basis='median_deltaX_descriptive_only';overlapAllowed=$true}}
 foreach($power in @($fields|Where-Object {$_.role -eq 'row_power_field' -and $_.visibleFieldSupport})){
  $targets=@();$evidence=@($power.id);$opposing=@('layout evidence does not determine electrical ownership');$missing=@('explicit power ownership or aggregation statement','independent diagram/engineering confirmation')
  foreach($l in $power.layoutEvidence){
   $targets+=,[pscustomobject]@{kind='row';localViewId=$l.localViewId;rowId=$l.rowId;status='candidate'}
   $identifiers=@($fields|Where-Object {$_.role -eq 'identifier/load-reference' -and $_.visibleFieldSupport -and $_.sourceStatement.localViewId -eq $l.localViewId -and @($_.layoutEvidence|Where-Object rowId -eq $l.rowId).Count -gt 0}|Group-Object {$_.sourceStatement.statementId}|ForEach-Object {$_.Group[0]})
   foreach($f in $identifiers){$targets+=,[pscustomobject]@{kind='representation';localViewId=$l.localViewId;rowId=$l.rowId;handle=$f.sourceStatement.handle;parentHandle=$f.sourceStatement.parentHandle;statementId=$f.sourceStatement.statementId;sourceSnapshot=$source;status='candidate'};$evidence+=,$f.id}
   if($identifiers.Count -gt 1){
    $targets+=,[pscustomobject]@{kind='identifier-group';localViewId=$l.localViewId;rowId=$l.rowId;members=@($identifiers|ForEach-Object sourceStatement);meaning='hypothetical_group_not_merged_object';status='candidate'}
    $opposing+=,'multiple independent identifier representations; shared field versus aggregate meaning unresolved'
   }elseif(!$identifiers.Count){$missing+=,'non-hidden identifier/load expression in supplied row window'}
  }
  $hypotheses+=,[pscustomobject]@{id='H'+($hypotheses.Count+1);modelType='BindingHypothesis';sourceSnapshot=$source;scopeId=$ScopeId;subject=$power.sourceStatement;role='row_power_field';candidateTargets=$targets;hypothesisType='row_field_ownership_alternatives';supportingEvidence=$evidence;opposingEvidence=$opposing;missingEvidence=$missing;status='unresolved'}
 }
 [pscustomobject]@{schemaVersion='1.0';modelType='SystemDiagramFieldCandidateModel';sourceSnapshot=$source;scopeId=$ScopeId;columnPatterns=$columns;fieldRoles=$fields;bindingHypotheses=$hypotheses;rowLayouts=$layouts;unclassifiedStatements=$unclassified;limitations=@('scoped lexical candidates, not universal rules','no confirmed binding','no evaluated rendering visibility','no electrical objects or quantities')}
}
Export-ModuleMember -Function Get-DiagramFieldCandidates
