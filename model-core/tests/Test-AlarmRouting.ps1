param([string]$OutputPath)
$ErrorActionPreference='Stop'
if(-not ('Mep.Routing.Graph' -as [type])){Add-Type -Path (Join-Path $PSScriptRoot '../RoutingGeometry.cs')}
function Assert($condition,$message){if(!$condition){throw $message}}
$ring=[double[][]]@(@(-10,-10,0),@(10,-10,0),@(10,10,0),@(-10,10,0))
function S($id,$a,$b,$scope='fire_alarm'){[Mep.Routing.Segment]@{id=$id;rawEntityRef=$id;layer='test';a=$a;b=$b;systemScope=$scope}}
$a=S a @(-5,0,0) @(5,0,0);$cross=S cross @(0,-5,0) @(0,5,0)
$g=[Mep.Routing.Graph]::Build(@($a,$cross),$ring,0.001,1)
Assert ($g.components.Count -eq 2 -and $g.edges.Count -eq 2) 'Interior crossing must not connect'
Assert ($g.contacts[0].type -eq 'crossing_without_connection') 'Crossing review missing'
$g=[Mep.Routing.Graph]::Build(@($a,(S branch @(0,0,0) @(0,5,0))),$ring,0.001,1)
Assert ($g.components.Count -eq 1 -and $g.edges.Count -eq 3) 'T contact must split real segment'
Assert ([math]::Abs($g.components[0].total2DGeometricLength-15) -lt 0.00001) 'Length conservation'
$g=[Mep.Routing.Graph]::Build(@($a,(S gap @(5.5,0,0) @(8,0,0))),$ring,0.001,1)
Assert ($g.components.Count -eq 2 -and $g.gaps.Count -eq 1 -and !$g.gaps[0].bridgeAllowed) 'Never bridge a gap'
$g=[Mep.Routing.Graph]::Build(@((S short @(0,0,0) @(0.5,0,0))),$ring,0.001,1)
Assert ($g.gaps.Count -eq 0) 'A short real edge is not its own gap'
$g=[Mep.Routing.Graph]::Build(@($a,(S unknown @(5,0,0) @(8,0,0) unknown),(S phone @(5,0,0) @(8,0,0) fire_phone)),$ring,0.001,1)
Assert ($g.edges.Count -eq 1) 'System isolation'
$g=[Mep.Routing.Graph]::Build(@($a,(S elevated @(0,0,1) @(0,5,1))),$ring,0.001,1)
Assert ($g.components.Count -eq 2) 'Different Z must not join'
$concave=[double[][]]@(@(0,0,0),@(8,0,0),@(8,2,0),@(2,2,0),@(2,8,0),@(0,8,0))
$g=[Mep.Routing.Graph]::Build(@((S clip @(-1,4,0) @(7,4,0))),$concave,0.001,1)
Assert ($g.edges.Count -eq 1 -and [math]::Abs($g.edges[0].segmentLength-2) -lt 0.00001) 'Use real polygon, not bounds'
$g=[Mep.Routing.Graph]::Build(@((S c1 @(-15,-5,0) @(0,10,0)),(S c2 @(-15,5,0) @(0,-10,0))),$ring,0.001,1)
Assert ($g.components.Count -eq 2) 'Artificial clipping endpoints must not join interior crossings'
$result=& (Join-Path $PSScriptRoot '../Read-AlarmRouting.ps1') -OutputPath $OutputPath
Assert ($result.edges.Count -gt 0 -and $result.components.Count -gt 0) 'Real routing fixture empty'
Assert (@($result.edges|Where-Object systemScope -ne fire_alarm).Count -eq 0) 'Foreign system'
Assert (@($result.deviceEndpointRelations|Where-Object relationStatus -ne unresolved).Count -eq 0) 'No insertion-point port snapping'
Assert (!$result.bridgeAllowed -and $result.quantities.Count -eq 0 -and $result.physicalConnections.Count -eq 0) 'Forbidden inference'
Assert ($result.upstreamLogicalGaps.Count -eq 2 -and $result.upstreamLogicalOpenEnds.Count -eq 17) 'Preserve source scoped gaps/open ends'
Write-Output ('PASS AlarmRouting: edges={0}, nodes={1}, components={2}, open={3}, gaps={4}, device unresolved={5}, golden length={6}' -f $result.edges.Count,$result.nodes.Count,$result.components.Count,$result.openEndpoints.Count,$result.gaps.Count,$result.deviceEndpointRelations.Count,$result.goldenSample.component.total2DGeometricLength)
