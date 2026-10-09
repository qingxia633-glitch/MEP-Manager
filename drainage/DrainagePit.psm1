Set-StrictMode -Version 2
function Field-Pit($text,$key){
 $m=[regex]::Match($text,'(?m)^'+[regex]::Escape($key)+'=(.*?)\r?$')
 if(!$m.Success){return $null};$m.Groups[1].Value.Trim('"')
}
function Points-Pit($text,$pattern){
 @(foreach($m in [regex]::Matches($text,$pattern)){,@($m.Groups[1].Value -split '\s+'|Where-Object {$_}|ForEach-Object {[double]::Parse($_,[cultureinfo]::InvariantCulture)})})
}
function Select-PitRecord($text,$start,$end,$key,$handle){
 $records=@([regex]::Matches($text,'(?ms)^'+$start+'.*?^'+$end+'\r?$')|Where-Object {(Field-Pit $_.Value $key) -ceq $handle})
 if($records.Count -ne 1){throw "Expected unique record $key=$handle"};$records[0].Value
}
function Test-PitCrossDocumentEligibility($Candidate){
 # This stage never authorizes cross-document position matching.
 return $false
}
function Read-PitCandidate {
 param($Spec,[string]$Root=(Join-Path $PSScriptRoot '..'))
 $texts=@{};$sources=@{}
 foreach($p in $Spec.sources.psobject.Properties){
  $path=Join-Path $Root $p.Value.path;$hash=(Get-FileHash -LiteralPath $path).Hash
  if($hash -cne $p.Value.sha256){throw 'Pinned snapshot changed'}
  $t=[IO.File]::ReadAllText($path)
  if($t -notmatch '(?m)^END_OF_REPORT' -or ($t -match '(?m)^INCOMPLETE_REPORT')){throw 'Incomplete source'}
  $dwg=Field-Pit $t 'DWG';if(($dwg -split '[\\/]')[-1] -cne $Spec.dwgName){throw 'Wrong DWG'}
  $texts[$p.Name]=$t;$sources[$p.Name]=@{path=$p.Value.path;sha256=$hash;dwg=$dwg}
 }
 if((Field-Pit $texts.probe 'ReadErrorCount') -ne '0' -or (Field-Pit $texts.probe 'DefinitionPathStatus') -ne 'resolved'){throw 'Probe/path not accepted'}
 $path=@($Spec.parentDefinition,$Spec.carrierHandle,$Spec.definition)
 $actualPath=@([regex]::Matches((Field-Pit $texts.probe 'SourceDefinitionPath'),'"([^"]+)"')|ForEach-Object {$_.Groups[1].Value})
 if(($actualPath -join '|') -cne ($path -join '|')){throw 'Definition path mismatch'}
 function Geometry($h){
  $r=Select-PitRecord $texts.probe 'SourceDefinitionPath=' 'Entity_END' 'SourceInternalHandle' $h
  [pscustomobject]@{handle=$h;entityType=(Field-Pit $r 'DXF_Type');layer=(Field-Pit $r 'Layer');coordinateFrame='DefinitionLocal';sourceDefinition=$Spec.definition;sourceInstancePath=$path;sourceSnapshot=$sources.probe;rawRecord=$r;geometryPoints=@(Points-Pit $r '(?m)^DXF:1[0-3]=\(([^)]+)\)');closedRaw=(Field-Pit $r 'Closed_RAW');visibilityDXF60=(Field-Pit $r 'DXF60');referencedBlock=(Field-Pit $r 'ReferencedBlockName');semanticStatus='candidate'}
 }
 function IndexStatement($h){
  $r=Select-PitRecord $texts.index 'Text_BEGIN' 'Text_END' 'InternalHandle' $h
  if((Field-Pit $r 'SourceBlock') -cne $Spec.parentDefinition){throw 'Statement definition mismatch'}
  [pscustomobject]@{handle=$h;rawText=(Field-Pit $r 'Text_RAW');layer=(Field-Pit $r 'Layer');sourceDefinition=(Field-Pit $r 'SourceBlock');coordinateFrame='DefinitionLocal';coordinates=@(Points-Pit $r '(?m)^LocalPoint_DXF10=\(([^)]+)\)');sourceSnapshot=$sources.index;rawRecord=$r;evidenceType='DrawingFact'}
 }
 $identifier=IndexStatement $Spec.identifierHandle
 if($identifier.rawText -cne $Spec.identifier){throw 'Identifier changed'}
 $carrier=Select-PitRecord $texts.local 'LocalEntity_BEGIN' 'LocalEntity_END' 'SourceHandle' $Spec.carrierHandle
 if((Field-Pit $carrier 'ReferencedBlockName') -cne $Spec.definition){throw 'Carrier changed'}
 $pumps=@();$seen=@{};$i=0
 foreach($group in $Spec.pumps){
  $members=@(foreach($h in $group){if($seen.ContainsKey($h)){throw 'Repeated member across symbol groups'};$seen[$h]=$true;Geometry $h})
  $i++;$pumps+=,[pscustomobject]@{modelType='PumpSymbolCandidate';id="symbol-$i";members=$members;status='candidate';engineeringType='unresolved';operatingMode='unresolved';power='unresolved';model='unresolved'}
 }
 $categories=@(for($i=0;$i -lt $Spec.categoryHandles.Count;$i++){
  $s=IndexStatement $Spec.categoryHandles[$i];if($s.rawText -cne $Spec.categoryTexts[$i]){throw 'Category declaration changed'}
  [pscustomobject]@{scope='category_only';status='candidate';statement=$s;instanceInheritance='not_applied'}
 })
 $placements=@(foreach($p in $Spec.placements){
  $r=[regex]::Match($texts.plan,'(?ms)^EntityHandle="'+[regex]::Escape($p.top)+'"\r?\n.*?(?=^EntityHandle=|^LayerEntityCount=|\z)').Value
  if(!$r -or (Field-Pit $r 'DXF_Type') -ne 'INSERT'){throw 'Placement INSERT missing'}
  $topRef=Select-PitRecord $texts.index 'Reference_BEGIN' 'Reference_END' 'InternalHandle' $p.top
  $links=@();$parent=Field-Pit $r 'BlockName'
  foreach($h in $p.nested){$rr=Select-PitRecord $texts.index 'Reference_BEGIN' 'Reference_END' 'InternalHandle' $h
   if((Field-Pit $rr 'ParentBlock') -cne $parent){throw 'Nested parent mismatch'}
   $links+=,@{handle=$h;sourceSnapshot=$sources.index;rawRecord=$rr;transformStatus='incomplete_rotation_scale_normal_not_exported'}
   $parent=Field-Pit $rr 'ReferencedBlockName'
  }
  if($parent -cne $Spec.parentDefinition){throw 'Placement target mismatch'}
  [pscustomobject]@{path=@('ModelSpace',$p.top)+@($p.nested)+$path;status='candidate';selectionStatus='unresolved';InstanceWCS='not_computed';topInsert=@{handle=$p.top;layer=(Field-Pit $r 'Layer');sourceSnapshot=$sources.plan;rawRecord=$r;insertionWCS=@(Points-Pit $r '(?m)^Insertion_WCS=\(([^)]+)\)');visibilityStatus='evaluated_visibility_unknown';indexVisibilityEvidence=@{DXF60_RAW=(Field-Pit $topRef 'DXF60_RAW');rawRecord=$topRef;sourceSnapshot=$sources.index}};nestedReferences=$links;transformEvidenceStatus=if($links.Count){'incomplete'}else{'top_transform_observed_snapshot_correspondence_unverified'};scopeStatus='unresolved'}
 })
 [pscustomobject]@{schemaVersion='1.0';modelType='DrainagePitInstanceCandidate';analysisRunId=[guid]::NewGuid().ToString();pitIdentifier=$identifier.rawText;identifierEvidence=$identifier;sourceDefinition=$Spec.definition;sourceInstancePath=$path;sourceSnapshots=$sources;pitOutlineCandidate=@{status='candidate';members=@($Spec.outer|ForEach-Object {Geometry $_});dimensionStatus='drawing_units_only_not_engineering_dimensions'};innerOutlineCandidate=@{status='candidate';members=@($Spec.inner|ForEach-Object {Geometry $_})};auxiliaryGeometry=@($Spec.auxiliary|ForEach-Object {Geometry $_});pumpSymbolCandidates=$pumps;categoryRelationCandidate=@{status='partially_compatible';basis='reviewed_identifier_category_and_paired_layout_not_automatic_rule'};categoryAttributeCandidates=$categories;placementStatus='unresolved';InstanceWCS='not_computed';crossDocumentCoordinateMatchingAllowed=$false;placementHypotheses=$placements;missingInformation=@('selected_top_level_instance','snapshot_correspondence_not_verified','evaluated_visibility_and_view_scope','nested_reference_full_transform','engineering_units_and_dimensions','pump_identity_and_control_semantics');evidence=@(@{type='DerivedInference';status='candidate';claim='identifier_to_carrier_local_layout';identifier=$identifier.handle;carrier=$Spec.carrierHandle;sourceSnapshot=$sources.local;rawRecord=$carrier},@{type='DerivedInference';status='candidate';claim='paired_pump_like_layout';basis='explicit_reviewed_fixture_members_not_automatic_recognition';memberGroups=@($Spec.pumps)});conflicts=@();exceptions=@{sourceSnapshot=$sources.local;unknownWindowRecords=@([regex]::Matches($texts.local,'(?ms)^LocalEntity_BEGIN.*?^LocalEntity_END')|Where-Object {$_.Value -match 'WindowMembership="unknown"'}|ForEach-Object {@{handle=(Field-Pit $_.Value 'SourceHandle');rawRecord=$_.Value;status='unknown'}})};limitations=@('candidate at definition path, not confirmed installed device','no electrical or terminal binding','no quantity calculation','raw source records retained without snapshot confirmation migration')}
}
Export-ModuleMember -Function Read-PitCandidate,Test-PitCrossDocumentEligibility
