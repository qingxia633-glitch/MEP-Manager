param(
 [Parameter(Mandatory)][string]$Report,
 [Parameter(Mandatory)][string]$ContextSpec,
 [string]$Output
)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'ViewContext.psm1') -Force
$spec=Get-Content -LiteralPath $ContextSpec -Raw -Encoding UTF8|ConvertFrom-Json
$hash=(Get-FileHash -LiteralPath $Report -Algorithm SHA256).Hash
if($hash -ne $spec.drawingSnapshotId){throw 'Context specification belongs to another report snapshot; review required'}
$raw=@(Read-LocalEntities -Report $Report -Handles $spec.selectionHandles)
$geometry=Get-LocalTrayUnits -RawEntities $raw
$records=@(Read-AnnotationRegion -Report $Report -Geometry $geometry|Where-Object {$_.handle -in $spec.annotationHandles})
$result=Invoke-LocalViewAnalysis -Geometry $geometry -Records $records -Spec $spec
$json=$result|ConvertTo-Json -Depth 70
if($Output){$json|Set-Content -LiteralPath $Output -Encoding UTF8}else{$json}
