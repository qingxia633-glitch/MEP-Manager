param([string]$Root=(Join-Path $PSScriptRoot '..'),[string]$OutputPath)
$ErrorActionPreference='Stop'
foreach($pin in (Get-Content (Join-Path $PSScriptRoot 'tests/alarm-routing-sources.json') -Raw -Encoding UTF8|ConvertFrom-Json)){
 if((Get-FileHash (Join-Path $Root $pin.path)).Hash -cne $pin.sha256){throw "Routing source artifact changed: $($pin.path)"}
}
if(-not ('Mep.Routing.Graph' -as [type])){Add-Type -Path (Join-Path $PSScriptRoot 'RoutingGeometry.cs')}
$source='local_test_data/fire-alarm-full-snapshot-20260923/MEP-full-entity-report.txt'
$hash=(Get-FileHash -LiteralPath (Join-Path $Root $source)).Hash
$fixture=Get-Content (Join-Path $PSScriptRoot 'tests/fire-fixture.json') -Raw -Encoding UTF8|ConvertFrom-Json
if($hash -cne $fixture.source.sha256){throw 'Alarm snapshot changed'}
$raw=[IO.File]::ReadAllText((Join-Path $Root $source))
function Field($text,$key){[regex]::Match($text,'(?m)^'+[regex]::Escape($key)+'=(.*?)\r?$').Groups[1].Value.Trim('"')}
function Point($text){,[double[]]@([regex]::Matches($text,'[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?')|ForEach-Object {[double]::Parse($_.Value,[cultureinfo]::InvariantCulture)})}
if(!(Field $raw DWG).EndsWith($fixture.source.dwgName) -or (Field $raw ReadErrorCount) -ne '0' -or $raw -notmatch '(?m)^END_OF_REPORT'){throw 'Source incomplete'}
$polygonPath='outputs/fire-broadcast-zone1-mapping/results.json'
$polygon=Get-Content (Join-Path $Root $polygonPath) -Raw -Encoding UTF8|ConvertFrom-Json
if(@($polygon.vertices).Count -ne 52 -or $polygon.polygonRef -notmatch ':55DF5$'){throw 'Reviewed polygon unavailable'}
$logicalPath='outputs/fire-alarm-logical-network/results.json'
$logical=Get-Content (Join-Path $Root $logicalPath) -Raw -Encoding UTF8|ConvertFrom-Json
$records=@{};$segments=[Collections.Generic.List[Mep.Routing.Segment]]::new();$excluded=[Collections.Generic.List[object]]::new()
$layer=@($fixture.lines|Where-Object systemCandidate -eq fire_alarm|Select-Object -ExpandProperty layer -Unique)
if($layer.Count -ne 1){throw 'Layer candidate policy ambiguous'}
foreach($record in [regex]::Split($raw,'(?m)(?=^EntityHandle=)')){
 $handle=Field $record EntityHandle;if(!$handle){continue};$records[$handle]=$record
 $type=Field $record DXF_Type;if($type -notin @('LINE','LWPOLYLINE')){continue}
 $rawLayer=Field $record Layer;if($rawLayer -cne $layer[0]){continue}
 $ref=$hash+':'+$handle
 $vertices=if($type -eq 'LINE'){@((Point (Field $record Start_WCS)),(Point (Field $record End_WCS)))}else{@([regex]::Matches($record,'(?m)^Vertex_WCS=(.*?)\r?$')|ForEach-Object {Point $_.Groups[1].Value})}
 $bulges=@([regex]::Matches($record,'\(42 \. ([^)]+)\)')|ForEach-Object {[double]::Parse($_.Groups[1].Value,[cultureinfo]::InvariantCulture)})
 if(@($vertices|Where-Object Count -ne 3).Count -or $vertices.Count -lt 2 -or @($bulges|Where-Object {$_ -ne 0}).Count){$excluded.Add(@{rawEntityRef=$ref;reason='missing_vertices_or_curved_geometry';status='unresolved'});continue}
 $count=$vertices.Count-1;if($type -eq 'LWPOLYLINE' -and (Field $record Closed) -in @('T',':vlax-true')){$count++}
 for($i=0;$i -lt $count;$i++){$segments.Add([Mep.Routing.Segment]@{id=$ref+':segment:'+ $i;rawEntityRef=$ref;layer=$rawLayer;systemScope='fire_alarm';vertexIndex=$i;a=$vertices[$i];b=$vertices[($i+1)%$vertices.Count]})}
}
$graph=[Mep.Routing.Graph]::Build($segments.ToArray(),[double[][]]$polygon.vertices,0.001,1.0)
$sourceGeometry=@(foreach($ref in @($graph.edges.rawEntityRef|Select-Object -Unique)){
 $handle=$ref.Split(':')[-1];$r=$records[$handle]
 [pscustomobject]@{rawEntityRef=$ref;sourcePath=$source;sourceSnapshot=$hash;handle=$handle;entityType=(Field $r DXF_Type);layer=(Field $r Layer);vertices=@($segments|Where-Object rawEntityRef -eq $ref|ForEach-Object {@{vertexIndex=$_.vertexIndex;start=$_.a;end=$_.b}});systemScopeEvidenceRef='model-core/tests/fire-fixture.json';systemScopeStatus='candidate'}
})
Import-Module (Join-Path $PSScriptRoot '../tray-evidence/SpatialRelations.psm1')
foreach($endpoint in $graph.openEndpoints){
 if((Get-PolygonBoundaryDistanceXY -Point $endpoint.coordinates -Vertices ([double[][]]$polygon.vertices)) -le 0.001){$endpoint.possibleCause='compartment_clip_boundary'}
 $endpoint.modelType='OpenEndpointCandidate'
}
$endpointCandidates=@(foreach($edge in $graph.edges){
 foreach($end in @('start','end')){[pscustomobject]@{modelType='RoutingEndpointCandidate';edgeRef=$edge.edgeId;rawEntityRef=$edge.rawEntityRef;end=$end;point=if($end -eq 'start'){$edge.startXY}else{$edge.endXY};nodeRef=if($end -eq 'start'){$edge.fromNode}else{$edge.toNode};portStatus='unresolved'}}
})
foreach($gap in $graph.gaps){
 $gap|Add-Member coordinates @($graph.nodes|Where-Object nodeId -in @($gap.fromNode,$gap.toNode)|ForEach-Object {$_.point})
 $gap|Add-Member neighboringEdgeRefs @($graph.edges|Where-Object {$_.fromNode -in @($gap.fromNode,$gap.toNode) -or $_.toNode -in @($gap.fromNode,$gap.toNode)}|ForEach-Object edgeId)
}
$deviceRelations=@(foreach($membership in $logical.memberships){[pscustomobject]@{modelType='DeviceEndpointRelationCandidate';membershipRef=$membership.membershipId;instanceRef=$membership.instanceRef;relationStatus='unresolved';reason='plan_instance_true_representation_boundary_not_admitted';portRole='unresolved';physicalConnection='unresolved'}})
$reviews=[Collections.Generic.List[object]]::new()
foreach($p in $graph.openEndpoints){$reviews.Add(@{type='routing_open_endpoint';sourceRef=$p.nodeRef;status='open'})}
foreach($p in $graph.gaps){$reviews.Add(@{type='routing_gap';sourceRef=@($p.fromNode,$p.toNode);status='open'})}
foreach($p in $graph.contacts|Where-Object type -eq crossing_without_connection){$reviews.Add(@{type='crossing_not_connected';sourceRef=@($p.a,$p.b);status='open'})}
foreach($p in $deviceRelations){$reviews.Add(@{type='device_endpoint_unresolved';sourceRef=$p.instanceRef;status='open'})}
foreach($edge in $logical.edges){$reviews.Add(@{type='logical_without_route';sourceRef=$edge.edgeId;status='open';reason='no_admitted_cross_drawing_endpoint_binding'})}
foreach($component in $graph.components){$component|Add-Member edgeCount $component.edgeRefs.Count;$component|Add-Member nodeCount $component.nodeRefs.Count;$component|Add-Member attachedDeviceCandidates @();$component|Add-Member gapRefs @($graph.gaps|Where-Object {$_.fromNode -in $component.nodeRefs -or $_.toNode -in $component.nodeRefs});$reviews.Add(@{type='route_without_logical_target';sourceRef=$component.componentId;status='open'})}
$golden=$graph.components|Sort-Object @{Expression={$_.edgeRefs.Count};Descending=$true},@{Expression={$_.openEndpointRefs.Count}},componentId|Select-Object -First 1
$output=[pscustomobject]@{
 modelType='RoutingGraphCandidate';systemScope='fire_alarm';status='experimental';compartmentRef=$logical.compartmentRef
 sourceDrawing=(Field $raw DWG);sourceSnapshot=$hash;sourcePath=$source;polygonRef=$polygon.polygonRef
 sourceArtifacts=@(@{path=$polygonPath;sha256=(Get-FileHash (Join-Path $Root $polygonPath)).Hash},@{path=$logicalPath;sha256=(Get-FileHash (Join-Path $Root $logicalPath)).Hash})
 coordinateTransform='identity_to_already_projected_polygon';drawingUnits=(Field $raw INSUNITS);scaleStatus='unresolved';lengthMeaning='2D drawing units, not engineering quantity'
 systemScopeEvidence=@{status='candidate';basis='snapshot-scoped reviewed layer clue';layer=$layer[0];evidenceRef='model-core/tests/fire-fixture.json';confirmedMembership=$false}
 tolerance=0.001;gapSearchRadius=1.0;gapSearchMeaning='near-end investigation window in drawing units, not connection tolerance'
 nodes=@($graph.nodes);edges=@($graph.edges);connections=@($graph.contacts);openEndpoints=@($graph.openEndpoints);gaps=@($graph.gaps);components=@($graph.components)
 endpoints=$endpointCandidates
 sourceGeometry=$sourceGeometry;scopeMethod='finite segment clipping against all 52 polygon edges; clipped endpoints are scope boundaries'
 deviceEndpointRelations=$deviceRelations;excludedGeometry=@($excluded);reviewItems=@($reviews)
 upstreamLogicalGaps=@($logical.gaps);upstreamLogicalOpenEnds=@($logical.openEnds);upstreamReviewItems=@($logical.reviewItems)
 sourceScopeBoundary='system diagram gaps retained separately; never transplanted as plan routes';bridgeAllowed=$false
 goldenSample=@{selection='most real edges, then fewest open ends; all device boundaries unresolved';component=$golden;edges=@($graph.edges|Where-Object edgeId -in $golden.edgeRefs)}
 formalCircuit=@();physicalConnections=@();quantities=@();confirmedDeviceRelations=0
}
if($OutputPath){$output|ConvertTo-Json -Depth 90|Set-Content -LiteralPath $OutputPath -Encoding utf8}
$output
