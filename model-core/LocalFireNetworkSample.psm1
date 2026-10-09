# Bounded sample adapter: Handles/context selections live in the fixture manifest.
# Policy and geometry functions have no sample-specific identifiers.
Import-Module (Join-Path $PSScriptRoot 'LocalLogicalNetwork.psm1')
Import-Module (Join-Path $PSScriptRoot 'ModelCore.psm1')
Import-Module (Join-Path $PSScriptRoot '../design-knowledge/EvidenceAdmission.psm1')
. (Join-Path $PSScriptRoot '../design-knowledge/tests/Read-RelationChainFixture.ps1')
. (Join-Path $PSScriptRoot 'Read-GapBoundaryFixture.ps1')
function Read-LocalFireNetworkBundle {
 param([string]$Root=(Join-Path $PSScriptRoot '..'))
 $m=Get-Content (Join-Path $PSScriptRoot 'tests/local-fire-network-fixture.json') -Raw -Encoding UTF8|ConvertFrom-Json
 $path=Join-Path $Root $m.source.path
 if((Get-FileHash $path).Hash-cne $m.source.sha256){throw 'Local network snapshot changed'}
 $s=[IO.File]::ReadAllText($path)
 function Field($r,$k){[regex]::Match($r,'(?m)^'+[regex]::Escape($k)+'=(.*?)\r?$').Groups[1].Value.Trim('"')}
 function Points($r,$k){,@([regex]::Matches($r,'(?m)^'+[regex]::Escape($k)+'=\(([^)]+)\)')|ForEach-Object {,@($_.Groups[1].Value.Split(' ')|ForEach-Object {[double]::Parse($_,[cultureinfo]::InvariantCulture)})})}
 if($s-notmatch '(?m)^END_OF_REPORT' -or (Field $s ReadErrorCount)-ne '0'){throw 'Source report not accepted'}
 $doc=Field $s DWG;$records=@{};$offsets=@{}
 foreach($v in [regex]::Matches($s,'(?ms)^EntityHandle=.*?(?=^EntityHandle=|^LayerEntityCount=|^LAYER_END|\z)')){$h=Field $v.Value EntityHandle;$records[$h]=$v.Value;$offsets[$h]=@($v.Index,$v.Length)}
 $refs=[ordered]@{};$handles=[ordered]@{}
 function AddRef($h){
  if(!$records.ContainsKey($h)){throw "Missing local source $h"};$id=$m.source.sha256+':'+$h
  if(!$refs.Contains($id) -or !$refs[$id].PSObject.Properties['rawLayer']){$r=$records[$h];$refs[$id]=[pscustomobject]@{resolved=$true;sourceSnapshot=$m.source.sha256;sourcePath=$m.source.path;sourceDocument=$doc;handle=$h;entityType=(Field $r DXF_Type);rawLayer=(Field $r Layer);referencedDefinition=(Field $r BlockName);sourceSpan=[pscustomobject]@{offset=$offsets[$h][0];length=$offsets[$h][1];unit='utf16_code_units'};coordinateFrame='WCS';position=(Points $r Insertion_WCS)}}
  $handles[$h]=$id;return $id
 }
 function Attribs($h){
  @(foreach($am in [regex]::Matches($records[$h],'(?m)^Attribute_DXF=(.*)')){
   $d=$am.Groups[1].Value;$ah=[regex]::Match($d,'\(5 \. "([^"]*)"\)').Groups[1].Value;$id=$m.source.sha256+':'+$ah
   $refs[$id]=[pscustomobject]@{resolved=$true;sourceSnapshot=$m.source.sha256;sourcePath=$m.source.path;sourceDocument=$doc;handle=$ah;parentRef=(AddRef $h);entityType='ATTRIB';flags=[int][regex]::Match($d,'\(70 \. (\d+)\)').Groups[1].Value;sourceSpanRef=($m.source.sha256+':'+$h)}
   [pscustomobject]@{reference=$id;tag=[regex]::Match($d,'\(2 \. "([^"]*)"\)').Groups[1].Value;value=[regex]::Match($d,'\(1 \. "([^"]*)"\)').Groups[1].Value}
  })
 }
 $chainBundle=Read-RelationChainFixture;$chain=Get-RelationChainAdmission $chainBundle
 $role=Get-RoleEvidenceAdmission (Read-RoleAdmissionFixture)
 $alias=@{}
 foreach($p in $chainBundle.references.PSObject.Properties){$id=$p.Value.sourceSnapshot+':'+$p.Value.handle;$alias[$p.Name]=$id;$refs[$id]=$p.Value}
 function Aliases($ids){foreach($item in $ids){if(!$alias.ContainsKey($item)){throw 'Missing role evidence alias'};$alias[$item]}}
 $regionRef=AddRef $m.regionHandle
 $region=[pscustomobject]@{reference=$regionRef;titleCandidate=(Field $records[$m.regionHandle] Text_RAW);window=$m.window;scopeStatus='local_investigation_window_not_engineering_boundary';sourceSnapshot=$m.source.sha256}
 $up=AddRef $m.upstreamText
 $upstream=[pscustomobject]@{modelType='UpstreamSourceCandidate';sourceRefs=@($up);rawTextRef=$up;targetInstance='unresolved';status='candidate';noAutomaticConnection=$true}
 function Inside($point){$point[0]-ge $m.window[0] -and $point[0]-le $m.window[2] -and $point[1]-ge $m.window[1] -and $point[1]-le $m.window[3]}
 $networks=@()
 $boundaryProofs=@{}
 foreach($probe in $m.boundaryProbes){
  $proof=Read-GapBoundaryFixture $Root $probe $records[$probe.object]
  $objRef=AddRef $probe.object;$proof|Add-Member objectRef $objRef
  $attrRefs=@(Attribs $probe.object|ForEach-Object reference)
  $proof|Add-Member instanceAttributeRefs $attrRefs
  foreach($ref in $proof.references){$refs[$ref.id]=$ref}
  $boundaryProofs[$probe.object]=$proof
 }
 foreach($spec in $m.networks){
  $context=@($spec.contextRefs|ForEach-Object {AddRef $_});$nodes=@();$relations=@();$excluded=@();$open=@();$gaps=@();$covered=@{};$gapEnds=@{};$linePoints=@{};$lineBulges=@{};$regionBoundaries=@()
  foreach($h in $spec.lines){
   $id=AddRef $h;$r=$records[$h];$pts=Points $r Vertex_WCS
   $bulges=@([regex]::Matches($r,'Width_or_bulge_DXF=\(42 \. ([^)]+)')|ForEach-Object {[double]::Parse($_.Groups[1].Value,[cultureinfo]::InvariantCulture)})
   if((Field $r DXF_Type)-ne 'LWPOLYLINE' -or $pts.Count-ne 2){throw "This fixture requires two-vertex polylines: $h"}
   $linePoints[$h]=$pts
   $lineBulges[$h]=$bulges
   $refs[$id]|Add-Member -NotePropertyName bulgesRaw -NotePropertyValue $bulges -Force
   $basis=if($id-eq $alias.lowerLine -and $spec.system-eq 'fire_broadcast'){'endpoint roles + local system context'}else{'reviewed local system text and line context'}
   $nodeKind=if($h-ceq $spec.bus){'shared_bus_representation_candidate'}else{'line_representation_candidate'}
   $nodes+=,[pscustomobject]@{representationRef=$id;systemIdentity=$spec.system;nodeKind=$nodeKind;roleCandidate=$nodeKind;roleStatus='candidate';scopeBasis=$basis;evidenceRefs=@($id)+$context}
   for($endpoint=0;$endpoint-lt 2;$endpoint++){
    if(!(Inside $pts[$endpoint])){
     # Intersections with the investigation window, retaining the entire raw segment.
     $other=$pts[1-$endpoint];$outside=$pts[$endpoint]
     if(Inside $other){
      if(@($bulges|Where-Object {$_-ne 0}).Count){throw 'Window clipping of curved segment is not supported'}
      $ts=@();for($axis=0;$axis-lt 2;$axis++){$delta=$outside[$axis]-$other[$axis];if($delta-ne 0){foreach($border in @($m.window[$axis],$m.window[$axis+2])){$t=($border-$other[$axis])/$delta;if($t-gt 0 -and $t-le 1){$ts+=$t}}}}
      $t=($ts|Measure-Object -Minimum).Minimum
      $point=@(0..2|ForEach-Object {$other[$_]+$t*($outside[$_]-$other[$_])})
      $regionBoundaries+=,[pscustomobject]@{representationRef=$id;point=$point;rawEndpointIndex=$endpoint}
     }
    }
   }
  }
  foreach($h in $spec.devices){
   $id=AddRef $h;$attrs=Attribs $h;$name=@($attrs|Where-Object {$_.tag-eq 'A' -and $_.value})
   $roleName=if($name.Count){$name[0].value}else{'unknown'};$roleRefs=@($id)+@($name|ForEach-Object reference);$status=if($name.Count){'candidate'}else{'unresolved'}
   $override=@($spec.roleTextOverrides|Where-Object device -CEQ $h)
   if($override.Count){$roleRefs+=@($override[0].sourceRefs|ForEach-Object {AddRef $_});$roleName=(@($override[0].sourceRefs|ForEach-Object {Field $records[$_] Text_RAW}) -join '');$status='candidate'}
   if($id-eq $alias.instance){$roleName=$role.deviceRole.roleCandidate;$status=$role.deviceRole.status;$roleRefs+=@(Aliases $role.deviceRole.sourceRefs)}
   $nodes+=,[pscustomobject]@{representationRef=$id;systemIdentity=$spec.system;nodeKind='device_category_candidate';roleCandidate=$roleName;roleStatus=$status;scopeBasis='source name or reviewed role; system-specific representation only';evidenceRefs=@($roleRefs)+$context}
  }
  for($i=0;$i-lt $spec.lines.Count;$i++){for($j=$i+1;$j-lt $spec.lines.Count;$j++){
   $ha=$spec.lines[$i];$hb=$spec.lines[$j];$a=AddRef $ha;$bb=AddRef $hb
   $geo=Get-LocalSegmentRelation $linePoints[$ha] $linePoints[$hb] $m.tolerance $lineBulges[$ha] $lineBulges[$hb]
   $local=@($geo.contacts|Where-Object {Inside $_.point})
   if(!$local.Count){continue}
   if(!$geo.eligibleContact){$excluded+=,[pscustomobject]@{representationRefs=@($a,$bb);geometryType=$geo.geometryType;geometryEvidence=$geo;evidenceRefs=@($a,$bb);reason='interior crossing or overlap is not endpoint contact'};continue}
   foreach($c in $local){if($c.endpointA-ge 0){$covered[$ha+':'+$c.endpointA]=$true};if($c.endpointB-ge 0){$covered[$hb+':'+$c.endpointB]=$true}}
   $relations+=,[pscustomobject]@{fromRef=$a;toRef=$bb;systemIdentity=$spec.system;relationType=if($spec.bus-in @($ha,$hb) -and $geo.geometryType-eq 'endpoint_on_segment'){'branch_to_bus'}else{'line_to_line'};geometryType=$geo.geometryType;geometryStatus='supported';geometryEvidence=$geo;semanticStatus='supported_candidate';evidenceRefs=@($a,$bb)+$context}
  }}
  foreach($h in $spec.excludedCrossings){
   $id=AddRef $h;$geo=Get-LocalSegmentRelation (Points $records[$h] Vertex_WCS) $linePoints[$spec.bus] $m.tolerance
   $excluded+=,[pscustomobject]@{representationRefs=@($id,(AddRef $spec.bus));geometryType=$geo.geometryType;geometryEvidence=$geo;evidenceRefs=@($id);reason='reviewed crossing without endpoint contact; not admitted'}
  }
  # Only the already probed module/speaker contacts are eligible device edges.
  $deviceContacts=@()
  if($spec.system-eq 'fire_alarm'){$deviceContacts+=@($role.lineRelations|Where-Object fromRef -EQ 'upperLine')}
  if($spec.system-eq 'fire_broadcast'){$deviceContacts+=@($role.lineRelations|Where-Object fromRef -EQ 'leftLine');$deviceContacts+=@($chain.lineRelations)}
  foreach($contact in $deviceContacts){
   $from=$alias[$contact.fromRef];$to=$alias[$contact.toRef]
   if(!$from -or !$to -or $contact.status-ne 'supported'){continue}
   $lineHandle=$refs[$from].handle;$endpoint=if($to-eq $alias.speaker){1}else{0}
   $covered[$lineHandle+':'+$endpoint]=$true
   $proof=@(Aliases $contact.sourceRefs)
   $relations+=,[pscustomobject]@{fromRef=$from;toRef=$to;systemIdentity=$spec.system;relationType='line_to_device_representation';geometryType=if($contact.boundary-eq 'top'){'boundary_contact'}else{'boundary_crossing'};geometryStatus='supported';geometryEvidence=[pscustomobject]@{sourceRelationRef=$contact.fromRef+':'+$contact.toRef;endpointIndex=$endpoint;proofRefs=$proof;meaning='previously probed boundary contact/crossing; not port';coordinateFrame='WCS'};semanticStatus='supported_candidate';evidenceRefs=$proof+$context}
  }
  foreach($gap in $spec.gaps){
   $a=AddRef $gap.a;$bb=AddRef $gap.b;$obj=AddRef $gap.object;$pa=$linePoints[$gap.a][$gap.aEnd];$pb=$linePoints[$gap.b][$gap.bEnd]
   $d2=0.;for($axis=0;$axis-lt 3;$axis++){$d2+=[math]::Pow($pa[$axis]-$pb[$axis],2)}
   $gaps+=,[pscustomobject]@{fromRef=$a;toRef=$bb;fromPoint=$pa;toPoint=$pb;probableBoundaryObject=$obj;reason=$gap.reason;separationDrawingUnits=[math]::Sqrt($d2)}
   if($boundaryProofs.ContainsKey($gap.object)){$gaps[-1]|Add-Member boundaryEvidence $boundaryProofs[$gap.object]}
   $gapEnds[$gap.a+':'+$gap.aEnd]=$obj;$gapEnds[$gap.b+':'+$gap.bEnd]=$obj
  }
  $unexpanded=@(foreach($pair in $spec.unexpandedAssociations){[pscustomobject]@{lineRef=(AddRef $pair[0]);deviceRef=(AddRef $pair[1]);systemIdentity=$spec.system;geometryStatus='unresolved';semanticStatus='category_layout_candidate';admissionStatus='blocked';blockingReasons=@('device_boundary_or_port_unread');evidenceRefs=@((AddRef $pair[0]),(AddRef $pair[1]))+$context}})
  foreach($h in $spec.lines){for($end=0;$end-lt 2;$end++){
   $point=$linePoints[$h][$end];$key=$h+':'+$end
   if((Inside $point) -and !$covered.ContainsKey($key)){
    $kind=if($gapEnds.ContainsKey($key)){'gap_endpoint'}elseif(@($unexpanded|Where-Object lineRef -EQ $handles[$h]).Count){'device_relation_unresolved'}else{'unresolved_termination'}
    $open+=,[pscustomobject]@{representationRef=$handles[$h];endpointIndex=$end;point=$point;coordinateFrame='WCS';kind=$kind;status='unresolved';evidenceRefs=@($handles[$h]);portRole='unresolved'}
   }
  }}
  $networks+=,[pscustomobject]@{system=$spec.system;nodes=$nodes;relations=$relations;gaps=$gaps;excludedRelations=$excluded;regionBoundaries=$regionBoundaries;openEnds=$open;unresolvedEndpointAssociations=$unexpanded;evidenceRefs=$context+@($nodes|ForEach-Object evidenceRefs|Select-Object -Unique)}
 }
 $cross=@(foreach($c in $m.crossSystems){[pscustomobject]@{representationRef=(AddRef $c.representation);systems=$c.systems;evidenceRefs=@($c.sourceRefs|ForEach-Object {AddRef $_});basis=$c.basis}})
 # Requirement states come from the existing Golden artifact, never re-resolved here.
 $rm=Get-Content (Join-Path $PSScriptRoot '../design-knowledge/tests/role-admission-sample.json') -Raw -Encoding UTF8|ConvertFrom-Json
 $reqFile=Join-Path $Root $rm.requirementSource.path
 if((Get-FileHash $reqFile).Hash-cne $rm.requirementSource.sha256){throw 'Golden requirement source changed'}
 $existing=Get-Content $reqFile -Raw -Encoding UTF8|ConvertFrom-Json
 $reqs=@(foreach($system in @('fire_phone','fire_broadcast','fire_alarm')){
  $rid=switch($system){fire_phone {'req:phone-relation'} fire_broadcast {'req:broadcast'} fire_alarm {'req:membership'}}
  $match=@($existing.requirements|Where-Object requirementRef -CEQ $rid);if($match.Count-ne 1){throw 'Golden requirement absent'}
  [pscustomobject]@{requirementId=$rid;systemIdentity=$system;status=$match[0].statusUnchanged;projectId=$m.projectId;sourceRegionRef=$regionRef;source=$rm.requirementSource;scopeBinding='current user-authorized local investigation, not fulfilled fact'}
 })
 $reviews=@(foreach($review in $chain.reviewItems){$v=$review|ConvertTo-Json -Depth 40|ConvertFrom-Json;$v.sourceRefs=@(Aliases $v.sourceRefs);$v})
 $coverage=@(foreach($capability in @('boundary_object_relation','gap_semantic_refinement')){
  New-CapabilityCoverage -CapabilityId $capability -Domain electrical -ObjectType NetworkGapCandidate -CapabilityType evidence_boundary -Status validated_sample -ValidatedSamples @($m.sampleId) -ApplicableScope 'Reviewed local terminal-box probe and three independent system gaps' -KnownLimitations @('No internal continuity, terminal mapping, physical connections or routing','One real sample; no reusable claim') -EvidenceRefs @($boundaryProofs.Values|ForEach-Object evidenceRefs) -Version '1.0'
 })
 [pscustomobject]@{sampleId=$m.sampleId;projectId=$m.projectId;sourceRegion=$region;upstreamSourceCandidate=$upstream;references=[pscustomobject]$refs;handleIndex=[pscustomobject]$handles;networks=$networks;crossSystems=$cross;requirements=$reqs;reviewItems=$reviews;capabilityCoverage=$coverage}
}
Export-ModuleMember -Function Read-LocalFireNetworkBundle
