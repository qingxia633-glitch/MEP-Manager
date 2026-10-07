param([string]$Fixture=(Join-Path $PSScriptRoot 'tests/local-fixture.json'))
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'SystemDiagram.psm1') -Force
$root=Join-Path $PSScriptRoot '..'
$f=Get-Content -LiteralPath $Fixture -Raw -Encoding UTF8|ConvertFrom-Json
foreach($s in @($f.sources.diagram,$f.sources.outer,$f.sources.child)){
 $path=Join-Path $root $s.path
 if((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $s.sha256){throw 'Fixture source changed; explicit review required, no evidence migration'}
}
$snapshot=Read-DiagramSnapshot (Join-Path $root $f.sources.diagram.path)
$outer=Read-DiagramProbe (Join-Path $root $f.sources.outer.path)
$child=Read-DiagramProbe (Join-Path $root $f.sources.child.path)
$inserts=@(foreach($h in $f.rowInsertHandles){$v=@($snapshot.entities|Where-Object handle -eq $h);if($v.Count -ne 1){throw "Missing/duplicate row basis: $h"};$v[0]})
$statements=@(foreach($h in $f.statementHandles){$v=@($snapshot.statements|Where-Object handle -eq $h);if($v.Count -ne 1){throw "Missing/duplicate statement: $h"};$v[0]})
$view=New-DiagramLocalView -Snapshot $snapshot.sourceSnapshot -RowInserts $inserts -Statements $statements -LocalViewId $f.localViewId -RowBand $f.rowBandDrawingUnits -Tolerance $f.toleranceDrawingUnits
$hc=$f.humanConfirmation
$hc|Add-Member sourceSnapshot $snapshot.sourceSnapshot
$hc|Add-Member localViewId $f.localViewId
$hc|Add-Member projectScope $f.projectScope
$view.humanConfirmations=@($hc)
$view.snapshotCorrespondences=@([pscustomobject]@{source=$snapshot.sourceSnapshot.sha256;target=$outer.Snapshot;definition=$f.probeCorrespondence.outerBlock;status=$f.probeCorrespondence.status;basis=$f.probeCorrespondence.basis},[pscustomobject]@{source=$outer.Snapshot;target=$child.Snapshot;definition=$f.probeCorrespondence.symbolBlock;status='candidate';basis=$f.probeCorrespondence.basis})
foreach($e in $inserts){
 $confirmation=$null;if($e.handle -eq $hc.outerHandle){$confirmation=$hc}
 $device=New-DeviceCandidate -OuterInsert $e -OuterProbe $outer -ChildProbe $child -Link $f.probeCorrespondence -HumanConfirmation $confirmation -LocalViewId $f.localViewId -CandidateRole $f.symbolCandidateRole
 $view.deviceCandidates+=,$device
 $row=$view.rows|Where-Object {$_.rowBasis.handle -eq $e.handle}
 $row.memberRepresentations+=,$device.id
 if($null -ne $confirmation){$row.humanConfirmations+=,$hc.id}
}
$view.representationEquivalences=@(New-RepresentationEquivalence -OuterProbe $outer -ChildProbe $child -Selection $f.equivalenceFixture -Tolerance $f.toleranceDrawingUnits)
# Return an object to the caller. No output file, AutoCAD, or recursive probe.
$view
