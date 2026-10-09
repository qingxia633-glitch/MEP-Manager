param([string]$OutputPath)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'PlanLogicalRelation.psm1') -Force
$root=Split-Path $PSScriptRoot
$pins=Get-Content (Join-Path $PSScriptRoot 'tests/plan-logical-sources.json') -Raw -Encoding utf8|ConvertFrom-Json
$data=@();foreach($p in $pins){$file=Join-Path $root $p.path;if((Get-FileHash $file).Hash -cne $p.sha256){throw 'Pinned source changed'};$data+=,(Get-Content $file -Raw -Encoding utf8|ConvertFrom-Json)}
$selection=Get-Content (Join-Path $PSScriptRoot 'tests/plan-logical-selection.json') -Raw -Encoding utf8|ConvertFrom-Json
$result=Join-PlanLogicalRelation $data[0] $data[1] $data[2] $selection $pins[1].path
$result|Add-Member sourceArtifacts $pins
if($OutputPath){$result|ConvertTo-Json -Depth 80|Set-Content $OutputPath -Encoding utf8}
$result
