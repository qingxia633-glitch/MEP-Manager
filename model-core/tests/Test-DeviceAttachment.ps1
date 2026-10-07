param([string]$OutputPath)
$ErrorActionPreference='Stop'
if(-not ('Mep.DeviceRepresentation.Geometry' -as [type])){Add-Type -Path (Join-Path $PSScriptRoot '../DeviceRepresentation.cs')}
function Assert($c,$m){if(!$c){throw $m}}
$square=[double[][]]@(@(-1,-1,0),@(1,-1,0),@(1,1,0),@(-1,1,0))
$p=[Mep.DeviceRepresentation.Geometry]::Transform([double[][]]@(,[double[]]@(2,1,0)),@(10,20,0),@(2,3,1),([math]::PI/2),@(0,0,1),@(1,1,0),$false,$false)
Assert ([math]::Abs($p[0][0]-10) -lt 1e-9 -and [math]::Abs($p[0][1]-22) -lt 1e-9) 'Rotated scaled base-point transform'
$p=[Mep.DeviceRepresentation.Geometry]::Transform([double[][]]@(,[double[]]@(1,2,3)),@(0,0,0),@(-2,3,1),0,@(0,0,1),@(0,0,0),$false,$false)
Assert ($p[0][0] -eq -2 -and $p[0][1] -eq 6 -and $p[0][2] -eq 3) 'Negative scale must be retained'
$p=[Mep.DeviceRepresentation.Geometry]::Transform([double[][]]@(,[double[]]@(1,2,3)),@(0,0,0),@(1,1,1),0,@(0,0,-1),@(0,0,0),$false,$false)
Assert ($p[0][0] -eq -1 -and $p[0][1] -eq 2 -and $p[0][2] -eq -3) 'Normal basis'
foreach($case in @('missing','dynamic','nested')){$blocked=$false;try{[void][Mep.DeviceRepresentation.Geometry]::Transform($square,@(0,0,0),$(if($case -eq 'missing'){@(1,1)}else{@(1,1,1)}),0,@(0,0,1),@(0,0,0),($case -eq 'dynamic'),($case -eq 'nested'))}catch{$blocked=$true};Assert $blocked "Must block $case"}
$r=[Mep.DeviceRepresentation.Geometry]::Relate(@(1.01,0,0),@(2,0,0),$square,0.001,1)
Assert ($r.relationType -eq 'segment_ends_near_boundary' -and !$r.attachmentAllowed) 'Near is not touching'
$r=[Mep.DeviceRepresentation.Geometry]::Relate(@(-2,0,0),@(2,0,0),$square,0.001,1)
Assert ($r.relationType -eq 'crossing_through_representation' -and !$r.attachmentAllowed -and $r.physicalConnection -eq 'unresolved') 'Crossing cannot attach'
$r=[Mep.DeviceRepresentation.Geometry]::Relate(@(1,0,0),@(2,0,0),$square,0.001,1)
Assert ($r.attachmentAllowed -and $r.portStatus -eq 'unresolved') 'Boundary candidate is not a port'
$r=[Mep.DeviceRepresentation.Geometry]::Relate(@(0,0,0),@(2,0,0),$square,0.001,1)
Assert ($r.relationType -eq 'endpoint_inside_representation' -and $r.physicalConnection -eq 'unresolved') 'Inside representation only'
$transformed=[Mep.DeviceRepresentation.Geometry]::Transform($square,@(10,20,0),@(-2,3,1),([math]::PI/2),@(0,0,1),@(0,0,0),$false,$false)
$r=[Mep.DeviceRepresentation.Geometry]::Relate(@(13,20,0),@(15,20,0),$transformed,0.001,1)
Assert ($r.relationType -eq 'endpoint_on_boundary') 'Rotated mirrored scaled boundary contact'
$r=[Mep.DeviceRepresentation.Geometry]::Relate(@(1,0,3000),@(2,0,3000),$square,0.001,1)
Assert ($r.relationType -eq 'unresolved' -and !$r.attachmentAllowed) 'No XY-only attachment across Z mismatch'
$path=Join-Path $PSScriptRoot '../../outputs/fire-alarm-routing/results.json';$before=(Get-FileHash $path).Hash
$audit=& (Join-Path $PSScriptRoot '../Read-DeviceAttachment.ps1') -OutputPath $OutputPath
Assert ((Get-FileHash $path).Hash -eq $before) 'Raw routing graph modified'
Assert ($audit.geometry.Count -eq 118 -and $audit.originalComponentCount -eq 74 -and $audit.resultComponentCount -eq 74) 'Scope and component preservation'
Assert (@($audit.geometry|Where-Object geometryStatus -ne supported_candidate).Count -eq 0) 'Real transforms unresolved'
Assert ($audit.attachedOpenEndpoints.Count -eq 94) 'Real endpoint fixture changed'
Assert (@($audit.relations|Where-Object {$_.relationType -eq 'crossing_through_representation' -and $_.attachmentAllowed}).Count -eq 0) 'Crossing mistaken for connection'
Assert (@($audit.geometry.representativePoints|Where-Object confirmedPort).Count -eq 0) 'POINT promoted to port'
Assert ($audit.confirmedPorts.Count -eq 0 -and $audit.physicalConnections.Count -eq 0 -and !$audit.requirementsModified) 'Forbidden upgrade'
Assert ($audit.golden.Count -eq 2 -and @($audit.golden|Where-Object {$_.relation.relationType -ne 'endpoint_on_boundary'}).Count -eq 0) 'Real golden relations'
Write-Output ('PASS DeviceAttachment: checked={0}, attached open={1}, components={2}, no confirmed ports/physical connections' -f $audit.geometry.Count,$audit.attachedOpenEndpoints.Count,$audit.resultComponentCount)
