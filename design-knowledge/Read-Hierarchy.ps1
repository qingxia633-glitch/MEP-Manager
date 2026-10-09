param([Parameter(Mandatory)][string]$ReportPath)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'DesignStatementReader.psm1') -Force
Import-Module (Join-Path $PSScriptRoot 'SectionHierarchy.psm1') -Force
$snapshot=Read-DesignTextSnapshot $ReportPath
$reader=Find-DesignStatementCandidates $snapshot.textRecords -Geometry $snapshot.geometryRecords -LayoutAware
# Return referenced sources with the separate structure overlay. No files are written.
[pscustomobject]@{sourceSnapshot=$snapshot.sourceSnapshot;readerResult=$reader;hierarchy=(Find-DocumentHierarchyCandidates $reader)}
