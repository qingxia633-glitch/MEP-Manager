param(
 [Parameter(Mandatory)][string]$Report,
 [Parameter(Mandatory)][string]$Selection,
 [string]$Output,
 [double]$Tolerance=0.00001
)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'GeometryUnits.psm1') -Force
$selectionData=Get-Content -LiteralPath $Selection -Raw -Encoding UTF8 | ConvertFrom-Json
$entities=@(Read-LocalEntities -Report $Report -Handles $selectionData.selectionHandles)
$result=Get-LocalTrayUnits -RawEntities $entities -Tolerance $Tolerance
$json=$result | ConvertTo-Json -Depth 40
if($Output){$json | Set-Content -LiteralPath $Output -Encoding UTF8}else{$json}
