param(
 [string]$InputPath=(Join-Path $PSScriptRoot '../local_test_data/ew0002-evidence-admission-final-20260925.json'),
 [string]$OutputPath
)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'EvidenceInvestigationAdapter.psm1') -Force
Import-Module (Join-Path $PSScriptRoot '../model-core/GoldenSample.psm1')
Import-Module (Join-Path $PSScriptRoot '../model-core/FireGoldenSample.psm1')
if($OutputPath -and (Test-Path -LiteralPath $OutputPath)){throw 'Existing investigation output protected'}
$a=Get-Content -LiteralPath $InputPath -Raw|ConvertFrom-Json
$all=@($a.statementEvidence)+@($a.referenceEvidence)
$pump=Read-GoldenModel;$fire=Read-FireGoldenModel
$requirements=@($pump.requirements|Where-Object requiredFact -In @('individual_pump_mapping','physical_routing','procurement_boundary'))+@($fire.requirements|Where-Object requirementId -In @('req:phone-relation','req:broadcast','req:membership'))
$tasks=@($requirements|ForEach-Object {[pscustomobject]@{requirement=$_;context=[pscustomobject]@{mode='engineering_task'}}})
$local=@(New-SourceInvestigationTask $all)
$r=[pscustomobject]@{modelType='EvidenceInvestigationAudit';version='experimental-1';upstreamProvenance=[pscustomobject]@{path=(Resolve-Path -LiteralPath $InputPath).Path;sha256=(Get-FileHash -LiteralPath $InputPath).Hash;sourceSnapshot=$a.sourceSnapshot};goldenRequirements=$requirements;goldenResults=(Invoke-EvidenceInvestigation $all $tasks);sourceLocalTasks=$local;sourceLocalResults=(Invoke-EvidenceInvestigation $all $local);interpretation='Source-local follow-ups are not successful help to the separate Golden installation/network tasks'}
if($OutputPath){$r|ConvertTo-Json -Depth 80|Set-Content -LiteralPath $OutputPath -Encoding UTF8;Write-Host "Saved: $OutputPath"}else{$r}
