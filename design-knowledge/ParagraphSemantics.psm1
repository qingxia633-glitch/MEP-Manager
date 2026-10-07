Set-StrictMode -Version 2
Import-Module (Join-Path $PSScriptRoot 'ProjectDesignKnowledge.psm1')
# Shared existing splitter: no paragraph discovery, hierarchy edits or new sentence rules.
function Invoke-ParagraphSemanticCandidates {
 param([object[]]$Paragraphs)
 if(!$Paragraphs -or !$Paragraphs.Count){return [pscustomobject]@{paragraphs=@();reviewItems=@()}}
 $paragraphs=($Paragraphs|ConvertTo-Json -Depth 80|ConvertFrom-Json)
 $reviews=New-Object 'Collections.Generic.List[object]'
 function Review($kind,$subject,$facts){$reviews.Add([pscustomobject]@{modelType='ReviewItem';type=$kind;subject=$subject;sourceEvidence=$facts;status='open';humanDecision='pending';invalidationDependencies=@($subject);automaticResolution=$false})}
 foreach($p in $paragraphs){
  $p.atomicStatements=@();$p.conditions=@();$p.exceptions=@();$p.references=@();$p.signalCandidates=@();$p|Add-Member groupCandidate $null -Force
  if($p.readingOrderCandidate.confidence -eq 'low'){continue}
  $joined=$p.textFragments.rawText -join ''
  $p.groupCandidate=[pscustomobject]@{modelType='DesignStatementGroupCandidate';groupId=$p.paragraphId;sourceRegion=$p.regionId;textFragments=$p.textFragments;readingOrderCandidate=$p.readingOrderCandidate;normalizedStatementCandidate=$joined;status='candidate'}
  # Offsets map through the joined candidate back into immutable source fragments.
  function Span([int]$at,[int]$length){$offset=0;foreach($f in $p.textFragments){$lo=[math]::Max($at,$offset);$hi=[math]::Min($at+$length,$offset+$f.rawText.Length);if($hi -gt $lo){[pscustomobject]@{modelType='TextSpanReference';fragmentRef=$f.id;handle=$f.handle;sourceSnapshot=$f.sourceSnapshot;start=($lo-$offset);length=($hi-$lo);rawText=$f.rawText.Substring($lo-$offset,$hi-$lo);offsetUnit='UTF16_code_unit'}};$offset+=$f.rawText.Length}}
  foreach($m in [regex]::Matches($joined,'[^。；]+[。；]?')){
   $kind=if($m.Value -match '(详见|参见|见.*图)'){'reference_statement'}elseif($m.Value -match '(用以|为保证)'){'purpose_statement'}elseif($m.Value -match '(安装|敷设)'){'installation_requirement'}elseif($m.Value -match '(应|宜|可|不得|设)'){'requirement'}else{'unknown'}
   $p.atomicStatements+=,[pscustomobject]@{modelType='AtomicStatementCandidate';statementId=($p.paragraphId+':'+$m.Index);rawText=$m.Value;sourceSpans=@(Span $m.Index $m.Length);statementTypeCandidate=$kind;semanticCompleteness='partial';scope='unresolved';status='candidate'}
  }
  $conditionMatches=@([regex]::Matches($joined,'较[长短]的[^，。；：]+'))+@([regex]::Matches($joined,'(?:当|若|对于)[^。；]+?(?:时|，)|[^，。；]+时，[^，。；]+?(?:不能|无法)[^，。；]+'))
  foreach($m in $conditionMatches){
   $kind=if($m.Value -match '^较[长短]'){'qualitative_length'}else{'general_predicate'}
   $p.conditions+=,(New-ApplicabilityCondition ($p.paragraphId+':condition:'+ $m.Index) @(Span $m.Index $m.Length) $kind)
  }
  foreach($m in [regex]::Matches($joined,'除[^。；，]+外|[^。；]+(?:不能|无法)[^。；]+(?:可|允许)[^。；]+')){
   $kind=if($m.Value -match '除.*注明.*外'){'override'}elseif($m.Value -match '不能|无法'){'conditional_exception'}else{'unresolved'}
   $p.exceptions+=,(New-ExceptionClause @(Span $m.Index $m.Length) $p.paragraphId $kind @($p.conditions|ForEach-Object {$_.conditionId}) @())
  }
  foreach($m in [regex]::Matches($joined,'当|若|对于|除|其它|或|应|宜|可|不得|详见|参见|用以|为保证')){$p.signalCandidates+=,[pscustomobject]@{signal=$m.Value;sourceSpans=@(Span $m.Index $m.Length);status='candidate';effectScope='unresolved'}}
  if($p.conditions.Count -or $p.exceptions.Count){Review 'condition_scope_uncertain' $p.paragraphId @($p.conditions,$p.exceptions)}
  if($joined -match '其它|其余'){Review 'remainder_set_uncertain' $p.paragraphId @($p.textFragments)}
  foreach($m in [regex]::Matches($joined,'(?:详见|参见|(?<![详参])见)[^，。；]+')){
   $raw=$m.Value;$name=$raw -replace '^(详见|参见|见)','';$type='unresolved'
   if($name -match '(?:图集|标准图|\d{2}[A-Z]+\d{2,}(?:-\d+)?)'){$type='external_standard'}elseif($name -match '系统图'){$type='system_drawing'}elseif($name -match '大样|详图'){$type='detail_drawing'}elseif($name -match '图'){$type='project_drawing'}
   $ref=New-StatementCrossDrawingReference @(Span $m.Index $m.Length) @() @() $type $name
   $ref.modelType='CrossDrawingReferenceCandidate'
   $ref|Add-Member -NotePropertyName referenceTypeCandidate -NotePropertyValue $type
   $ref|Add-Member -NotePropertyName status -NotePropertyValue candidate
   $p.references+=,$ref
   if($name -match '及|和|、|或'){Review 'multiple_reference_targets' $p.paragraphId @($ref)}
  }
 }
 [pscustomobject]@{paragraphs=$paragraphs;reviewItems=$reviews.ToArray()}
}
Export-ModuleMember -Function Invoke-ParagraphSemanticCandidates
