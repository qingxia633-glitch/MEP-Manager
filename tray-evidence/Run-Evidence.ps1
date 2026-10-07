param(
 [Parameter(Mandatory)][string]$Report,
 [Parameter(Mandatory)][string]$GeometryResult,
 [string]$UnitContext,
 [string]$Output,
 [double]$Margin=6000
)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'TrayEvidence.psm1') -Force
$geometry=Get-Content -LiteralPath $GeometryResult -Raw -Encoding UTF8 | ConvertFrom-Json
$hash=(Get-FileHash -LiteralPath $Report -Algorithm SHA256).Hash
if(@($geometry.rawEntities|Where-Object {$_.reportSHA256 -ne $hash}).Count -gt 0){throw 'Geometry/report snapshot mismatch'}
$context=$null
if($UnitContext){$context=Get-Content -LiteralPath $UnitContext -Raw -Encoding UTF8 | ConvertFrom-Json}
$records=@(Read-AnnotationRegion -Report $Report -Geometry $geometry -Margin $Margin)
$result=Get-TrayEvidence -Geometry $geometry -Records $records -UnitContext $context
$json=$result | ConvertTo-Json -Depth 60
if($Output){$json | Set-Content -LiteralPath $Output -Encoding UTF8}else{$json}
