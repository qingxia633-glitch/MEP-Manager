param([Parameter(Mandatory)][string]$ManifestPath)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'SheetScope.psm1') -Force
Import-Module (Join-Path $PSScriptRoot 'DesignStatementReader.psm1') -Force
Import-Module (Join-Path $PSScriptRoot 'SectionHierarchy.psm1') -Force
$root=Split-Path $PSScriptRoot -Parent
$manifest=Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8|ConvertFrom-Json
if($manifest.correspondenceStatus-ne 'explicitly_supplied_for_this_analysis'){throw 'Explicit cross-report correspondence required'}
foreach($source in @($manifest.snapshot)+@($manifest.probes)){
 $file=Join-Path $root $source.path
 if((Get-FileHash -LiteralPath $file).Hash-cne $source.sha256){throw "Source fingerprint mismatch: $file"}
}
$path=Join-Path $root $manifest.snapshot.path
$snapshot=Read-SheetSnapshot $path
$definitions=@($manifest.probes|ForEach-Object {Read-SheetProbe (Join-Path $root $_.path)})
$text=Read-DesignTextSnapshot $path
$reader=Find-DesignStatementCandidates $text.textRecords -Geometry $text.geometryRecords -LayoutAware
$hierarchy=Find-DocumentHierarchyCandidates $reader
# Reviewed legend source handles are fixture input, never discovery rules. Resolve
# against the current snapshot explicitly; do not migrate old semantic evidence.
$extra=@($manifest.additionalRegions|ForEach-Object {[pscustomobject]@{id=$_.id;type=$_.type;refs=@($_.handles|ForEach-Object {$snapshot.sourceSnapshot+':'+$_})}})
$result=Resolve-SheetScope $snapshot $definitions $reader $hierarchy $extra
$result|Add-Member sourceCorrespondence $manifest
$result
