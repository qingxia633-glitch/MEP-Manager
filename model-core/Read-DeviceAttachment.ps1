param([string]$Root=(Join-Path $PSScriptRoot '..'),[string]$OutputPath)
$ErrorActionPreference='Stop'
foreach($pin in (Get-Content (Join-Path $PSScriptRoot 'tests/device-attachment-sources.json') -Raw -Encoding UTF8|ConvertFrom-Json)){
 if((Get-FileHash (Join-Path $Root $pin.path)).Hash -cne $pin.sha256){throw "Attachment input changed: $($pin.path)"}
}
if(-not ('Mep.DeviceRepresentation.Geometry' -as [type])){Add-Type -Path (Join-Path $PSScriptRoot 'DeviceRepresentation.cs')}
function Field($r,$k){[regex]::Match($r,'(?m)^'+[regex]::Escape($k)+'=(.*?)\r?$').Groups[1].Value.Trim('"')}
function Point($s){,[double[]]@([regex]::Matches($s,'[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?')|ForEach-Object {[double]::Parse($_.Value,[cultureinfo]::InvariantCulture)})}
function Transform($pts,$t){,[Mep.DeviceRepresentation.Geometry]::Transform([double[][]]$pts,$t.insertion,$t.scale,$t.rotation,$t.normal,$t.definitionBase,$t.dynamic,$t.nested)}
$routingPath='outputs/fire-alarm-routing/results.json'
$route=Get-Content (Join-Path $Root $routingPath) -Raw -Encoding UTF8|ConvertFrom-Json
$logical=Get-Content (Join-Path $Root 'outputs/fire-alarm-logical-network/results.json') -Raw -Encoding UTF8|ConvertFrom-Json
$source=$route.sourcePath
if((Get-FileHash (Join-Path $Root $source)).Hash -cne $route.sourceSnapshot){throw 'Source snapshot changed'}
$raw=[IO.File]::ReadAllText((Join-Path $Root $source));$records=@{}
foreach($r in [regex]::Split($raw,'(?m)(?=^EntityHandle=)')){$h=Field $r EntityHandle;if($h){$records[$h]=$r}}
$definitions=@{}
foreach($f in (Get-Content (Join-Path $PSScriptRoot 'tests/device-representation-fixture.json') -Raw -Encoding UTF8|ConvertFrom-Json)){
 $text=[IO.File]::ReadAllText((Join-Path $Root $f.probe));$hash=(Get-FileHash (Join-Path $Root $f.probe)).Hash
 if($hash -cne $f.sha256){throw 'Pinned definition changed'}
 if((Field $text DWG) -cne (Field $raw DWG) -or $text -notmatch '(?m)^END_OF_REPORT' -or (Field $text DefinitionIsDynamicBlock) -ne ':vlax-false'){throw 'Definition scope incomplete'}
 $parts=@{};$local=@();$diagnostics=@()
 foreach($r in [regex]::Split($text,'(?m)(?=^SourceInternalHandle=)')){
  $h=Field $r SourceInternalHandle;if(!$h){continue};$parts[$h]=$r;$type=Field $r DXF_Type
  if($r -match 'Error=|ERROR|UNREADABLE'){
   if($type -ne 'ATTDEF' -or $r -notmatch 'BoundsError='){throw 'Geometry diagnostic requires review'}
   $diagnostics+=@{handle=$h;type='attribute_bounds_unavailable';raw=(Field $r BoundsError)}
  }
  if($type -eq 'INSERT'){throw 'Nested definition requires separate transform admission'}
  if($type -in @('LINE','LWPOLYLINE','POINT','CIRCLE')){
   $pts=@([regex]::Matches($r,'(?m)^DXF:10=(.*?)\r?$')|ForEach-Object {$p=Point $_.Groups[1].Value;if($p.Count -eq 2){$p=[double[]]@($p[0],$p[1],0)};,$p})
   if($type -eq 'LINE'){$pts+=,(Point (Field $r 'DXF:11'))}
   $local+=@{ref=$hash+':'+$h;handle=$h;type=$type;points=$pts;radius=if($type -eq 'CIRCLE'){[double](Field $r 'DXF:40')}else{$null};semantic=if($type -eq 'POINT'){'reference_point'}elseif($h -in $f.boundaryRefs){'representation_boundary'}else{'symbol_geometry'}}
  }
 }
 $ring=@();$previous=$null;$first=$null
 foreach($h in $f.boundaryRefs){$r=$parts[$h];if(!$r -or (Field $r DXF_Type) -ne 'LINE'){throw 'Reviewed boundary line missing'};$a=Point (Field $r 'DXF:10');$b=Point (Field $r 'DXF:11');if($previous -and [math]::Sqrt([math]::Pow($previous[0]-$a[0],2)+[math]::Pow($previous[1]-$a[1],2)) -gt 1e-8){throw 'Boundary is not a real closed line chain'};if(!$first){$first=$a};$ring+=,$a;$previous=$b}
 if([math]::Sqrt([math]::Pow($previous[0]-$first[0],2)+[math]::Pow($previous[1]-$first[1],2)) -gt 1e-8){throw 'Open boundary'}
 $name=Field $text Block_BEGIN
 $definitions[$name]=@{blockDefinitionRef=$hash+':'+$name;sourcePath=$f.probe;sample=$f.sample;localGeometry=$local;boundary=$ring;boundaryRefs=$f.boundaryRefs;definitionBase=(Point (Field $text 'DefinitionDXF:10'));diagnostics=$diagnostics}
}
$geometry=@();$relations=@()
foreach($member in $logical.memberships){
 $h=$member.instanceRef.Split(':')[-1];$r=$records[$h];$name=Field $r BlockName;if(!$definitions.ContainsKey($name)){continue};$d=$definitions[$name]
 $t=@{insertion=(Point (Field $r Insertion_WCS));normal=(Point (Field $r Normal_DXF210));definitionBase=$d.definitionBase;scale=@();rotation=[double]::NaN;dynamic=((Field $r IsDynamicBlock) -ne ':vlax-false');nested=$false}
 foreach($code in @(41,42,43,50)){$v=[regex]::Match($r,'(?m)^BlockTransform_or_Array_DXF=\('+ $code+' \. ([^)]+)\)').Groups[1].Value;if(!$v){continue};if($code -eq 50){$t.rotation=[double]::Parse($v,[cultureinfo]::InvariantCulture)}else{$t.scale+=[double]::Parse($v,[cultureinfo]::InvariantCulture)}}
 foreach($code in @(70,71)){$v=[regex]::Match($r,'(?m)^BlockTransform_or_Array_DXF=\('+ $code+' \. ([^)]+)\)').Groups[1].Value;if(!$v -or [int]$v -gt 1){$t.nested=$true}}
 $g=[pscustomobject]@{modelType='DeviceRepresentationGeometryCandidate';instanceRef=$member.instanceRef;handle=$h;sample=$d.sample;blockDefinitionRef=$d.blockDefinitionRef;localGeometryRefs=@($d.localGeometry.ref);insertTransform=$t;worldGeometry=@();worldBoundary=@();representativePoints=@();geometryStatus='unresolved';evidenceRefs=@($member.roleEvidenceRef,$d.sourcePath);roleStatus=$member.roleStatus;diagnostics=$d.diagnostics}
 try {
  $g.worldBoundary=Transform $d.boundary $t
  $g.worldGeometry=@(foreach($item in $d.localGeometry){
   $curveBasis=@()
   if($item.type -eq 'CIRCLE'){$center=$item.points[0];$curveBasis=Transform @($center,[double[]]@(($center[0]+$item.radius),$center[1],$center[2]),[double[]]@($center[0],($center[1]+$item.radius),$center[2])) $t}
   @{sourceRef=$item.ref;type=$item.type;semantic=$item.semantic;worldPoints=(Transform $item.points $t);localRadius=$item.radius;worldCurveBasis=$curveBasis;curveMeaning=if($item.type -eq 'CIRCLE'){'center plus two radius basis points; affine circle; not used as boundary'}else{$null};curveTransformRef=$member.instanceRef;curveStatus=if($item.type -eq 'CIRCLE'){'parametric_affine_circle_not_used_as_boundary'}else{'supported_candidate'}}
  })
  $g.representativePoints=@($g.worldGeometry|Where-Object type -eq POINT|ForEach-Object {@{sourceRef=$_.sourceRef;point=$_.worldPoints[0];semantic='candidate_port_point';status='unresolved';confirmedPort=$false}})
  $g.geometryStatus='supported_candidate'
 }catch{$g|Add-Member blockingReason $_.Exception.Message}
 $geometry+=,$g
 foreach($edge in $route.edges){
  $calc=if($g.geometryStatus -eq 'supported_candidate'){[Mep.DeviceRepresentation.Geometry]::Relate($edge.startXY,$edge.endXY,[double[][]]$g.worldBoundary,0.001,1.0)}else{$null}
  $relations+=,[pscustomobject]@{modelType='DeviceEndpointRelationCandidate';routingEdgeRef=$edge.edgeId;routingEndpointRef=@($edge.fromNode,$edge.toNode);rawRoutingRef=$edge.rawEntityRef;deviceInstanceRef=$g.instanceRef;sample=$g.sample;relationType=if($calc){$calc.relationType}else{'unresolved'};distance=if($calc){$calc.distance}else{$null};intersectionPoint=if($calc){$calc.intersectionPoints}else{@()};endpointTypes=if($calc){$calc.endpointTypes}else{@('unresolved','unresolved')};status=if($calc){$calc.status}else{'unresolved'};attachmentAllowed=($calc -and $calc.attachmentAllowed);physicalConnection='unresolved';portRole='unresolved';evidenceRefs=@($g.blockDefinitionRef,$edge.rawEntityRef)}
 }
}
$golden=@(foreach($sample in @($geometry.sample|Select-Object -Unique)){
 $best=$relations|Where-Object sample -eq $sample|Sort-Object @{Expression={if($_.attachmentAllowed){0}elseif($_.relationType -in @('segment_crosses_boundary','crossing_through_representation')){1}else{2}}},distance,deviceInstanceRef,routingEdgeRef|Select-Object -First 1
 @{sample=$sample;geometry=($geometry|Where-Object instanceRef -eq $best.deviceInstanceRef);relation=$best;selection='endpoint evidence first, then crossing, then minimum distance; stable source refs as tie break'}
})
$attachedEnds=@(@(foreach($r in $relations|Where-Object attachmentAllowed){for($i=0;$i -lt 2;$i++){if($r.endpointTypes[$i] -in @('endpoint_on_boundary','endpoint_inside_representation') -and $r.routingEndpointRef[$i] -in $route.openEndpoints.nodeRef){$r.routingEndpointRef[$i]}}})|Select-Object -Unique)
$components=@(foreach($c in $route.components){@{componentRef=$c.componentId;attachedDeviceCandidates=@($relations|Where-Object {$_.attachmentAllowed -and $_.routingEdgeRef -in $c.edgeRefs}|Select-Object -ExpandProperty deviceInstanceRef -Unique)}})
$rank=@{endpoint_on_boundary=0;endpoint_inside_representation=1;crossing_through_representation=2;segment_crosses_boundary=2;segment_ends_near_boundary=3;unresolved=4;no_relation=5}
$instanceOutcomes=@(foreach($g in $geometry){$best=$relations|Where-Object deviceInstanceRef -eq $g.instanceRef|Sort-Object @{Expression={$rank[$_.relationType]}},distance|Select-Object -First 1;@{instanceRef=$g.instanceRef;sample=$g.sample;strongestRelation=$best.relationType;relationRef=$best.routingEdgeRef}})
$result=[pscustomobject]@{modelType='DeviceRoutingAttachmentAudit';sourceDrawing=$route.sourceDrawing;sourceSnapshot=$route.sourceSnapshot;sourceRoutingHash=(Get-FileHash (Join-Path $Root $routingPath)).Hash;definitions=@($definitions.Values);geometry=$geometry;relations=$relations;golden=$golden;attachedOpenEndpoints=$attachedEnds;componentAttachments=$components;originalComponentCount=$route.components.Count;resultComponentCount=$route.components.Count;physicalConnections=@();confirmedPorts=@();requirementsModified=$false;tolerance=0.001;nearDistance=1.0;units='raw drawing units';statistics=@($relations|Group-Object relationType|ForEach-Object {@{relationType=$_.Name;pairCount=$_.Count}})}
$result|Add-Member instanceOutcomes $instanceOutcomes
if($OutputPath){$result|ConvertTo-Json -Depth 70|Set-Content -LiteralPath $OutputPath -Encoding utf8}
$result
