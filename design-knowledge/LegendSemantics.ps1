# Candidate-only interpretation. Raw fragments remain authoritative.
function New-LegendValueCandidate {
 param([object[]]$Fragments=@(),$Value=$null,[string]$Status='unresolved')
 [pscustomobject]@{rawText=@($Fragments|ForEach-Object {$_.rawText});sourceFragments=@($Fragments);evidenceRefs=@($Fragments|ForEach-Object {$_.handle});valueCandidate=$Value;status=$Status;automaticApplication=$false}
}
function ConvertTo-LegendMountingCandidate {
 param([object[]]$Fragments=@(),[switch]$ReadingOrderSupported)
 $texts=@($Fragments|ForEach-Object {$_.rawText}|Select-Object -Unique)
 $text=if($texts.Count -eq 1){$texts[0]}elseif($ReadingOrderSupported){$texts -join ''}else{''}
 $datum='unresolved';$meaning='unspecified';$method='unresolved';$value=$null;$unit=$null;$normal=$null
 if($text -match '距地'){$datum='floor';$meaning='height_unspecified'}
 if($text -match '底边?距地'){$meaning='bottom_height'}
 if($text -match '中心距地'){$meaning='center_height'}
 if($text -match '顶板下'){$datum='slab_underside';$meaning='downward_offset'}
 if($text -match '梁下'){$datum='beam_underside';$meaning='downward_offset'}
 if($text -match '距顶'){$datum='ceiling';$meaning='downward_offset'}
 if($text -match '吸顶'){$datum='ceiling';$meaning='ceiling_mounted';$method='ceiling_mounted'}
 if($text -match '吊装'){$meaning='suspended';$method='suspended'}
 if($text -match '挂墙|壁装|挂装'){$method='wall_mounted'}
 if($text -match '落地'){$method='floor_mounted'}
 $numbers=[regex]::Matches($text,'(?<![\d.])(\d+(?:\.\d+)?)\s*(mm|m|米)?')
 if($numbers.Count -eq 1){$value=[double]::Parse($numbers[0].Groups[1].Value,[cultureinfo]::InvariantCulture);$unit=$numbers[0].Groups[2].Value
  if($datum -ne 'unresolved' -and $unit -in @('m','米','mm')){$normal=if($unit -eq 'mm'){$value/1000}else{$value}}
 }
 $status=if(!$text){'unresolved'}elseif($text -match '或' -or $datum -eq 'unresolved' -or ($null -ne $value -and !$unit)){'partial'}else{'candidate'}
 [pscustomobject]@{rawText=@($Fragments|ForEach-Object {$_.rawText});sourceFragments=@($Fragments);evidenceRef=@($Fragments|ForEach-Object {$_.handle});normalizedTextCandidate=$text;numericValueCandidate=$value;unitCandidate=$unit;referenceDatumCandidate=$datum;measurementMeaningCandidate=$meaning;normalizedValueCandidate=$normal;normalizedUnitCandidate=if($null -ne $normal){'m'}else{$null};mountingMethodCandidate=$method;status=$status;conditionsUnresolved=($text -match '或');automaticZAssignment=$false}
}
function ConvertTo-SemanticLegendEntry {
 param($Entry,[string]$SourceSheet,[object[]]$OrderedInstallationFragments=@(),[switch]$ReadingOrderSupported)
 $fields=[ordered]@{};foreach($p in $Entry.PSObject.Properties){$fields[$p.Name]=$p.Value}
 $mount=ConvertTo-LegendMountingCandidate $OrderedInstallationFragments -ReadingOrderSupported:$ReadingOrderSupported
 $fields.sourceDrawing=$Entry.sourceDocument;$fields.sourceSheet=$SourceSheet;$fields.sourceRegion=$Entry.regionId;$fields.rowRef=$Entry.entryId
 $fields.baseSymbolRef=@($Entry.symbolRepresentations|Where-Object entityType -eq 'INSERT'|ForEach-Object {$_.handle})
 $fields.qualifierRefs=@();$fields.representationPatternRef=$null;$fields.rawName=@($Entry.nameFragments.rawText)
 $fields.engineeringRoleCandidate=New-LegendValueCandidate $Entry.nameFragments $Entry.normalizedNameCandidate 'candidate'
 $fields.typeCandidate=New-LegendValueCandidate
 # A combined model/specification cell is not proof of how to split its contents.
 $fields.modelCandidate=New-LegendValueCandidate $Entry.modelFragments $null 'partial'
 $fields.specificationCandidate=New-LegendValueCandidate $Entry.modelFragments $null 'unresolved'
 $fields.modelSpecificationSeparationStatus='requires_review'
 $modelTexts=@($Entry.modelFragments|ForEach-Object {$_.rawText}|Select-Object -Unique)
 if($modelTexts.Count -eq 1 -and $modelTexts[0] -cmatch '^[A-Za-z][A-Za-z0-9./-]*\d[A-Za-z0-9./-]*$'){
  $fields.modelCandidate=New-LegendValueCandidate $Entry.modelFragments $modelTexts[0] 'candidate'
  $fields.modelSpecificationSeparationStatus='model_token_candidate_specification_unresolved'
 }
 $fields.mountingHeightCandidate=$mount;$fields.mountingMethodCandidate=New-LegendValueCandidate $OrderedInstallationFragments $mount.mountingMethodCandidate $mount.status
 $fields.elevationReferenceCandidate=$mount.referenceDatumCandidate;$fields.conditions=@();$fields.remarks=@()
 $fields.unitCandidate=New-LegendValueCandidate $Entry.noteFragments $null 'candidate'
 $fields.evidenceRefs=@($Entry.sourceHandles);$fields.applicabilityScope=$Entry.scope;$fields.conflictStatus='not_evaluated'
 $fields.presenceStatus='legend_definition_present'
 [pscustomobject]$fields
}
function New-RepresentationPattern {
 param([string]$Id,[string]$BaseSymbolDefinition,[string]$SourceScope,[object[]]$EvidenceRefs,[hashtable]$Results,[string[]]$QualifierTokens=@(),[string[]]$DefaultQualifierTokens=@(),[bool]$QualifierRequiredByLegend=$false,$RelativePositionPattern=$null)
 if(!$Id -or !$BaseSymbolDefinition -or !$SourceScope -or !$EvidenceRefs.Count){throw 'Pattern needs scoped source evidence'}
 [pscustomobject]@{modelType='RepresentationPattern';patternId=$Id;baseSymbolDefinition=$BaseSymbolDefinition;qualifierToken=@($QualifierTokens);qualifierEntityType='external_or_internal_evidence_required';relativePositionPattern=$RelativePositionPattern;associationRule='requires_independent_layout_or_structural_evidence';otherModifiers=@();resultingRole=$Results['role'];resultingType=$Results['type'];resultingModel=$Results['model'];resultingSpecification=$Results['specification'];resultingMountingHeight=$Results['mountingHeight'];resultingMountingMethod=$Results['mountingMethod'];sourceScope=$SourceScope;evidenceRefs=@($EvidenceRefs);status='candidate';defaultQualifierTokens=@($DefaultQualifierTokens);qualifierRequiredByLegend=$QualifierRequiredByLegend;presenceStatus='legend_definition_present'}
}
function Resolve-RepresentationPattern {
 param($Pattern,[string]$Drawing,[string]$BaseSymbolDefinition,[string[]]$ObservedTokens=@(),$Coverage=$null,[object[]]$AssociationEvidence=@(),[switch]$ConflictPresent)
 $reasons=@();$status='unresolved'
 if($ConflictPresent){$status='conflicting';$reasons+='conflicting_representation'}
 elseif($Drawing -cne $Pattern.sourceScope -or $BaseSymbolDefinition -cne $Pattern.baseSymbolDefinition){$reasons+='source_or_definition_scope_mismatch'}
 elseif($Pattern.qualifierToken.Count){
  if(@($Pattern.qualifierToken|Where-Object {$ObservedTokens -cnotcontains $_}).Count -eq 0 -and $AssociationEvidence.Count){$status='supported'}else{$reasons+='qualifier_association_unresolved'}
 }elseif($Pattern.defaultQualifierTokens.Count -and $Pattern.qualifierRequiredByLegend -and $Coverage -and $Coverage.drawing -ceq $Drawing -and $Coverage.fullDrawing -and $Coverage.includesBlocks -and $Coverage.includesAttributes -and $Coverage.includesHidden -and $Coverage.matches -eq 0 -and $Coverage.evidenceRefs.Count -and !$ObservedTokens.Count -and @($Pattern.defaultQualifierTokens|Where-Object {$Coverage.tokens -cnotcontains $_}).Count -eq 0){$status='supported'}
 else{$reasons+='negative_evidence_coverage_insufficient'}
 [pscustomobject]@{modelType='RepresentationRoleCandidate';patternRef=$Pattern.patternId;baseBlockRef=$BaseSymbolDefinition;qualifierEvidenceRef=@($AssociationEvidence);coverageEvidence=$Coverage;representationRoleCandidate=$Pattern.resultingRole;propertyCandidates=$Pattern;status=$status;blockingReasons=$reasons;confirmed=$false;automaticApplication=$false;presenceStatus='instance_presence_unresolved';qualifierPresenceCandidate=[pscustomobject]@{modelType='RepresentationQualifierPresenceCandidate';drawing=$Drawing;tokens=@($Pattern.qualifierToken)+@($Pattern.defaultQualifierTokens);status=if($status -eq 'supported' -and !$ObservedTokens.Count){'no_instance_evidence_found'}elseif($ObservedTokens.Count -and $AssociationEvidence.Count){'drawing_instance_present'}else{'instance_presence_unresolved'};evidence=$Coverage};invalidationDependencies=@($Pattern.evidenceRefs)+@($AssociationEvidence)}
}
