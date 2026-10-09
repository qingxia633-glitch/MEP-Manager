Set-StrictMode -Version 2
Import-Module (Join-Path $PSScriptRoot 'ModelCore.psm1')
function Read-GoldenModel {
 param([string]$Root=(Join-Path $PSScriptRoot '..'))
 $spec=Get-Content (Join-Path $PSScriptRoot 'tests/golden-sample.json') -Raw -Encoding UTF8|ConvertFrom-Json
 $manifest=Get-Content (Join-Path $PSScriptRoot 'tests/source-manifest.json') -Raw -Encoding UTF8|ConvertFrom-Json
 $raw=@{};$sourceRefs=@{}
 foreach($s in $manifest){
  $p=Join-Path $Root $s.path
  if((Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash -cne $s.sha256){throw "Golden source changed: $($s.path)"}
  $raw[$s.key]=[IO.File]::ReadAllText($p);$sourceRefs[$s.key]=$s
 }
 $pit=$raw.pit|ConvertFrom-Json;$config=$raw.configuration|ConvertFrom-Json;$rows=$raw.rows|ConvertFrom-Json
 $record=[regex]::Match($raw.power,'(?ms)^EntityHandle="'+[regex]::Escape($spec.panelHandle)+'"\r?\n.*?(?=^EntityHandle=|^LayerEntityCount=|\z)').Value
 if(!$record -or !$record.Contains($spec.identifierHandle) -or !$record.Contains($spec.panelIdentifier)){throw 'Panel fixture source missing'}
 $panelId=$spec.projectId+':instance:'+$sourceRefs.power.sha256+':'+$spec.panelHandle
 $pitId=$spec.projectId+':pit:'+ $sourceRefs.pit.sha256+':'+$spec.pitIdentifier
 $configId=$rows.panelConfigurationId
 $groupId=$pitId+':pump-symbol-group'
 $representationId=$pitId+':representation-paths'
 $scope=@{projectId=$spec.projectId;snapshotIds=@($manifest|ForEach-Object {$_.sha256});subjectIds=@($panelId,$pitId,$configId,$groupId,$representationId);spatialScope='reviewed local basement area only';scopePropagation='forbidden'}
 function E($id,$kind,$fact,$claim,$deps=@()){
  @{evidenceId=$id;kind=$kind;fact=$fact;claim=$claim;status='supported';scope=$scope;dependencies=@($deps);provenance=@{source=if($kind -eq 'HumanConfirmation'){$spec.humanEvidenceSource}else{'golden fixture adaptation; source models preserved'};sourceRefs=@($manifest)}}
 }
 $hcLocation=E 'human-location' HumanConfirmation 'drainage_pump_group_location' $spec.humanClaims.location
 $hcSymbols=E 'human-symbols' HumanConfirmation 'visible_paired_symbols' $spec.humanClaims.symbols
 $hcRule=E 'human-project-rule' HumanConfirmation 'same_identifier_configuration_rule' $spec.humanClaims.configurationRule
 $hcConfig=E 'human-configuration' HumanConfirmation 'panel_configuration' $spec.humanClaims.configuration
 $panelEvidence=E 'panel-source' DrawingFact 'panel_installation_instance' 'Independent plan INSERT and identifier; source record below'
 $prov=@{source='reviewed golden sample adapter';sampleId=$spec.sampleId;sourceRefs=@($manifest)}
 $uses=New-AssociationCandidate $panelId usesConfiguration @($configId) $scope @($panelEvidence,$hcRule,$hcConfig) -Status supported -Provenance $prov
 $location=New-AssociationCandidate $pitId sameBuildingLocation @($panelId) $scope @($hcLocation) -Status supported -Provenance $prov
 $represents=New-AssociationCandidate $representationId represents @($pitId) $scope @($hcSymbols) -MissingEvidence @('final equipment identities') -Status supported -Provenance $prov
 $groupEvidence=E 'group-inference' DerivedInference 'group_level_association' 'Supported group-level candidate only; no individual terminal or physical connection' @($hcLocation.evidenceId,$hcSymbols.evidenceId,$hcRule.evidenceId,$hcConfig.evidenceId,$panelEvidence.evidenceId)
 $group=New-AssociationCandidate $panelId suppliesCandidate @($groupId) $scope @($groupEvidence) -MissingEvidence @('individual_pump_mapping','water_level_device_binding','physical_routing','procurement_boundary') -Status supported -Provenance $prov
 $evidence=@($hcLocation,$hcSymbols,$hcRule,$hcConfig,$panelEvidence,$groupEvidence)
 $task='resolve electrical supply from panel configuration to installed pump group'
 $requirements=@(foreach($r in $spec.requirements){Resolve-InformationRequirement -RequirementId ($spec.sampleId+':'+$r.fact) -TaskType $task -RequiredFact $r.fact -Scope $scope -Evidence $evidence -SearchScopeCandidates $r.search})
 $objects=@(@{handle=$spec.panelHandle;attributeHandle=$spec.identifierHandle;coordinates=$spec.panelCoordinates;coordinateFrame='ModelSpaceWCS';sourceSnapshot=$sourceRefs.power},$pit.identifierEvidence)
 $reviews=@(Get-ModelReviewItems -Requirements $requirements -Associations @($uses,$location,$represents,$group) -SourceDocuments $manifest -SourceObjects $objects -Dependencies (@($manifest.sha256)+@($evidence.evidenceId)))
 $catalog=Get-Content (Join-Path $PSScriptRoot 'capabilities.json') -Raw -Encoding UTF8|ConvertFrom-Json
 $coverage=@(foreach($c in $catalog){New-CapabilityCoverage -CapabilityId $c.id -Domain $c.domain -ObjectType $c.objectType -CapabilityType $c.type -Status $c.status -ValidatedSamples $c.samples -ApplicableScope $c.scope -KnownLimitations $c.limitations -UnresolvedCases $c.unresolved -EvidenceRefs $c.evidence})
 [pscustomobject][ordered]@{modelType='GoldenSampleModel';version='1.0';sampleId=$spec.sampleId;scope=$scope;sourceManifest=$manifest;representationBundle=@{id=$representationId;memberPaths=@($spec.representationPaths);selectionStatus='unresolved'};pumpGroup=@{id=$groupId;pitRef=$pitId;members=@($pit.pumpSymbolCandidates);status='candidate'};originalModels=@{pit=$pit;configuration=$config;outgoingRows=$rows};panelRepresentation=@{id=$panelId;handle=$spec.panelHandle;attributeHandle=$spec.identifierHandle;sourceSnapshot=$sourceRefs.power;rawRecord=$record};placementOverlay=@{placementStatus='canonical_placement_candidate';selectedRawRepresentation='unresolved';representationPaths=@($spec.representationPaths);evidenceRefs=@($hcLocation.evidenceId,$hcSymbols.evidenceId);InstanceWCS='not_recomputed';rawModelNotModified=$true};associations=@($uses,$location,$represents,$group);domainViews=@(@{modelType='PumpGroupElectricalAssociationCandidate';associationRef=$group.associationId;configurationRef=$configId;outgoingRows=@($rows.outgoingRows.rowId);interpretation='supported_group_candidate_only';individualMapping=@();sensorBinding='unresolved'});evidence=$evidence;requirements=$requirements;taskStatus='blocked_for_confirmed_supply';networks=@(New-NetworkSkeleton);reviewItems=$reviews;coverage=$coverage;ruleSource=(Get-Content (Join-Path $PSScriptRoot 'rule-source.json') -Raw -Encoding UTF8|ConvertFrom-Json);ruleReferences=@();prohibitedInferences=@('individual mapping','sensor binding','operating logic inheritance','confirmed instance power/duty','Circuit','quantity')}
}
Export-ModuleMember -Function Read-GoldenModel
