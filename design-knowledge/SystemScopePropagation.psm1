Set-StrictMode -Version Latest
Import-Module (Join-Path $PSScriptRoot '../model-core/SystemOntology.psm1')
function Add-DesignSystemScopes {
 param($Statements,$Hierarchy,[Parameter(Mandatory)][string]$ProjectId)
 if(!$ProjectId -or $Statements.sourceSnapshot -ne $Hierarchy.sourceSnapshot -or $Statements.sheetRef -ne $Hierarchy.identity.sheetId){throw 'Registered project and matching snapshot/sheet required'}
 $r=$Statements|ConvertTo-Json -Depth 80|ConvertFrom-Json
 $raw=@{};foreach($f in $Hierarchy.after.rawTextRecords){$raw[$f.id]=$f}
 $reviews=@()
 foreach($s in $r.designStatements){
  $candidates=@();$contexts=@();$ownTypes=@();$titleTypes=@()
  foreach($sec in $Hierarchy.hierarchy.sections|Where-Object {$_.sectionId -in $s.sectionRef}){
   # Source membership is mandatory; no spatial-nearest or numbering-only inheritance.
   if(@($s.sourceSpans|Where-Object {$_.fragmentRef -notin $sec.fragmentRefs}).Count){continue}
   foreach($ref in $sec.titleFragmentRefs){if($raw.ContainsKey($ref)){
    $f=$raw[$ref];$title=$f.rawText -replace '^\s*[0-9]+(?:\.[0-9]+)*[.、]?\s*',''
    $isTitle=($title.Length -le 35 -and $title -notmatch '[，。；;：:]|采用|设置|安装|应|不得')
    if($isTitle){$contexts+=,[pscustomobject]@{text=$f.rawText;sourceType=if($s.sourceEntityHandles -contains $f.handle){'explicit_section_title'}else{'inherited_section_context'};section=$sec.sectionId;fragment=$f;offset=0}}
   }}
  }
  foreach($span in $s.sourceSpans){$contexts+=,[pscustomobject]@{text=$span.rawText;sourceType='statement_local_term';section=$null;fragment=$span;offset=$span.start}}
  # Paragraph evidence supports only the same paragraph, and cannot cross a section boundary.
  $paragraph=@($Hierarchy.after.paragraphs|Where-Object paragraphId -EQ $s.paragraphRef)
  $sectionFragments=@($Hierarchy.hierarchy.sections|Where-Object {$_.sectionId -in $s.sectionRef}|ForEach-Object fragmentRefs)
  if($paragraph.Count -eq 1){foreach($f in $paragraph[0].textFragments){
   if($sectionFragments.Count -and $f.id -notin $sectionFragments){continue}
   $contexts+=,[pscustomobject]@{text=$f.rawText;sourceType='paragraph_local_term';section=$null;fragment=$f;offset=0}
  }}
  $seen=@{}
  foreach($ctx in $contexts){foreach($hit in @(Find-SystemAlias $ctx.text)){
   $f=$ctx.fragment;$handle=$f.handle;$start=$ctx.offset+$hit.start;$key=$ctx.sourceType+':'+$handle+':'+$start+':'+$hit.canonicalSystemTypeCandidate
   if($seen.ContainsKey($key)){continue};$seen[$key]=$true
   $ref=[pscustomobject]@{sourceSnapshot=$s.sourceSnapshot;handle=$handle;start=$start;length=$hit.length;rawText=$hit.rawTerm;offsetUnit='UTF16_code_unit'}
   $candidates+=,[pscustomobject]@{modelType='SystemScopeCandidate';systemScopeId=$s.statementId+':system-scope:'+ $candidates.Count;canonicalSystemTypeCandidate=$hit.canonicalSystemTypeCandidate;rawSystemText=$hit.rawTerm;sourceType=$ctx.sourceType;sourceRefs=@($ref);sourceSectionRef=$ctx.section;sourceParagraphRef=$s.paragraphRef;supportingEvidence=@('ontology_alias:'+ $hit.ontologyVersion,'same_source_context');contradictingEvidence=@();scopeInheritanceCandidate=[pscustomobject]@{status=if($ctx.sourceType -eq 'inherited_section_context'){'candidate'}else{'not_required'};crossSectionPropagation=$false};confidence='partial';status='candidate'}
   if($ctx.sourceType -eq 'statement_local_term'){$ownTypes+=$hit.canonicalSystemTypeCandidate}
   if($ctx.sourceType -match 'section'){$titleTypes+=$hit.canonicalSystemTypeCandidate}
  }}
  $types=@($candidates|ForEach-Object canonicalSystemTypeCandidate|Select-Object -Unique)
  $issues=@()
  if(!$types.Count){$status='unknown';$issues+='system_scope_unknown';if($s.rawText -match '系统'){$issues+='ontology_alias_unresolved'}}
  elseif($types.Count -gt 1){$status='ambiguous';$issues+=@('system_scope_ambiguous','multi_system_statement');if(@($ownTypes|Where-Object {$_ -notin $titleTypes}).Count -and $titleTypes.Count){$issues+='inherited_scope_conflict'}}
  else{$status=if(@($candidates|Where-Object {$_.sourceType -in @('explicit_section_title','inherited_section_context','statement_local_term')}).Count){'supported_candidate'}else{'partial'}}
  if($s.crossDrawingReferences.Count -gt 0 -and !$ownTypes.Count -and $types.Count){$status='ambiguous';$issues+='inherited_scope_conflict'}
  foreach($c in $candidates){$c.status=$status;$c.contradictingEvidence=@($issues);if($status -eq 'ambiguous'){$c.scopeInheritanceCandidate.status='stopped_for_review'}}
  $s|Add-Member systemScopeCandidates $candidates -Force;$s|Add-Member systemScopeStatus $status -Force
  $s|Add-Member systemScopeProvenance ([pscustomobject]@{projectId=$ProjectId;sourceSnapshot=$s.sourceSnapshot;sourceSheet=$s.sheetId;registrationBasis='caller supplied project registration; not filename inference';scopeMeaning='document-topic candidate, not installed-network membership'}) -Force
  foreach($issue in $issues|Select-Object -Unique){$reviews+=,[pscustomobject]@{modelType='ReviewItem';type=$issue;sourceStatementRef=$s.statementId;sourceRefs=@($candidates|ForEach-Object sourceRefs);status='unresolved';automaticResolution=$false}}
 }
 $r|Add-Member systemScopeReviews $reviews -Force
 return $r
}
Export-ModuleMember -Function Add-DesignSystemScopes,Find-SystemAlias
