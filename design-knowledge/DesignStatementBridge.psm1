Set-StrictMode -Version 2
Import-Module (Join-Path $PSScriptRoot 'ParagraphSemantics.psm1')
Import-Module (Join-Path $PSScriptRoot 'ProjectDesignKnowledge.psm1')

function Test-BridgeSpanContainment($Inner,$Outer){
 if(!$Inner.Count){return $false}
 foreach($s in $Inner){
  if(!@($Outer|Where-Object {$_.fragmentRef -ceq $s.fragmentRef -and $_.sourceSnapshot -ceq $s.sourceSnapshot -and $_.start -le $s.start -and $_.start+$_.length -ge $s.start+$s.length}).Count){return $false}
 };return $true
}
function Get-AtomicSubSpans($Atomic,[int]$Start,[int]$Length){
 $offset=0
 foreach($s in $Atomic.sourceSpans){
  $lo=[math]::Max($Start,$offset);$hi=[math]::Min($Start+$Length,$offset+$s.length)
  if($hi -gt $lo){[pscustomobject]@{modelType='TextSpanReference';fragmentRef=$s.fragmentRef;handle=$s.handle;sourceSnapshot=$s.sourceSnapshot;start=$s.start+$lo-$offset;length=$hi-$lo;rawText=$s.rawText.Substring($lo-$offset,$hi-$lo);offsetUnit='UTF16_code_unit'}}
  $offset+=$s.length
 }
}
function ConvertTo-AutomaticDesignStatements {
 param($InputResult)
 $sem=Invoke-ParagraphSemanticCandidates $InputResult.after.paragraphs
 $statements=@();$reviews=@();$processing=@();$spanIndex=[ordered]@{};$allAtomic=@()
 $raw=@{};foreach($t in $InputResult.after.rawTextRecords){$raw[$t.id]=$t}
 function SpanRefs($spans){foreach($s in $spans){
  if(!$raw.ContainsKey($s.fragmentRef)){throw 'Span raw entity not available'}
  $t=$raw[$s.fragmentRef]
  if($t.handle -cne $s.handle -or $t.sourceSnapshot -cne $s.sourceSnapshot -or $s.start -lt 0 -or $s.length -le 0 -or $s.start+$s.length -gt $t.rawText.Length -or $t.rawText.Substring($s.start,$s.length) -cne $s.rawText){throw 'Span/raw evidence mismatch'}
  $id=$s.fragmentRef+':span:'+$s.start+':'+$s.length
  $spanIndex[$id]=$s; $id
 }}
 function Issue($kind,$subject,$refs,$reason){[pscustomobject]@{modelType='ReviewItem';type=$kind;subject=$subject;sourceRefs=@($refs);reason=$reason;status='open';humanDecision='pending';automaticResolution=$false}}
 foreach($p in $sem.paragraphs){
  $allAtomic+=@($p.atomicStatements)
  $processing+=,[pscustomobject]@{paragraphRef=$p.paragraphId;pipeline='Invoke-ParagraphSemanticCandidates';atomicRefs=@($p.atomicStatements|ForEach-Object statementId);status=if($p.atomicStatements.Count){'processed'}else{'blocked'};semanticUpgrade='candidate_only'}
  if(!$p.atomicStatements.Count){$reviews+=Issue 'reading_order_blocks_atomic_generation' $p.paragraphId @($p.textFragments.id) 'Existing splitter declines low confidence order';continue}
  $fragments=@($p.textFragments|ForEach-Object {$f=$_|Select-Object *;$f|Add-Member fragmentId $_.id -Force;$f})
  $region=[pscustomobject]@{regionId=$p.regionId;sheetRef=$InputResult.identity.sheetId;source=[pscustomobject]@{scope=[pscustomobject]@{documentApplicability='local_document_statement';buildingScope='unresolved';storeyScope='unresolved'}}}
  $group=[pscustomobject]@{groupId=$p.paragraphId;sourceRegion=$region;sourceDocument=$p.sourceDocument;sourceSnapshot=$p.sourceSnapshot;textFragments=$fragments}
  foreach($a in $p.atomicStatements){
   if(!$a.rawText.Trim()){$reviews+=Issue 'empty_atomic_candidate' $a.statementId @($a.sourceSpans.fragmentRef) 'Whitespace atomic retained, DesignStatement upgrade blocked';continue}
   $id=$p.sourceSnapshot+':design-statement:'+$a.statementId
   $bodyRefs=@(SpanRefs $a.sourceSpans)
   if(($a.sourceSpans.rawText -join '') -cne $a.rawText){throw 'Atomic raw text not reconstructed by source spans'}
   $entityRefs=@($a.sourceSpans.fragmentRef|Select-Object -Unique)
   $columnRefs=@($InputResult.coverage.rawTextDispositions|Where-Object {$_.rawEntityRef -in $entityRefs}|ForEach-Object columnScopeId|Select-Object -Unique)
   $sections=@($InputResult.hierarchy.sections|Where-Object {$s=$_;@($entityRefs|Where-Object {$_ -notin $s.fragmentRefs}).Count -eq 0 -and $s.sourceRegion.regionRefs -contains $p.regionId})
   $subs=@($InputResult.hierarchy.subItems|Where-Object {$u=$_;@($entityRefs|Where-Object {$_ -notin $u.fragmentRefs}).Count -eq 0})
   # Retain every context candidate. Only a unique section can contribute an automatic subject label.
   $subject='unresolved';$scopeSource='unresolved';$contextRefs=@()
   if($sections.Count -eq 1){foreach($ref in $sections[0].titleFragmentRefs){
    if(!$raw.ContainsKey($ref)){continue};$title=$raw[$ref]
    $m=[regex]::Match($title.rawText,'^\s*\d+(?:\.\d+)+[.、]?\s*(?<label>[^：:。；，,]{2,30})[:：]')
    if($m.Success -and $m.Groups['label'].Value -notmatch '应|宜|不得|详见|规定|要求|[为是]$' -and [regex]::Matches($m.Groups['label'].Value,'[（(]').Count -eq [regex]::Matches($m.Groups['label'].Value,'[）)]').Count){
     $subject=$m.Groups['label'].Value.Trim();$scopeSource='hierarchy'
     $contextRefs+=@(SpanRefs @([pscustomobject]@{modelType='TextSpanReference';fragmentRef=$title.id;handle=$title.handle;sourceSnapshot=$title.sourceSnapshot;start=$m.Groups['label'].Index;length=$m.Groups['label'].Length;rawText=$m.Groups['label'].Value;offsetUnit='UTF16_code_unit'}))
    }
   }}
   $conditions=@();$exceptions=@();$references=@();$alts=@();$purpose=$null;$attachmentIssues=@()
   foreach($c in $p.conditions){
    if(Test-BridgeSpanContainment $c.sourceSpans $a.sourceSpans){
     $bounded=($c.kind -eq 'qualitative_length' -or $c.rawText -match '^当.+时$|^若.+[，,]$' -or ($c.rawText -match '^对于.+[，,]$' -and $c.rawText -notmatch '应|宜|不得|采用|设置|安装|敷设'))
     if($bounded){$conditions+=,$c}else{$attachmentIssues+='condition_predicate_unresolved'}
    }
   }
   foreach($c in $p.exceptions){
    if(Test-BridgeSpanContainment $c.sourceSpans $a.sourceSpans){
     if($c.exceptionKind -eq 'unresolved' -or $a.statementTypeCandidate -notin @('requirement','installation_requirement','material_requirement') -or @($c.triggerConditionRefs|Where-Object {$_ -notin @($conditions|ForEach-Object conditionId)}).Count){$attachmentIssues+='exception_trigger_scope_unresolved'}
     else{$copy=$c|Select-Object *;$copy.appliesToStatement=$id;$copy.effectStatementRefs=@($id);$exceptions+=,$copy}
    }
   }
   foreach($c in $p.references){if(Test-BridgeSpanContainment $c.sourceSpans $a.sourceSpans){$references+=,$c}}
   # Conservative parenthesized alternative only. Bare "or" remains a signal.
   foreach($m in [regex]::Matches($a.rawText,'(?<left>[^，,。；;：:（）()、和与及\s]{1,12})[（(]或(?<right>[^（）()，,。；;]{1,12})[）)]')){
    $left=$m.Groups['left'];$right=$m.Groups['right']
    if($left.Value -match '应|宜|不得|采用|设置|^设|^为|^通过') {continue}
    $options=@([pscustomobject]@{rawText=$left.Value;sourceSpans=@(Get-AtomicSubSpans $a $left.Index $left.Length)},[pscustomobject]@{rawText=$right.Value;sourceSpans=@(Get-AtomicSubSpans $a $right.Index $right.Length)})
    $clause=New-AlternativeClause @(Get-AtomicSubSpans $a $m.Index $m.Length) $options
    $clause|Add-Member hostStatementRef $id;$clause|Add-Member attachmentBasis 'explicit_parentheses_or_two_bounded_options_within_atomic_span'
    $alts+=,$clause
   }
   foreach($signal in $p.signalCandidates|Where-Object signal -EQ '或'){
    if((Test-BridgeSpanContainment $signal.sourceSpans $a.sourceSpans) -and !@($alts|Where-Object {Test-BridgeSpanContainment $signal.sourceSpans $_.sourceSpans}).Count){$attachmentIssues+='alternative_signal_without_bounded_options'}
   }
   $m=[regex]::Match($a.rawText,'^(?<subject>[^，,。；;：:]+?)(?<connector>用以)(?<purpose>[^。；;]+)[。；;]?\s*$')
   if($m.Success){
    $purpose=New-PurposeClause @(Get-AtomicSubSpans $a $m.Groups['subject'].Index $m.Groups['subject'].Length) @(Get-AtomicSubSpans $a $m.Groups['purpose'].Index $m.Groups['purpose'].Length) @(Get-AtomicSubSpans $a $m.Groups['connector'].Index $m.Groups['connector'].Length)
    $purpose|Add-Member hostStatementRef $id;$purpose|Add-Member attachmentBasis 'bounded_subject_connector_goal_in_same_atomic'
   }elseif($a.statementTypeCandidate -eq 'purpose_statement'){$attachmentIssues+='purpose_arguments_unresolved'}
   $type=$a.statementTypeCandidate
   if($type -notin @('requirement','definition','installation_requirement','material_requirement','reference_statement','note','purpose_statement','unknown')){$type='unknown'}
   $weakType=($type -eq 'requirement' -and $a.rawText -notmatch '应(?!急|用)|宜|不得|可(?!靠)|(?<!建)设(?!计)')
   if($weakType){$type='unknown'}
   $s=New-DesignStatementCandidate $id $group $type $a.sourceSpans -Conditions $conditions -Alternatives $alts -Purpose $purpose -Exceptions $exceptions -References $references -SubjectScope $subject
   $scope=[pscustomobject]@{subjectScopeCandidate=$subject;scopeSource=$scopeSource;contextSpanRefs=$contextRefs;localSectionRefs=@($sections|ForEach-Object sectionId);localDocumentScope='local_document_statement';buildingScope='unresolved';storeyScope='unresolved';systemScopeCandidate='unresolved';applicability='unresolved';automaticApplication=$false}
   $coverageOK=@($entityRefs|Where-Object {$ref=$_;!@($InputResult.coverage.rawTextDispositions|Where-Object {$_.rawEntityRef -eq $ref -and $_.disposition -eq 'paragraph_member'}).Count}).Count -eq 0
   $reasons=@('instance_applicability_unresolved','semantic_split_candidate_not_rule')
   $status='partial'
   if($type -eq 'unknown'){$status='unresolved';$reasons+='statement_type_unresolved'}
   if($weakType){$reasons+='atomic_type_signal_only'}
   if($sections.Count -ne 1){$status='unresolved';$reasons+='section_context_unresolved'}
   if(!$coverageOK){$status='unresolved';$reasons+='paragraph_coverage_unresolved'}
   if($columnRefs.Count -ne 1){$status='unresolved';$reasons+='column_scope_reference_unresolved'}
   if($p.readingOrderCandidate.confidence -notin @('high','medium')){$status='unresolved';$reasons+='reading_order_unresolved'}
   if($a.rawText -notmatch '[。；;]\s*$'){$status='unresolved';$reasons+='atomic_termination_unresolved'}
   if(@($sections|Where-Object {$_.completeness.completeness -in @('unresolved','incomplete')}).Count){$reasons+='section_completeness_unresolved'}
   if($subs.Count -gt 1 -or @($subs|Where-Object status -NE supported).Count){$status='unresolved';$reasons+='subitem_context_unresolved'}
   $reasons+=@($attachmentIssues|Select-Object -Unique)
   $extra=[ordered]@{sheetId=$InputResult.identity.sheetId;drawingNumber=$InputResult.identity.drawingNumber;columnScopeRef=($p.regionId+':column');sectionRef=@($sections|ForEach-Object sectionId);subItemRef=@($subs|ForEach-Object subItemId);paragraphRef=$p.paragraphId;atomicRef=$a.statementId;sourceSpanRefs=$bodyRefs;sourceEntityHandles=@($a.sourceSpans.handle|Select-Object -Unique);rawText=$a.rawText;normalizedTextCandidate=$a.rawText.Trim();statementStatus=$status;semanticCompleteness=if($status -eq 'unresolved'){'unresolved'}else{'partial'};applicabilityScope=$scope;qualityEvidence=[pscustomobject]@{readingOrderConfidence=$p.readingOrderCandidate.confidence;paragraphCoverageSupported=$coverageOK;sourceTraceComplete=$true;hierarchyRefs=@($sections|ForEach-Object sectionId)+@($subs|ForEach-Object subItemId);sectionCompleteness=@($sections|ForEach-Object {$_.completeness.completeness});clauseAttachmentIssues=@($attachmentIssues|Select-Object -Unique)};statusReasons=$reasons}
   foreach($key in $extra.Keys){$s|Add-Member -NotePropertyName $key -NotePropertyValue $extra[$key] -Force}
   $s.columnScopeRef=if($columnRefs.Count -eq 1){$columnRefs[0]}else{$null}
   $s|Add-Member columnScopeCandidates $columnRefs
   $s|Add-Member textColumnRef ($p.regionId+':column')
   $s|Add-Member columnScopeBasis 'upstream_raw_text_disposition_reference'
   $s|Add-Member atomicStatementTypeCandidate $a.statementTypeCandidate
   $s|Add-Member clauseAttachments ([pscustomobject]@{basis='source_span_containment_and_local_syntax';conditionRefs=@($conditions|ForEach-Object conditionId);hostStatementRef=$id;automaticApplication=$false})
   $statements+=,$s
   foreach($why in $reasons|Select-Object -Unique){$reviews+=Issue $why $id $bodyRefs 'Candidate retained; no automatic application or adjudication'}
  }
  # Report extracted clauses crossing atomic boundaries rather than silently assigning to a nearby statement.
  foreach($c in @($p.conditions)+@($p.exceptions)+@($p.references)){
   $hosts=@($p.atomicStatements|Where-Object {$_.rawText.Trim() -and (Test-BridgeSpanContainment $c.sourceSpans $_.sourceSpans)})
   if($hosts.Count -ne 1){$reviews+=Issue 'clause_host_unresolved' $p.paragraphId @($c.sourceSpans.fragmentRef) 'Clause is not wholly contained in exactly one nonempty atomic'}
  }
 }
 [pscustomobject]@{modelType='DesignStatementBridgeResult';version='experimental-1';sourceSnapshot=$InputResult.sourceSnapshot;sheetRef=$InputResult.identity.sheetId;drawingNumber=$InputResult.identity.drawingNumber;paragraphProcessing=$processing;atomicStatements=$allAtomic;designStatements=$statements;sourceSpans=@(foreach($key in $spanIndex.Keys){[pscustomobject]@{spanId=$key;span=$spanIndex[$key]}});reviewItems=$reviews;upstreamSemanticReviews=$sem.reviewItems;formalEvidence=@();engineeringProperties=@();ruleReferences=@();quantityRules=@();circuits=@();quantities=@();limitations=@('candidate conversion, not instance applicability','parenthesized alternatives only; unbounded or remains signal','purpose requires explicit subject and goal around connector','no semantic splitter repair; blank atomics reviewed','no cross-drawing target resolution')}
}
Export-ModuleMember -Function ConvertTo-AutomaticDesignStatements
