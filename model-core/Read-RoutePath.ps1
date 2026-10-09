param([string]$OutputPath)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'RoutePath.psm1') -Force
$root=Split-Path $PSScriptRoot;$data=@()
$pins=Get-Content (Join-Path $PSScriptRoot 'tests/route-path-sources.json') -Raw -Encoding utf8|ConvertFrom-Json
foreach($p in $pins){$file=Join-Path $root $p.path;if((Get-FileHash $file).Hash -cne $p.sha256){throw 'Pinned route evidence changed'};$data+=,(Get-Content $file -Raw -Encoding utf8|ConvertFrom-Json)}
$x=Find-PlanRoutePath $data[0] $data[1] $data[2] $data[3] $pins[0].path $pins[1].path $pins[3].path
$x|Add-Member sourceArtifacts $pins
if($OutputPath){$x|ConvertTo-Json -Depth 90|Set-Content $OutputPath -Encoding utf8};$x
