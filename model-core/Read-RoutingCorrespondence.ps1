param([string]$OutputPath)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'RoutingCorrespondence.psm1') -Force
$root=Split-Path $PSScriptRoot
$sources=Get-Content (Join-Path $PSScriptRoot 'tests/routing-correspondence-sources.json') -Raw -Encoding utf8|ConvertFrom-Json
$data=@();foreach($s in $sources){$p=Join-Path $root $s.path;if((Get-FileHash $p).Hash -cne $s.sha256){throw "Source changed: $($s.path)"};$data+=,(Get-Content $p -Raw -Encoding utf8|ConvertFrom-Json)}
if($data[2].sourceRoutingHash -cne $sources[0].sha256){throw 'Attachment routing revision mismatch'}
$result=Join-RoutingCorrespondence -Routing $data[0] -Logical $data[1] -Attachment $data[2]
$result|Add-Member sourceArtifacts $sources
if($OutputPath){$result|ConvertTo-Json -Depth 90|Set-Content $OutputPath -Encoding utf8}
$result
