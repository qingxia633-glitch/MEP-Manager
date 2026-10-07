Set-StrictMode -Version 2
Import-Module (Join-Path $PSScriptRoot 'ProjectDesignKnowledge.psm1')
Import-Module (Join-Path $PSScriptRoot '../model-core/ModelCore.psm1')

# Reviewed sample adapter. No production rule contains these Handles or text interpretations.
function Read-DesignStatementFixture {
 param([string]$Root=(Join-Path $PSScriptRoot '..'))
 $f=Get-Content (Join-Path $PSScriptRoot 'tests/design-statement.json') -Raw -Encoding UTF8|ConvertFrom-Json
 $path=Join-Path $Root $f.source.path
 if((Get-FileHash -LiteralPath $path).Hash -cne $f.source.sha256){throw 'Statement source snapshot changed'}
 $text=[IO.File]::ReadAllText($path)
 function Field($r,$key){[regex]::Match($r,'(?m)^'+[regex]::Escape($key)+'=(.*?)\r?$').Groups[1].Value.Trim('"')}
 if(!(Field $text DWG).EndsWith($f.source.document) -or $text -notmatch '(?m)^END_OF_REPORT' -or (Field $text ReadErrorCount) -ne '0'){throw 'Statement snapshot not accepted'}
 function Record($h){
  $m=[regex]::Match($text,'(?ms)^EntityHandle="'+[regex]::Escape($h)+'".*?(?=^EntityHandle=|^LayerEntityCount=|^LAYER_END|\z)')
  if(!$m.Success){throw "Missing fixture record: $h"}
  $r=$m.Value
  [pscustomobject]@{handle=$h;entityType=(Field $r DXF_Type);layer=(Field $r Layer);rawText=(Field $r Text_RAW);coordinateRaw=(Field $r Insertion_WCS);rawRecord=$r;sourceDocument=$f.source.document;sourceSnapshot=$f.source.sha256}
 }
 $parent=Record $f.titleParent
 $attrs=@(foreach($h in @($f.titleAttribute,$f.drawingNumberAttribute)){
  $a=@([regex]::Matches($parent.rawRecord,'(?m)^Attribute_DXF=(.*)')|Where-Object {$_.Groups[1].Value.Contains('(5 . "'+$h+'")')})
  if($a.Count -ne 1){throw 'Title attribute provenance missing'}
  $raw=$a[0].Groups[1].Value
  [pscustomobject]@{handle=$h;parentHandle=$parent.handle;entityType='ATTRIB';rawText=[regex]::Match($raw,'\(1 \. "([^"]*)"\)').Groups[1].Value;coordinateRaw=[regex]::Match($raw,'\(10 ([^)]+)\)').Groups[1].Value;tag=[regex]::Match($raw,'\(2 \. "([^"]*)"\)').Groups[1].Value;rawDXF=$raw;sourceSnapshot=$f.source.sha256}
 })
 $source=New-DesignKnowledgeSource $f.fixtureId (New-DesignScope $f.projectId $f.source.document $f.source.sha256 unresolved unresolved) $f.source.path DrawingFact $f.source.sha256
 $context=@($f.contextHandles|ForEach-Object {Record $_})
 $region=New-StatementSourceRegion ($f.fixtureId+':region') $source (@($parent)+$attrs+$context) @{basis='numbered paragraph, preceding context, following numbered item; sheet association candidate';titleAttributeRef=$f.titleAttribute;drawingNumberAttributeRef=$f.drawingNumberAttribute;physicalFrame='not_expanded';paragraphStart=$f.fragments[0].handle;nextParagraph=$f.contextHandles[-1]}
 $fragments=@(foreach($v in $f.fragments){
  $r=Record $v.handle
  if($r.entityType -ne 'TEXT' -or $r.rawText -cne $v.rawText){throw 'Raw statement fixture changed'}
  New-TextFragmentCandidate $source $r
 })
 $coordinates=@($fragments|ForEach-Object {,@([regex]::Matches($_.coordinateRaw,'-?\d+(?:\.\d+)?')|ForEach-Object {[double]::Parse($_.Value,[cultureinfo]::InvariantCulture)})})
 $layout=@{basis=$f.readingEvidence;insertionPoints=@($coordinates);coordinateFrame='snapshot_WCS_drawing_units';lineGaps=@(($coordinates[0][1]-$coordinates[1][1]),($coordinates[1][1]-$coordinates[2][1]));continuationDeltaX=$coordinates[1][0]-$coordinates[2][0];firstLineIndent=$coordinates[0][0]-$coordinates[1][0];direction='top_to_bottom';semanticJoinEvidence=@('split words','punctuation','next numbered item')}
 if($layout.lineGaps[0] -le 0 -or $layout.lineGaps[1] -le 0 -or [math]::Abs($layout.continuationDeltaX) -gt 0.00001){throw 'Reviewed paragraph layout changed'}
 $order=New-ReadingOrderCandidate $fragments $layout ($fragments.rawText -join '')
 $group=New-DesignStatementGroup $f.fixtureId $region $fragments $order $f.paragraphNumber
 function Spans($s,[string]$within=''){@(Get-StatementTextSpans $group $s $within)}
 $subject=New-ApplicabilityCondition 'non-fire-load' @(Spans $f.subject) subject_scope
 $short=New-ApplicabilityCondition 'short-line' @(Spans $f.shortCondition) qualitative_length
 $long=New-ApplicabilityCondition 'long-line' @(Spans $f.longCondition) qualitative_length
 $options=@(foreach($o in @('短路瞬时','短路短延时')){[pscustomobject]@{rawText=$o;sourceSpans=@(Spans $o $f.alternative);status='candidate'}})
 $alternative=New-AlternativeClause @(Spans $f.alternative) $options
 $purpose=New-PurposeClause @(Spans $f.purposeSubject) @(Spans $f.purposeText) @(Spans $f.purposeConnector)
 $setting=@{rawText=$f.settingRequirement;sourceSpans=@(Spans $f.settingRequirement);status='candidate';actualSettings='unresolved'}
 $system=New-SystemScope $f.projectId (New-SystemIdentity power)
 $common=@{Group=$group;Discipline='electrical';SubjectScope='non_fire_load';SystemScope=$system}
 $a=New-DesignStatementCandidate -Id ($group.groupId+':A') @common -StatementType requirement -Spans @(Spans $f.requirementA) -Conditions @($subject,$short)
 $b=New-DesignStatementCandidate -Id ($group.groupId+':B') @common -StatementType requirement -Spans @(Spans ($f.requirementB+'，'+$f.settingRequirement)) -Conditions @($subject,$long) -Alternatives @($alternative) -AdditionalRequirements @($setting)
 $c=New-DesignStatementCandidate -Id ($group.groupId+':C') @common -StatementType purpose_statement -Spans @(Spans ($f.purposeSubject+$f.purposeConnector+$f.purposeText)) -Conditions @($subject) -Purpose $purpose
 $statements=@($a,$b,$c)
 $anomaly=New-SectionNumberAnomaly ($context|Where-Object handle -CEQ $f.sectionTitle) $f.parentNumber $group
 $reviews=@()
 if($anomaly){
  $requirement=[pscustomobject]@{requirementId=($group.groupId+':numbering');status='partial';taskType='resolve statement hierarchy';requiredFact='parent section identity';missingReason='Printed parent 4.11 and paragraph 4.12.1 differ; no automatic correction'}
  $reviews+=,(New-ReviewItem $requirement @($source) $context @('numbering typo','different parent section') @($group.groupId,$f.sectionTitle))
 }
 $evidence=@($statements|ForEach-Object {ConvertTo-DesignEvidence $_ ('design_statement:'+$_.statementId) $system})
 $ids=@('design_statement_extraction','text_reading_order','conditional_statement_model','alternative_clause_model','design_statement_scope')
 $coverage=@((Get-Content (Join-Path $Root 'model-core/capabilities.json') -Raw -Encoding UTF8|ConvertFrom-Json)|Where-Object {$ids -contains $_.id}|ForEach-Object {New-CapabilityCoverage $_.id $_.domain $_.objectType $_.type $_.status $_.samples $_.scope $_.limitations $_.unresolved $_.evidence})
 New-ProjectDesignKnowledge -ProjectId $f.projectId -Sources @($source) -Regions @($region) -Entries @() -Symbols @() -Comparisons @() -Conflicts @() -Evidence $evidence -Reviews $reviews -Coverage $coverage -StatementGroups @($group) -Statements $statements -StructuralAnomalies @($anomaly)
}
Export-ModuleMember -Function Read-DesignStatementFixture
