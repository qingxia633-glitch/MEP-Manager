Set-StrictMode -Version 2
Import-Module (Join-Path $PSScriptRoot 'ModelCore.psm1')
function Read-FireGoldenModel {
 param([string]$Root=(Join-Path $PSScriptRoot '..'))
 $f=Get-Content (Join-Path $PSScriptRoot 'tests/fire-fixture.json') -Raw -Encoding UTF8|ConvertFrom-Json
 foreach($source in @($f.source,$f.rule)){
  if((Get-FileHash -LiteralPath (Join-Path $Root $source.path)).Hash -cne $source.sha256){throw 'Pinned fire source changed'}
 }
 $text=[IO.File]::ReadAllText((Join-Path $Root $f.source.path))
 function Field($r,$k){[regex]::Match($r,'(?m)^'+[regex]::Escape($k)+'=(.*?)\r?$').Groups[1].Value.Trim('"')}
 if(!(Field $text DWG).EndsWith($f.source.dwgName) -or $text -notmatch '(?m)^END_OF_REPORT' -or (Field $text ReadErrorCount) -ne '0'){throw 'Fire source not accepted'}
 $records=@{}
 foreach($m in [regex]::Matches($text,'(?ms)^EntityHandle=.*?(?=^EntityHandle=|^LayerEntityCount=|^LAYER_END|\z)')){$records[(Field $m.Value EntityHandle)]=$m.Value}
 function Record($h){
  if(!$records.ContainsKey($h)){throw "Fixture handle missing: $h"};$r=$records[$h]
  $attrs=@(foreach($m in [regex]::Matches($r,'(?m)^Attribute_DXF=(.*)')){
   $a=$m.Groups[1].Value
   [pscustomobject]@{handle=[regex]::Match($a,'\(5 \. "([^"]*)"\)').Groups[1].Value;tag=[regex]::Match($a,'\(2 \. "([^"]*)"\)').Groups[1].Value;rawText=[regex]::Match($a,'\(1 \. "([^"]*)"\)').Groups[1].Value;flags=[int][regex]::Match($a,'\(70 \. (\d+)\)').Groups[1].Value;layer=[regex]::Match($a,'\(8 \. "([^"]*)"\)').Groups[1].Value;coordinateRaw=[regex]::Match($a,'\(10 ([^)]+)\)').Groups[1].Value;sourceSnapshot=$f.source;parentHandle=$h;rawDXF=$a}
  })
  [pscustomobject]@{id=($f.source.sha256+':'+$h);handle=$h;entityType=(Field $r DXF_Type);layer=(Field $r Layer);blockName=(Field $r BlockName);effectiveName=(Field $r EffectiveName_RAW);coordinatesRaw=(Field $r Insertion_WCS);verticesRaw=@([regex]::Matches($r,'(?m)^Vertex_WCS=(.*)')|ForEach-Object {$_.Groups[1].Value.Trim()});attributes=$attrs;rawRecord=$r;sourceSnapshot=$f.source;roleStatus='candidate';evaluatedVisibility='unknown'}
 }
 $representations=@(@($f.devices.handle)+@($f.lines.handle)+@($f.conflictHandles)|ForEach-Object {Record $_})
 $lookup=@{};foreach($r in $representations){$lookup[$r.handle]=$r}
 foreach($d in $f.devices){if(@($lookup[$d.handle].attributes|Where-Object rawText -CEQ $d.rawName).Count -ne 1){throw 'Device name fixture changed'}}
 foreach($l in $f.lines){if($lookup[$l.handle].layer -cne $l.layer){throw 'Line layer fixture changed'}}
 $systems=@{};$networks=@{}
 foreach($type in @('fire_alarm','fire_alarm_power','fire_phone','fire_broadcast','monitoring_security','other_weak_current','unknown')){
  $systems[$type]=New-SystemScope $f.projectId (New-SystemIdentity $type)
  if($type -ne 'unknown'){$networks[$type]=New-LogicalNetwork ($f.sampleId+':'+$type) $systems[$type]}
 }
 $socket=$lookup[$f.phoneSocketHandle];$phoneId=$socket.id+':phone-interface'
 $scope=@{projectId=$f.projectId;snapshotIds=@($f.source.sha256);subjectIds=@($representations.id)+@($networks.Values.networkId)+@($phoneId);regionId=$f.sampleId}
 $evidence=@();$associations=@()
 foreach($d in $f.devices){
  $r=$lookup[$d.handle]
  $ev=New-SystemEvidence ('role:'+ $r.handle) ('role:'+ $r.handle) DrawingFact supported $scope $systems.fire_alarm -Claim @{roleCandidate=$d.role;nameDeclaration=$d.rawName;finalDeviceType='unresolved'} -Provenance @{source=$r;interpretation='raw name supports device role candidate only'}
  $evidence+=,$ev
  $node=New-NetworkElement NodeCandidate $r.id LogicalNetwork @($ev.evidenceId) -Data @{representation=$r.id;roleCandidate=$d.role;loopId='unknown'} -SystemScope $systems.fire_alarm
  $networks.fire_alarm=Add-LogicalNetworkElement $networks.fire_alarm $node
  $associations+=, (New-AssociationCandidate $r.id belongsToSystemCandidate @($networks.fire_alarm.networkId) $scope @($ev) -Provenance @{sourceSnapshot=$f.source} -SystemScope $systems.fire_alarm -TargetSystemScopes @($systems.fire_alarm))
 }
 $phoneEv=New-SystemEvidence 'socket-capability' 'phone_socket_presence' DrawingFact candidate $scope $systems.fire_phone -Claim 'Name declaration includes phone socket; no terminal relation established' -Provenance @{source=$socket}
 $evidence+=,$phoneEv
 $phoneNode=New-NetworkElement NodeCandidate $phoneId LogicalNetwork @($phoneEv.evidenceId) -Data @{representation=$socket.id;interfaceRole='phone_socket_candidate';loopId='unknown'} -SystemScope $systems.fire_phone
 $networks.fire_phone=Add-LogicalNetworkElement $networks.fire_phone $phoneNode
 $cross=New-CrossSystemAssociationCandidate $socket.id @($phoneId) $systems.fire_alarm @($systems.fire_phone) $scope 'shared_representation_distinct_interface_candidates' @($evidence|Where-Object {$_.evidenceId -eq ('role:'+$socket.handle) -or $_.evidenceId -eq $phoneEv.evidenceId}) -MissingEvidence @('actual interfaces','phone network membership') -Provenance @{source=$socket}
 $human=@{kind='HumanConfirmation';source='user-provided building-4 legend transcription; source corrected to EC-4#-P+TBD_t8_t3.dwg';scope=$f.legendScope;originalSnapshot='not_supplied';originalHandle='not_supplied'}
 $legend=New-CrossDrawingLegendCandidate ($f.sampleId+':main-building-legend') $f.legendScope $f.legendEntries $human
 $ioSources=@($f.ioSupportingHandles|ForEach-Object {Record $_})
 $ioEntry=$f.legendEntries|Where-Object token -CEQ 'I/O'
 foreach($r in $ioSources){if(!@($r.attributes|Where-Object rawText -CEQ 'I/O').Count -or !@($r.attributes|Where-Object {$_.tag -eq 'A' -and $_.rawText -ceq $f.devices[-1].rawName}).Count){throw 'I/O support changed'}}
 $entry=New-LegendEntryCandidate $ioEntry.token $ioEntry.meaning $legend @{projectId=$f.projectId;snapshot=$f.source;representationIds=@($ioSources.id);propagation='reviewed_representations_only'} $ioSources supported
 $symbol=New-SymbolDefinitionCandidate ($f.sampleId+':io-symbol') @($ioSources.blockName|Select-Object -Unique) $ioSources $entry.applicableScope
 $reviews=@();$requirements=@()
 foreach($h in $f.conflictHandles){
  $r=$lookup[$h];$name=@($r.attributes|Where-Object tag -CEQ 'A');$label=@($r.attributes|Where-Object tag -CEQ '$TEXT$')
  if($label.Count -ne 1 -or $name.Count -ne 1 -or $label[0].rawText -cne 'I' -or $name[0].rawText -cne $f.devices[-1].rawName){throw 'Conflict fixture changed'}
  $legendI=$f.legendEntries|Where-Object token -CEQ 'I'
  $claims=@(@{kind='HumanConfirmation';declaration=$legendI;sourceScope=$f.legendScope;garageApplicability='unresolved'},@{kind='DrawingFact';name=$name[0];label=$label[0];sourceSnapshot=$f.source})
  $review=New-LegendConflictReview ('legend-conflict:'+ $r.id) $claims @($r,$name[0],$label[0]) @($f.source,$human) $systems.fire_alarm @($f.source.sha256,$legend.id)
  $reviews+=,$review
  $ev=New-SystemEvidence ('conflict:'+$h) ('role:I:'+$h) DerivedInference conflicting $scope $systems.fire_alarm -Claim @{reviewRef=$review.reviewId;claims=$claims} -Provenance @{humanLegend=$legend.id;rawRepresentation=$r;meaning='potential cross-drawing semantic conflict; no source chosen'}
  $evidence+=,$ev
  $requirements+=, (Resolve-InformationRequirement ('req:I:'+$h) 'resolve fire alarm device role' $ev.fact $scope @($ev) -SystemScope $systems.fire_alarm)
 }
 $requirements+=, (Resolve-InformationRequirement 'req:io-role' 'resolve fire alarm device role' ('role:'+$f.devices[-1].handle) $scope $evidence -SystemScope $systems.fire_alarm)
 $requirements+=, (Resolve-InformationRequirement 'req:phone-relation' 'resolve fire phone relation' 'phone_terminal_relation' $scope $evidence -SystemScope $systems.fire_phone)
 $requirements+=, (Resolve-InformationRequirement 'req:broadcast' 'resolve broadcast relation' 'broadcast_relation' $scope $evidence -SystemScope $systems.fire_broadcast)
 $membership=New-SystemEvidence 'membership-candidate' 'logical_membership' DerivedInference candidate $scope $systems.fire_alarm -Claim 'Devices form a system-category candidate collection; loop identity unknown' -Provenance @{associations=$associations}
 $evidence+=,$membership
 $requirements+=, (Resolve-InformationRequirement 'req:membership' 'resolve fire alarm logical network membership' 'logical_membership' $scope $evidence -SystemScope $systems.fire_alarm)
 $lineCandidates=@(foreach($l in $f.lines){[pscustomobject]@{representation=$lookup[$l.handle];systemScope=$systems[$l.systemCandidate];status='candidate';basis='layer clue only, no confirmed network membership';enteredLogicalNetwork=$false}})
 $contactLine=$lookup[$f.contactCandidate.lineHandle];$contactInsert=$lookup[$f.contactCandidate.insertHandle]
 function Coordinates($s){@([regex]::Matches($s,'-?\d+(?:\.\d+)?')|ForEach-Object {[double]::Parse($_.Value,[cultureinfo]::InvariantCulture)})}
 $point=Coordinates $contactInsert.coordinatesRaw
 $residuals=@(foreach($v in $contactLine.verticesRaw){$vp=Coordinates $v;if($vp.Count -eq 3 -and $point.Count -eq 3){[math]::Sqrt([math]::Pow($vp[0]-$point[0],2)+[math]::Pow($vp[1]-$point[1],2)+[math]::Pow($vp[2]-$point[2],2))}})
 $residual=($residuals|Measure-Object -Minimum).Minimum
 if($null -eq $residual -or $residual -gt $f.contactCandidate.tolerance){throw 'Reviewed endpoint/insertion contact changed'}
 $contact=New-NetworkElement ConnectionHypothesis ($f.sampleId+':geometric-contact') LogicalNetwork @($contactLine.id,$contactInsert.id) -SystemScope $systems.unknown -EndpointRefs @($contactLine.id,$contactInsert.id) -Data @{relation='vertex_equals_insert_point';residual=$residual;tolerance=$f.contactCandidate.tolerance;coordinateFrame='snapshot_WCS_drawing_units';electricalPort='unresolved';enteredLogicalNetwork=$false}
 $rule=New-RuleReference $f.rule.ruleId $f.rule.version @{domain='weak_current_fire';capability='system_identity_isolation';excludes=@('routing','quantity','wire specification resolution')} @($f.rule.sha256) $f.rule.path
 $rule|Add-Member -NotePropertyName sourceEvidence -NotePropertyValue $f.rule
 [pscustomobject]@{modelType='FireGoldenSampleModel';sampleId=$f.sampleId;sourceSnapshot=$f.source;window=$f.window;representations=$representations;crossDrawingLegend=$legend;legendEntries=@($entry);symbolDefinitions=@($symbol);reviews=$reviews;evidence=$evidence;requirements=$requirements;associations=$associations;crossSystemAssociations=@($cross);lineCandidates=$lineCandidates;connectionHypotheses=@($contact);networks=@($networks.Keys|Sort-Object|ForEach-Object {$networks[$_]});ruleReferences=@($rule);limitations=@('no confirmed loop or address','building reference incomplete','control wire system unknown','building 4 document legend scope not globally propagated','hidden attributes are not confirmed visible labels')}
}
Export-ModuleMember -Function Read-FireGoldenModel
