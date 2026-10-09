param([string]$Report = (Join-Path $PSScriptRoot '../local_test_data/MEP-entity-report.txt'))
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'CenterPath.psm1') -Force -DisableNameChecking
$config = Get-Content (Join-Path $PSScriptRoot 'samples.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$entities = Read-SampleReport $Report $config
$script:checks = 0
function Near($actual, $expected) { if ([math]::Abs($actual-$expected) -gt 0.00001) { throw "Expected $expected, got $actual" }; $script:checks++ }
function Verify($r) {
 Near $r.straight.geometry.points[0][0] 556014666.633999
 Near $r.straight.geometry.length.drawingUnits 4349.453361
 Near $r.straight.geometry.length.m 4.349453361
 Near $r.turn.supportedSegments[0].points[0][1] 553163640.265205
 Near $r.turn.supportedSegments[1].points[0][0] 556014150.352873
 Near $r.turn.topology.nodes[1].point[0] 556014150.352873
 Near $r.turn.topology.nodes[1].point[1] 553163640.265205
 Near $r.turn.geometry.length.drawingUnits 800
 Near $r.turn.geometry.length.m 0.8
 Near $r.turn.connections.inner.Count 3
}
$result = Build-Samples $entities $config
$roundtrip=$result | ConvertTo-Json -Depth 20 | ConvertFrom-Json
Near $roundtrip.turn.geometry.points[0][0] 556013750.352873
Near $roundtrip.turn.geometry.points[2][1] 553164040.265205
Verify $result
foreach ($key in @($entities.Keys)) {
 $old = $entities[$key].vertices
 $entities[$key].vertices = @($old[1], $old[0])
 Verify (Build-Samples $entities $config)
 $entities[$key].vertices = $old
}
$oldScale=$config.units.mmPerDrawingUnit
$config.units.mmPerDrawingUnit=2
Near (Build-Samples $entities $config).turn.geometry.length.m 1.6
$config.units.mmPerDrawingUnit=$oldScale
$original=$entities['528D6'].vertices[1][0]
$entities['528D6'].vertices[1][0]+=1
$rejected=$false
try { Build-Samples $entities $config | Out-Null } catch { $rejected=$true }
if(-not $rejected){throw 'Nonparallel pair was accepted'}
$script:checks++
$entities['528D6'].vertices[1][0]=$original
Write-Output "PASS: $script:checks checks (real report, individual endpoint reversals, unit scaling, invalid pair rejection)."
$result | ConvertTo-Json -Depth 20
