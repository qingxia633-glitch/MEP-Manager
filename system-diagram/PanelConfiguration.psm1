Set-StrictMode -Version 2
Import-Module (Join-Path $PSScriptRoot 'SystemDiagram.psm1') -DisableNameChecking

function Copy-PanelData($v) { ConvertFrom-Json (ConvertTo-Json -InputObject $v -Depth 90) }
function Select-PanelOne($items,$handle) {
 $found=@($items|Where-Object handle -ceq $handle)
 if($found.Count -ne 1){throw "Expected one selected entity/statement: $handle"};$found[0]
}
function Assert-PanelSource($actual,$expected) {
 if($actual.sha256 -cne $expected.sha256 -or ($actual.dwg -split '[\\/]')[-1] -cne $expected.dwgName){throw 'Snapshot/document mismatch; no confirmation migration'}
}
function Read-PanelConfigurationInputs {
 param($Spec,[string]$Root=(Join-Path $PSScriptRoot '..'))
 $result=[ordered]@{}
 foreach($side in @('plan','definition')) {
  $src=$Spec.sources.$side;$path=Join-Path $Root $src.path
  if((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -cne $src.sha256){throw 'Snapshot changed; explicit review required'}
  $snapshot=Read-DiagramSnapshot $path
  Assert-PanelSource $snapshot.sourceSnapshot $src
  if($side -eq 'plan') {
   $entity=Select-PanelOne $snapshot.entities $Spec.plan.insertHandle
   $statements=@($snapshot.statements|Where-Object parentHandle -ceq $entity.handle)
   $result[$side]=[pscustomobject]@{sourceSnapshot=$snapshot.sourceSnapshot;entities=@($entity);statements=$statements;geometry=@()}
  } else {
   $handles=@($Spec.definition.titleHandle)+@($Spec.declarations|ForEach-Object {$_.handle})
   $statements=@(foreach($h in ($handles|Select-Object -Unique)){Select-PanelOne $snapshot.statements $h})
   $geometryHandles=@($Spec.definition.boundaryHandle,$Spec.definition.deviceFrameHandle)+@($Spec.declarations|Where-Object kind -eq 'outgoing_row'|ForEach-Object {$_.lineHandle})
   $text=[IO.File]::ReadAllText($path)
   $geometry=@(foreach($h in ($geometryHandles|Select-Object -Unique)){
    $matchesForHandle=[regex]::Matches($text,'(?ms)^EntityHandle="'+[regex]::Escape($h)+'"\r?\n.*?(?=^EntityHandle=|^LayerEntityCount=|\z)')
    if($matchesForHandle.Count -ne 1){throw "Missing/duplicate geometry: $h"}
    $body=$matchesForHandle[0].Value
    if($body -notmatch '(?m)^DXF_Type="LWPOLYLINE"'){throw 'Only selected LWPOLYLINE representations supported'}
    $vertices=@(foreach($p in [regex]::Matches($body,'(?m)^Vertex_WCS=\(([^)]+)\)')){
     ,@($p.Groups[1].Value -split ' '|ForEach-Object {[double]::Parse($_,[cultureinfo]::InvariantCulture)})
    })
    [pscustomobject]@{handle=$h;type='LWPOLYLINE';layer=[regex]::Match($body,'(?m)^Layer="([^"]+)"').Groups[1].Value;closed=($body -match '(?m)^Closed=T\r?$');vertices=$vertices;rawRecord=$body;sourceSnapshot=$snapshot.sourceSnapshot}
   })
   $result[$side]=[pscustomobject]@{sourceSnapshot=$snapshot.sourceSnapshot;entities=@();statements=$statements;geometry=$geometry}
  }
 }
 [pscustomobject]$result
}

function New-PanelConfigurationModel {
 param($Inputs,$Spec)
 # Work on detached data: no mutation of raw statements, input fixtures or old views.
 $data=Copy-PanelData $Inputs;$f=Copy-PanelData $Spec
 if(!$f.projectId -or $f.drawingSetCompleteness -notin @('unknown','incomplete')){throw 'Explicit project and incomplete/unknown drawing-set scope required'}
 foreach($side in @('plan','definition')) {
  Assert-PanelSource $data.$side.sourceSnapshot $f.sources.$side
  foreach($r in @($data.$side.entities)+@($data.$side.statements)+@($data.$side.geometry)) {Assert-PanelSource $r.sourceSnapshot $f.sources.$side}
 }
 $plan=Select-PanelOne $data.plan.entities $f.plan.insertHandle
 $label=Select-PanelOne $data.plan.statements $f.plan.identifierHandle
 $title=Select-PanelOne $data.definition.statements $f.definition.titleHandle
 if($plan.type -cne 'INSERT' -or $label.type -cne 'ATTRIB' -or $label.parentHandle -cne $plan.handle -or $title.type -cne 'TEXT' -or $title.parentHandle){throw 'Invalid instance identifier or definition title carrier'}
 if($label.rawText -cne $f.plan.expectedIdentifier -or $title.rawText -cne $f.definition.expectedIdentifier){throw 'Selected identifier text changed'}
 $boundary=Select-PanelOne $data.definition.geometry $f.definition.boundaryHandle
 $frame=Select-PanelOne $data.definition.geometry $f.definition.deviceFrameHandle
 if(!$boundary.closed -or !$frame.closed){throw 'Confirmed region frames must retain their reported closure'}
 $evidence=@();$raw=@();$statements=@();$attributes=@();$rows=@();$conflicts=@();$missing=@()
 function Ref($record,$side) {
  $parent=$null;if($record.PSObject.Properties['parentHandle']){$parent=$record.parentHandle}
  [pscustomobject]@{projectId=$f.projectId;documentId=$f.sources.$side.documentId;sourceSnapshot=$record.sourceSnapshot;handle=$record.handle;parentHandle=$parent;entityType=$record.type;regionId=$f.sources.$side.regionId;localViewId=$f.sources.$side.localViewId}
 }
 function EvidenceId($side,$h) { $side+':fact:'+ $h }
 foreach($side in @('plan','definition')) {
  foreach($r in @($data.$side.entities)+@($data.$side.geometry)+@($data.$side.statements)) {
   # TEXT occurs only in statements here; each source representation stays separate.
   $id=EvidenceId $side $r.handle
   $raw+=,[pscustomobject]@{id=$id;sourceRef=(Ref $r $side);record=$r}
   $evidence+=,[pscustomobject]@{id=$id;evidenceType='DrawingFact';sourceRef=(Ref $r $side);readStatus='read';rawRecord=$r.rawRecord}
  }
 }
 $human=@()
 foreach($side in @('plan','definition')) {
  $hc=$f.humanConfirmations.$side
  if($null -eq $hc){$missing+=,"$side human confirmation";continue}
  foreach($key in @('documentId','regionId','localViewId')) {if($hc.scope.$key -cne $f.sources.$side.$key){throw "Human confirmation $key scope mismatch"}}
  if($hc.evidenceType -cne 'HumanConfirmation' -or $hc.status -cne 'confirmed' -or $hc.scope.projectId -cne $f.projectId -or $hc.scope.snapshotSHA256 -cne $data.$side.sourceSnapshot.sha256){throw 'Human confirmation project/snapshot/status mismatch'}
  $expected=if($side -eq 'plan'){@($plan.handle,$label.handle)}else{@($title.handle,$boundary.handle,$frame.handle)}
  if(@(Compare-Object @($hc.scope.anchorHandles|Sort-Object) @($expected|Sort-Object)).Count){throw 'Human confirmation anchor mismatch'}
  $hc|Add-Member -NotePropertyName sourceSnapshot -NotePropertyValue $data.$side.sourceSnapshot
  $human+=,$hc;$evidence+=,$hc
 }
 foreach($d in $f.declarations) {
  $s=Select-PanelOne $data.definition.statements $d.handle
  if($s.rawText -cne $d.expectedRawText){throw "Declaration text changed: $($d.handle)"}
  $sid='statement:'+ $s.handle;$aid='attribute:'+ $s.handle
  $value=$s.rawText;$unit=$null;$parseBasis='whole_raw_text';$component=$null
  if($d.kind -eq 'numeric') {
   $m=[regex]::Match($s.rawText,'^(?<field>[A-Za-z]+)\s*=\s*(?<value>\d+(?:\.\d+)?)\s*(?<unit>[A-Za-z]+)$')
   if(!$m.Success -or $m.Groups['field'].Value -cne $d.field){throw 'Unsupported numeric declaration'}
   $value=[double]::Parse($m.Groups['value'].Value,[cultureinfo]::InvariantCulture);$unit=$m.Groups['unit'].Value;$parseBasis='literal_field_equals_decimal_unit'
  } elseif($d.kind -eq 'excerpt') {
   if(!$d.excerpt -or !$s.rawText.Contains($d.excerpt)){throw 'Missing literal declaration excerpt'}
   $value=$d.excerpt;$component=@{start=$s.rawText.IndexOf($d.excerpt);length=$d.excerpt.Length};$parseBasis='explicit_literal_excerpt';
  } elseif($d.kind -notin @('text','outgoing_row')) {throw 'Unsupported declaration kind'}
  $support=@((EvidenceId 'definition' $s.handle));$visible='not_individually_confirmed';$visibleExcerpt=$null
  if($null -ne $f.humanConfirmations.definition) {
   $claims=@($f.humanConfirmations.definition.visibleTextClaims|Where-Object handle -ceq $s.handle)
   if($claims.Count -gt 1){throw 'Duplicate human text claim'}
   if($claims.Count){if(!$claims[0].excerpt -or !$s.rawText.Contains($claims[0].excerpt)){throw 'Human visible text claim differs from source'};$visible='human_confirmed_excerpt';$visibleExcerpt=$claims[0].excerpt;$support+=,$f.humanConfirmations.definition.id}
  }
  $statements+=,[pscustomobject]@{id=$sid;modelType='StatementCandidate';sourceRef=(Ref $s 'definition');handle=$s.handle;parentHandle=$s.parentHandle;rawText=$s.rawText;layer=$s.layer;insertion=$s.insertion;sourceSnapshot=$s.sourceSnapshot;candidateKind=$d.field;bindingStatus='candidate_configuration_membership';evidenceRefs=$support;visibilityStatus=$visible;confirmedVisibleExcerpt=$visibleExcerpt}
  $attributes+=,[pscustomobject]@{id=$aid;modelType='ConfigurationAttributeCandidate';field=$d.field;value=$value;unit=$unit;handle=$s.handle;rawText=$s.rawText;sourceSnapshot=$s.sourceSnapshot;sourceStatement=$sid;sourceRef=(Ref $s 'definition');evidenceRefs=$support;status='candidate';valueBasis='drawing_statement_only';parseBasis=$parseBasis;rawTextSpan=$component;conflicts=@()}
  if($d.kind -eq 'outgoing_row') {
   $line=Select-PanelOne $data.definition.geometry $d.lineHandle
   $rows+=,[pscustomobject]@{modelType='DiagramRowCandidate';rowId='outgoing:'+ $s.handle;localViewId=$f.sources.definition.localViewId;sourceSnapshot=$s.sourceSnapshot;rowBasis=@{kind='explicit_reviewed_line_and_label_selection';sourceRef=(Ref $line 'definition');vertices=$line.vertices};labelStatement=$sid;rawLabel=$s.rawText;memberRepresentations=@((Ref $s 'definition'),(Ref $line 'definition'));status='candidate';semanticStatus='outgoing_expression_not_final_circuit';evidenceRefs=@((EvidenceId 'definition' $s.handle),(EvidenceId 'definition' $line.handle));conflicts=@()}
  }
 }
 # Confirmations may mention only selected title/declarations, never nearby text.
 if($null -ne $f.humanConfirmations.definition) {
  foreach($claim in $f.humanConfirmations.definition.visibleTextClaims){$s=Select-PanelOne $data.definition.statements $claim.handle;if(!$claim.excerpt -or !$s.rawText.Contains($claim.excerpt)){throw 'Out-of-scope or changed human text claim'}}
 }
 $rule=$f.projectRule
 if($null -ne $rule) {
  if($rule.evidenceType -cne 'ProjectRule' -or $rule.scope.projectId -cne $f.projectId -or $rule.scope.objectType -cne 'panel' -or $rule.predicate -cne 'same_identifier_uses_same_configuration' -or $rule.status -cne 'human_confirmed'){throw 'Invalid project rule scope'}
  if($rule.sourceEvidence.evidenceType -cne 'HumanConfirmation' -or $rule.sourceEvidence.scope.projectId -cne $f.projectId){throw 'Project rule requires scoped human source'}
  $evidence+=,$rule.sourceEvidence;$evidence+=,$rule
 }else{$missing+=,'project-specific same-identifier configuration rule'}
 if($label.rawText -cne $title.rawText){$conflicts+=,[pscustomobject]@{id='identifier-conflict';field='panelIdentifier';sourceRefs=@((Ref $label 'plan'),(Ref $title 'definition'));claims=@($label.rawText,$title.rawText);status='unresolved'}}
 $configId=$f.projectId+':configuration:'+ $data.definition.sourceSnapshot.sha256+':'+$title.handle
 $instanceId=$f.projectId+':instance:'+ $data.plan.sourceSnapshot.sha256+':'+$plan.handle
 $config=[pscustomobject]@{modelType='PanelConfigurationCandidate';id=$configId;projectId=$f.projectId;panelIdentifier=@{rawValue=$title.rawText;sourceRef=(Ref $title 'definition')};status=if($null -ne $f.humanConfirmations.definition){'supported'}else{'candidate'};definitionRegion=@{regionId=$f.sources.definition.regionId;localViewId=$f.sources.definition.localViewId;sourceSnapshot=$data.definition.sourceSnapshot;title=(Ref $title 'definition');boundary=(Ref $boundary 'definition');internalDeviceFrame=(Ref $frame 'definition');extentStatus='reviewed_local_expression_not_whole_drawing'};configurationAttributes=$attributes;outgoingRowCandidates=$rows;humanConfirmationRefs=@($human|Where-Object {$_.scope.documentId -ceq $f.sources.definition.documentId}|ForEach-Object {$_.id});conflicts=@()}
 $instance=[pscustomobject]@{modelType='PanelInstanceCandidate';id=$instanceId;projectId=$f.projectId;sourceRef=(Ref $plan 'plan');identifierStatement=$label;otherRawStatements=@($data.plan.statements|Where-Object handle -cne $label.handle);status=if($null -ne $f.humanConfirmations.plan){'supported'}else{'candidate'}}
 $support=@((EvidenceId 'plan' $plan.handle),(EvidenceId 'plan' $label.handle),(EvidenceId 'definition' $title.handle))+@($human|ForEach-Object {$_.id})
 if($null -ne $rule){$support+=,$rule.id}
 $status=if($conflicts.Count){'ambiguous'}elseif($missing.Count){'candidate'}else{'supported'}
 $relation=[pscustomobject]@{id='usesConfiguration:1';modelType='BindingHypothesis';relationType='usesConfiguration';subject=$instanceId;candidateTargets=@($configId);status=$status;projectScope=$f.projectId;supportingEvidence=$support;opposingEvidence=@($conflicts|ForEach-Object {$_.id});missingEvidence=$missing;limitations=@('not same RawEntity','not same installed instance','not electrical connection','no cross-DWG coordinate matching','no automatic configuration propagation')}
 [pscustomobject]@{schemaVersion='1.0';modelType='PanelConfigurationEvidenceModel';analysisRunId=[guid]::NewGuid().ToString();projectId=$f.projectId;drawingSet=@{id=$f.drawingSetId;completeness=$f.drawingSetCompleteness;documents=@($f.sources.plan,$f.sources.definition)};scope='explicit_reviewed_fixture_not_discovery';rawRepresentations=$raw;statements=$statements;evidence=$evidence;humanConfirmations=$human;projectRules=@($rule|Where-Object {$null -ne $_});panelInstances=@($instance);panelConfigurations=@($config);bindingHypotheses=@($relation);conflicts=$conflicts;limitations=@('declarations remain candidate attributes','upstream reference unresolved','no design applicability or revision priority inferred','CAD Z is not engineering elevation','no circuits, electrical connections, paths or quantities')}
}
Export-ModuleMember -Function Read-PanelConfigurationInputs,New-PanelConfigurationModel
