Set-StrictMode -Version 2
Import-Module (Join-Path $PSScriptRoot 'SystemDiagram.psm1') -DisableNameChecking
function Copy-Outgoing($v){ConvertFrom-Json (ConvertTo-Json -InputObject $v -Depth 90)}
function One-Outgoing($items,$h){$a=@($items|Where-Object handle -ceq $h);if($a.Count -ne 1){throw "Expected one selected record: $h"};$a[0]}
function Read-OutgoingInputs {
 param($Spec,[string]$Root=(Join-Path $PSScriptRoot '..'))
 $mp=Join-Path $Root $Spec.configurationModel.path;$sp=Join-Path $Root $Spec.source.path
 if((Get-FileHash -LiteralPath $mp).Hash -cne $Spec.configurationModel.sha256 -or (Get-FileHash -LiteralPath $sp).Hash -cne $Spec.source.sha256){throw 'Pinned source changed; review required'}
 $model=Get-Content -LiteralPath $mp -Raw -Encoding UTF8|ConvertFrom-Json
 $snapshot=Read-DiagramSnapshot $sp
 $handles=@($Spec.sharedStatements|ForEach-Object {$_.handle})+@($Spec.rows|ForEach-Object {$_.identifierHandle;$_.targetHandle;$_.cableHandle;if($_.powerHandle){$_.powerHandle}})
 $statements=@(foreach($h in ($handles|Select-Object -Unique)){One-Outgoing $snapshot.statements $h})
 $configuration=@($model.panelConfigurations|Where-Object id -ceq $Spec.panelConfigurationId)
 if($configuration.Count -ne 1){throw 'Expected one panel configuration'}
 $gh=@($configuration[0].definitionRegion.internalDeviceFrame.handle)+@($Spec.rows|ForEach-Object {$_.geometryHandle;if($_.tailGeometryHandle){$_.tailGeometryHandle}})
 $text=[IO.File]::ReadAllText($sp)
 $geometry=@(foreach($h in ($gh|Select-Object -Unique)){
  $records=[regex]::Matches($text,'(?ms)^EntityHandle="'+[regex]::Escape($h)+'"\r?\n.*?(?=^EntityHandle=|^LayerEntityCount=|\z)')
  if($records.Count -ne 1){throw 'Missing/duplicate selected geometry'};$b=$records[0].Value
  $type=[regex]::Match($b,'(?m)^DXF_Type="([^"]+)"').Groups[1].Value
  if($type -notin @('LINE','LWPOLYLINE')){throw 'Only direct straight geometry supported'}
  if(@([regex]::Matches($b,'\(42 \. ([^)]+)\)')|Where-Object {[double]::Parse($_.Groups[1].Value,[cultureinfo]::InvariantCulture) -ne 0}).Count){throw 'Curved geometry unsupported'}
  $points=@(foreach($p in [regex]::Matches($b,'(?m)^(?:Vertex_WCS|Start_WCS|End_WCS)=\(([^)]+)\)')){,@($p.Groups[1].Value -split ' '|ForEach-Object {[double]::Parse($_,[cultureinfo]::InvariantCulture)})})
  [pscustomobject]@{handle=$h;type=$type;layer=[regex]::Match($b,'(?m)^Layer="([^"]+)"').Groups[1].Value;vertices=$points;closed=($b -match '(?m)^Closed=T\r?$');rawText=$null;rawRecord=$b;sourceSnapshot=$snapshot.sourceSnapshot}
 })
 [pscustomobject]@{configurationModel=$model;sourceSnapshot=$snapshot.sourceSnapshot;statements=$statements;geometry=$geometry}
}
function Distance-Outgoing($a,$b){$d=0.0;for($i=0;$i -lt 3;$i++){$d+=[math]::Pow(($a[$i]-$b[$i]),2)};[math]::Sqrt($d)}
function Contact-Outgoing($line,$frame,$tol){
 $hits=@();$min=[double]::PositiveInfinity
 for($k=0;$k -lt 2;$k++){$p=$line.vertices[$k]
  for($j=0;$j -lt $frame.vertices.Count;$j++){
   $a=$frame.vertices[$j];$b=$frame.vertices[($j+1)%$frame.vertices.Count];$len2=0.0;$dot=0.0
   for($c=0;$c -lt 3;$c++){$len2+=[math]::Pow(($b[$c]-$a[$c]),2);$dot+=($p[$c]-$a[$c])*($b[$c]-$a[$c])}
   if($len2 -eq 0){throw 'Degenerate frame segment'};$t=[math]::Max(0.0,[math]::Min(1.0,$dot/$len2))
   $q=@(for($c=0;$c -lt 3;$c++){$a[$c]+$t*($b[$c]-$a[$c])});$d=Distance-Outgoing $p $q;$min=[math]::Min($min,$d)
   if($d -le $tol){$hits+=,[pscustomobject]@{endpointIndex=$k;frameSegmentIndex=$j;point=$p;residual=$d}}
  }
 }
 [pscustomobject]@{evidenceType='PanelBoundaryContactEvidence';status=if(!$hits.Count){'not_observed'}elseif(@($hits.endpointIndex|Select-Object -Unique).Count -gt 1){'ambiguous'}else{'observed'};contacts=$hits;minimumResidual=$min;tolerance=$tol;meaning='geometric_contact_only_not_electrical_port'}
}
function New-OutgoingRowModel {
 param($Inputs,$Spec)
 $d=Copy-Outgoing $Inputs;$f=Copy-Outgoing $Spec
 if($d.sourceSnapshot.sha256 -cne $f.source.sha256 -or ($d.sourceSnapshot.dwg -split '[\\/]')[-1] -cne $f.source.dwgName){throw 'Snapshot/document mismatch'}
 $configs=@($d.configurationModel.panelConfigurations|Where-Object id -ceq $f.panelConfigurationId)
 if($configs.Count -ne 1){throw 'Panel configuration mismatch'};$config=$configs[0]
 if($d.configurationModel.projectId -cne $f.projectId -or $config.projectId -cne $f.projectId -or $config.definitionRegion.sourceSnapshot.sha256 -cne $d.sourceSnapshot.sha256 -or $config.definitionRegion.regionId -cne $f.regionId -or $config.definitionRegion.localViewId -cne $f.localViewId){throw 'Project/configuration region scope mismatch'}
 $tol=[double]$f.tolerance
 if($tol -le 0 -or [double]::IsNaN($tol) -or [double]::IsInfinity($tol)){throw 'Positive finite tolerance required'}
 foreach($r in @($d.statements)+@($d.geometry)){
  if($r.sourceSnapshot.sha256 -cne $d.sourceSnapshot.sha256 -or $r.sourceSnapshot.dwg -cne $d.sourceSnapshot.dwg){throw 'Mixed snapshot record'}
 }
 foreach($g in $d.geometry){foreach($p in $g.vertices){if($p.Count -ne 3){throw 'XYZ required'};foreach($v in $p){if([double]::IsNaN($v) -or [double]::IsInfinity($v)){throw 'Finite coordinates required'}}}}
 $frame=One-Outgoing $d.geometry $config.definitionRegion.internalDeviceFrame.handle
 if(!$frame.closed -or $frame.vertices.Count -lt 3){throw 'Closed device frame required'}
 function Statement($h,$expected){
  $s=One-Outgoing $d.statements $h
  if($s.rawText -cne $expected -or $s.type -cne 'TEXT' -or $s.parentHandle){throw 'Reviewed statement/carrier changed'}
  [pscustomobject]@{id='statement:'+ $s.handle;handle=$s.handle;entityType=$s.type;parentHandle=$s.parentHandle;rawText=$s.rawText;layer=$s.layer;coordinates=@{insertion=$s.insertion;alignment=$s.alignment;coordinateStatus=$s.coordinateStatus};sourceSnapshot=$s.sourceSnapshot;rawRecord=$s.rawRecord;evidenceType='DrawingFact';semanticStatus='candidate'}
 }
 function ObservedField($s){[pscustomobject]@{observationStatus='observed';statement=$s;bindingStatus='candidate_row_field_not_terminal_binding'}}
 $shared=@(foreach($s in $f.sharedStatements){Statement $s.handle $s.expectedRawText})
 $sharedIds=@($shared.id);$rows=@();$rules=@();$seen=@{}
 foreach($r in $f.rows){
  if($seen.ContainsKey($r.identifierHandle)){throw 'Duplicate row selection'};$seen[$r.identifierHandle]=$true
  $identifier=Statement $r.identifierHandle $r.expectedIdentifier
  $target=Statement $r.targetHandle $r.expectedTarget
  $cable=Statement $r.cableHandle $r.expectedCable
  $geometry=One-Outgoing $d.geometry $r.geometryHandle
  if($geometry.closed -or $geometry.vertices.Count -ne 2 -or (Distance-Outgoing $geometry.vertices[0] $geometry.vertices[1]) -le $tol){throw 'Nondegenerate two-point outgoing representation required'}
  $rowId=$config.id+':outgoing:'+ $identifier.handle
  $contact=Contact-Outgoing $geometry $frame $tol
  $contact|Add-Member sourceSnapshot $d.sourceSnapshot
  $contact|Add-Member geometryHandle $geometry.handle
  $contact|Add-Member frameHandle $frame.handle
  $power=[pscustomobject]@{observationStatus='not_observed';statement=$null;value=$null;unit=$null;bindingStatus='unresolved';scope='selected_local_row_not_global_absence'}
  if($r.powerHandle){$ps=Statement $r.powerHandle $r.expectedPower;$match=[regex]::Match($ps.rawText,'^(?<value>\d+(?:\.\d+)?)\s*(?<unit>[kK][wW])$');if(!$match.Success){throw 'Unsupported power declaration'}
   $power=[pscustomobject]@{observationStatus='observed';statement=$ps;value=[double]::Parse($match.Groups['value'].Value,[cultureinfo]::InvariantCulture);unit=$match.Groups['unit'].Value;bindingStatus='candidate_row_field';valueBasis='literal_row_text_not_configuration_parameter'}
  }
  $match=[regex]::Match($cable.rawText,'^(?<package>.+?)\s+(?<conduit>[A-Za-z]+\d+)\s+(?<methods>[A-Za-z]+(?:,[A-Za-z]+)*)$')
  if(!$match.Success -or $match.Groups['package'].Value -cne $f.reviewedPackagePhrase){throw 'Unsupported or changed package/token layout; review required'}
  function Token($value,$start){[pscustomobject]@{rawToken=$value;sourceStatement=$cable;span=@{start=$start;length=$value.Length};status='candidate';engineeringInterpretation='unresolved'}}
  $conduit=Token $match.Groups['conduit'].Value $match.Groups['conduit'].Index
  $methods=@();$offset=$match.Groups['methods'].Index
  foreach($token in ($match.Groups['methods'].Value -split ',')){$methods+=,(Token $token $offset);$offset+=$token.Length+1}
  $rule=[pscustomobject]@{id='procurement:'+ $identifier.handle;modelType='Procurement/QuantityRuleCandidate';sourceSnapshot=$d.sourceSnapshot;panelConfigurationId=$config.id;rowId=$rowId;sourceStatement=$cable;rawClaim=$match.Groups['package'].Value;claim=$f.procurementClaim;quantityInclusion='unresolved';status='candidate';scope='related_cable_only_no_automatic_conduit_exclusion'}
  $rules+=,$rule
  $tail=$null;$gap=$null
  if($r.tailGeometryHandle){$tail=One-Outgoing $d.geometry $r.tailGeometryHandle;$dist=[double]::PositiveInfinity;foreach($a in $geometry.vertices){foreach($b in $tail.vertices){$dist=[math]::Min($dist,(Distance-Outgoing $a $b))}}
   $gap=[pscustomobject]@{evidenceType='RepresentationGapEvidence';sourceSnapshot=$d.sourceSnapshot;sourceHandles=@($geometry.handle,$tail.handle);drawingUnitGap=$dist;method='minimum_distance_between_reported_endpoints';status='observed';action='preserved_not_filled';engineeringMeaning='unresolved'}
  }
  $alignment=@();$a=$geometry.vertices[0];$b=$geometry.vertices[1];$xy=[math]::Sqrt([math]::Pow(($b[0]-$a[0]),2)+[math]::Pow(($b[1]-$a[1]),2))
  if($xy -le $tol){throw 'XY layout basis unsupported'}
  foreach($s in @($identifier,$target,$cable)+@($power.statement|Where-Object {$null -ne $_})){
   $dx=$s.coordinates.insertion[0]-$a[0];$dy=$s.coordinates.insertion[1]-$a[1]
   $alignment+=,[pscustomobject]@{sourceStatement=$s.id;geometryHandle=$geometry.handle;longitudinalOffset=($dx*($b[0]-$a[0])+$dy*($b[1]-$a[1]))/$xy;transverseOffset=(-$dx*($b[1]-$a[1])+$dy*($b[0]-$a[0]))/$xy;basis='line_local_XY_frame';meaning='layout_only_not_binding';sourceSnapshot=$d.sourceSnapshot}
  }
  $missing=@('actual_terminal_identity_and_position','confirmed_electrical_port','cable_model_core_count_cross_section','switch_model_and_parameters_not_observed','dynamic_block_parameters_not_observed','conduit_and_installation_token_interpretation','supply_installation_responsibility_and_quantity_rules')
  if($null -eq $power.statement){$missing+=,'power_field_not_observed'}
  if($gap){$missing+=,'right_side_gap_meaning_unresolved'}
  if($contact.status -ne 'observed'){$missing+=,'unique_panel_boundary_contact'}
  $rows+=,[pscustomobject]@{modelType='OutgoingRowCandidate';sourceSnapshot=$d.sourceSnapshot;panelConfigurationId=$config.id;rowId=$rowId;rowIdentifier=$identifier;outgoingGeometry=$geometry;panelBoundaryContactEvidence=$contact;targetNameCandidate=(ObservedField $target);powerFieldCandidate=$power;cablePackageStatement=$cable;conduitToken=$conduit;installationMethodTokens=$methods;switchProtectionEvidence=@{observationStatus='not_observed';individualDeviceEvidence=@();scope='selected_row_only';sharedFunctionalClaimsDoNotEstablishIndividualDevices=$true};dynamicBlockParameters=@{observationStatus='not_observed';records=@()};sharedConfigurationStatements=$sharedIds;procurementQuantityRuleCandidate=$rule.id;additionalGeometry=$tail;gapEvidence=$gap;alignmentEvidence=$alignment;missingInformation=$missing;bindingStatus='candidate';electricalPortStatus='unresolved';terminalBindingStatus='unresolved'}
 }
 [pscustomobject]@{schemaVersion='1.0';modelType='OutgoingRowEvidenceModel';analysisRunId=[guid]::NewGuid().ToString();projectId=$f.projectId;panelConfigurationId=$config.id;sourceSnapshot=$d.sourceSnapshot;configurationModelSource=$f.configurationModel;regionId=$f.regionId;localViewId=$f.localViewId;scope='explicit_reviewed_row_selections_not_discovery';panelDeviceFrame=$frame;sharedConfigurationStatements=$shared;outgoingRows=$rows;procurementQuantityRuleCandidates=$rules;limitations=@('no confirmed field binding','no Circuit or actual terminal connection','no quantity exclusion or calculation','drawing-unit geometry only; CAD Z is not engineering elevation','not_observed is limited to this reviewed row evidence set')}
}
Export-ModuleMember -Function Read-OutgoingInputs,New-OutgoingRowModel
