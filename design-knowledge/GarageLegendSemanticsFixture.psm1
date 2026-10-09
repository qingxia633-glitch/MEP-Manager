# Reviewed real-table adapter. Handles here are fixture provenance, never generic matching rules.
Import-Module "$PSScriptRoot/GarageLegendFixture.psm1"
Import-Module "$PSScriptRoot/ProjectDesignKnowledge.psm1"
function Read-GarageLegendSemanticsFixture {
 $k=Read-GarageLegendFixture
 $entries=@(foreach($e in $k.legendEntries){
  $ordered=@($e.installationRequirementFragments|Sort-Object { $v=[regex]::Matches($_.coordinateRaw,'-?\d+(?:\.\d+)?'); -[double]$v[1].Value },{ $v=[regex]::Matches($_.coordinateRaw,'-?\d+(?:\.\d+)?'); [double]$v[0].Value })
  ConvertTo-SemanticLegendEntry $e 'EW-0007' $ordered -ReadingOrderSupported
 })
 $ordinary=$entries|Where-Object rowId -eq '14';$gas=$entries|Where-Object rowId -eq '48'
 if(!($gas.rawRepresentations|Where-Object {$_.handle -eq '23F42' -and $_.rawText -eq 'QM'})){throw 'Reviewed qualifier evidence missing'}
 $gas.qualifierRefs=@('23F42');$gas.representationPatternRef='garage-gas-sound-light';$ordinary.representationPatternRef='garage-ordinary-sound-light'
 $patterns=@(foreach($e in @($ordinary,$gas)){
  $args=@{Id=$e.representationPatternRef;BaseSymbolDefinition='$equip$00002679';SourceScope=$e.sourceDocument;EvidenceRefs=@($e.sourceHandles);Results=@{role=$e.engineeringRoleCandidate;model=$e.modelCandidate;specification=$e.specificationCandidate;mountingHeight=$e.mountingHeightCandidate;mountingMethod=$e.mountingMethodCandidate}}
  if($e.rowId -eq '48'){$args.QualifierTokens=@('QM');$args.RelativePositionPattern=@{directionCandidate='below';evidenceRefs=@('23AC5','23F42');basis='reviewed_same_row_symbol_cell';scope='this_legend_row'}}else{$args.DefaultQualifierTokens=@('QM');$args.QualifierRequiredByLegend=$true}
  $pattern=New-RepresentationPattern @args
  $pattern.qualifierEntityType='TEXT_external_to_block'
  $pattern
 })
 $k.legendEntries=$entries
 $k.representationPatterns=$patterns
 # Inventory the real header band using the reviewed table geometry, not expected header words.
 $f=Get-Content "$PSScriptRoot/tests/garage-legend.json" -Raw|ConvertFrom-Json
 $headers=@(foreach($record in [regex]::Split([IO.File]::ReadAllText($k.sources[0].rawSource),'(?m)^EntityHandle=')){
  $point=[regex]::Match($record,'(?m)^Insertion_WCS=\(([^)]+)\)')
  $text=[regex]::Match($record,'(?m)^Text_RAW="([^"]*)"')
  if(!$point.Success -or !$text.Success){continue}
  $xy=[double[]]($point.Groups[1].Value -split '\s+')
  if($xy[1] -lt $f.region.bodyTop -or $xy[1] -ge $f.region.top){continue}
  for($c=0;$c -lt $f.region.xColumns.Count-1;$c++){
   if($xy[0] -ge $f.region.xColumns[$c] -and $xy[0] -lt $f.region.xColumns[$c+1]){
    [pscustomobject]@{handle=($record -split '\r?\n')[0].Trim('"');rawText=$text.Groups[1].Value;column=$c;x=$xy[0];y=$xy[1]}
   }
  }
 })
 $inventory=@(foreach($group in $headers|Group-Object column){
  $ordered=@($group.Group|Sort-Object x)
  [pscustomobject]@{column=$group.Name;rawFragments=$ordered;headerCandidate=(@($ordered|Group-Object x|ForEach-Object {$_.Group[0].rawText}) -join '');status='reviewed_grid_reading_order_candidate'}
 })
 $k|Add-Member legendFieldInventory $inventory
 $k|Add-Member legendFieldCoverage ([pscustomobject]@{rows=$entries.Count;rowsWithName=@($entries|Where-Object {$_.nameFragments.Count}).Count;rowsWithModelSpecification=@($entries|Where-Object {$_.modelFragments.Count}).Count;rowsWithInstallation=@($entries|Where-Object {$_.installationRequirementFragments.Count}).Count;rowsWithNumericHeight=@($entries|Where-Object {$null -ne $_.mountingHeightCandidate.numericValueCandidate}).Count;rowsWithNormalizedHeight=@($entries|Where-Object {$null -ne $_.mountingHeightCandidate.normalizedValueCandidate}).Count})
 $k|Add-Member semanticLimitations @('combined_model_specification_cell','duplicate_text_retained','alternative_mounting_conditions_unresolved','no_automatic_instance_presence','cross_document_application_requires_scope_evidence')
 $k
}
Export-ModuleMember -Function Read-GarageLegendSemanticsFixture
