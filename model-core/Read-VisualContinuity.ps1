param([string]$OutputPath)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'VisualContinuity.psm1') -Force
$root=Split-Path $PSScriptRoot
$pins=Get-Content (Join-Path $PSScriptRoot 'tests/visual-continuity-sources.json') -Raw -Encoding utf8|ConvertFrom-Json
$data=@();foreach($s in $pins){$p=Join-Path $root $s.path;if((Get-FileHash $p).Hash -cne $s.sha256){throw "Source changed: $($s.path)"};$data+=,(Get-Content $p -Raw -Encoding utf8|ConvertFrom-Json)}
$routing=$data[0];$audit=$data[1];$inventory=$data[2]
if($inventory.summary.sourceHash -cne $routing.sourceSnapshot){throw 'Inventory source mismatch'}
if((Get-FileHash (Join-Path $root $inventory.summary.source)).Hash -cne $routing.sourceSnapshot){throw 'Raw snapshot changed'}
# Reviewed project pattern range, not a global routing tolerance or quantity constraint.
$pattern=[pscustomobject]@{patternId='reviewed-project-crossing-jump';sourceSnapshot=$routing.sourceSnapshot;status='supported_candidate';minGap=($audit.candidates|Measure-Object gapDistance -Minimum).Minimum;maxGap=($audit.candidates|Measure-Object gapDistance -Maximum).Maximum;tolerance=.001;angleToleranceDegrees=.01;evidenceRefs=@($audit.candidates|ForEach-Object {$pins[1].path+':'+$_.beforeHandle+':'+$_.afterHandle});rangeMeaning='observed reviewed sample envelope, drawing units; not reusable threshold'}
$geometry=@($inventory.entities|ForEach-Object {[pscustomobject]@{handle=$_.handle;rawEntityRef=$routing.sourceSnapshot+':'+$_.handle;sourceSnapshot=$inventory.summary.sourceHash;vertices=$_.vertices;bulges=$_.bulges;layer=$_.layer}})
$pairs=@($audit.candidates)+@($audit.collinearPairs|Where-Object {$_.crossedEdgeRef.Count -eq 0})
$result=New-RoutingContinuityView $routing $pairs $geometry $pattern
$result|Add-Member sourceArtifacts $pins
if($OutputPath){$result|ConvertTo-Json -Depth 60|Set-Content $OutputPath -Encoding utf8}
$result
