param([string]$OutputPath)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'DrainagePit.psm1') -Force
$spec=Get-Content (Join-Path $PSScriptRoot 'tests/k1-4-fixture.json') -Raw -Encoding UTF8|ConvertFrom-Json
$json=Read-PitCandidate $spec|ConvertTo-Json -Depth 80
if($OutputPath){if(Test-Path -LiteralPath $OutputPath){throw 'Existing output protected'};[IO.File]::WriteAllText($OutputPath,$json,[Text.UTF8Encoding]::new($false))}else{$json}
