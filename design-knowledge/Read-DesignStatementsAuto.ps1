param([Parameter(Mandatory)][string]$ReportPath,[switch]$Summary,[switch]$LegacySpacing)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'DesignStatementReader.psm1') -Force
$source=Read-DesignTextSnapshot $ReportPath
$result=Find-DesignStatementCandidates $source.textRecords -Geometry $source.geometryRecords -LayoutAware:(!$LegacySpacing)
if($Summary){
 [pscustomobject]@{sourceDocument=$source.sourceDocument;sourceSnapshot=$source.sourceSnapshot;regions=$result.regions.Count;paragraphs=$result.paragraphs.Count;reviewItems=$result.reviewItems.Count;reviewsByType=@($result.reviewItems|Group-Object type|Select-Object Name,Count);lowConfidenceRegions=@($result.regions|Where-Object confidence -EQ low).Count;highConfidenceOrders=@($result.paragraphs|Where-Object {$_.readingOrderCandidate.confidence -eq 'high'}).Count}|ConvertTo-Json -Depth 10
}else{$result|ConvertTo-Json -Depth 100}
